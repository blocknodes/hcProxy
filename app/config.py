"""hcProxy 配置：全部走环境变量，其余为常量默认值。

环境变量：
  HC_PROXY_HOST / HC_PROXY_PORT      监听地址（默认 0.0.0.0:8091）
  HC_PROXY_UPSTREAM                  上游真实 vllm 网关（默认 juagent 网关）
  HC_PROXY_UPSTREAM_KEY              上游鉴权 key（默认取 HC_LLM_API_KEY）
  HC_PROXY_DATA_DIR                  捕获落盘目录（默认 <项目>/data/captures）
  HC_PROXY_CAPTURE                   设 "0" 关闭落盘（只代理不捕获）
  HC_PROXY_TIMEOUT                   上游超时秒数（默认 120）
"""
from __future__ import annotations

import os
from pathlib import Path

# ---- 监听 ----
HOST = os.environ.get("HC_PROXY_HOST", "0.0.0.0")
PORT = int(os.environ.get("HC_PROXY_PORT", "8091"))

# ---- 上游真实 vllm server（OpenAI-format）----
# 默认指回 juagent 网关；切真实 vllm 时改这一个变量即可。
UPSTREAM = os.environ.get(
    "HC_PROXY_UPSTREAM", "http://10.19.96.219:4003/v1"
).rstrip("/")
API_KEY = os.environ.get("HC_PROXY_UPSTREAM_KEY", os.environ.get("HC_LLM_API_KEY", ""))

# ---- 超时 ----
TIMEOUT = float(os.environ.get("HC_PROXY_TIMEOUT", "120"))

# ---- 捕获落盘 ----
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("HC_PROXY_DATA_DIR", PROJECT_ROOT / "data" / "captures"))
#: 设 "0" 关闭落盘（代理仍工作）
CAPTURE = os.environ.get("HC_PROXY_CAPTURE", "1") not in {"0", "false", "off", "no"}

# ---- 捕获文件按 app 标记分流 ----
# 有 metadata.app 的请求落到 captures/<app>/，裸请求落到 captures/_raw/。
RAW_APP = "_raw"
