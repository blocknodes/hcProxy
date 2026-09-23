"""捕获落盘：每次 LLM 调用一行 JSONL，按天分目录。

布局：data/captures/<app标记>/YYYY-MM-DD.jsonl
  - <app标记> = metadata.app（如 hcAgent / hcTools）；无 metadata 的裸请求 → "_raw"
  - 每行一个 JSON 对象：
      {"ts": ..., "request": {...含 metadata...}, "response": {...}, "status": 200,
       "latency_ms": 123.4, "error": null}
  - 同一天同进程只开一次文件句柄（append），行内自带 ts，天然可 grep。

尽力而为：落盘抛异常只记 warning，绝不影响代理主链路。
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from . import config

logger = logging.getLogger("hcProxy.capture")

# {app标记: (date, file_handle)} —— 同一 app 同一天复用一个句柄
_handles: dict[str, tuple[str, Any]] = {}


def app_tag(payload: dict[str, Any]) -> str:
    """从请求体提取 app 标记（metadata.app），无则归入 _raw。"""
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        app = str(metadata.get("app", "")).strip()
        if app:
            # 防路径穿越：只留安全字符
            return "".join(c if c.isalnum() or c in "-_." else "_" for c in app)[:64]
    return config.RAW_APP


def _file_for(tag: str) -> Any:
    """拿到该 app 今天对应的 append 文件句柄（跨天自动切换）。"""
    today = datetime.now().strftime("%Y-%m-%d")
    entry = _handles.get(tag)
    if entry is not None and entry[0] == today:
        return entry[1]
    if entry is not None:
        try:  # 跨天：关旧句柄
            entry[1].close()
        except Exception:  # noqa: BLE001
            pass
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = config.DATA_DIR / tag / f"{today}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a", encoding="utf-8")  # noqa: SIM115
    _handles[tag] = (today, fh)
    logger.info("捕获文件：%s", path)
    return fh


def save(
    payload: dict[str, Any],
    *,
    response: dict[str, Any] | None,
    status: int | None,
    latency_ms: float,
    error: str | None = None,
) -> None:
    """落一条捕获记录。request 原样保存（含 metadata）。"""
    if not config.CAPTURE:
        return
    record = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "request": payload,
        "response": response,
        "status": status,
        "latency_ms": round(latency_ms, 1),
        "error": error,
    }
    try:
        fh = _file_for(app_tag(payload))
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    except Exception as exc:  # noqa: BLE001
        logger.warning("捕获落盘失败（不影响代理）：%s", exc)
