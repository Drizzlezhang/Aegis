"""Structured JSON logging for Aegis-Trader."""

import logging
import json
import sys
import time
from typing import Any


class JSONFormatter(logging.Formatter):
    """输出 JSON 格式日志行，支持 trace_id 上下文。"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self._format_time(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        # 附加上下文字段（trace_id, symbol, agent_name 等）
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False, default=str)

    @staticmethod
    def _format_time(record: logging.LogRecord) -> str:
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return dt.isoformat()


def setup_logging(level: str = "INFO", json_output: bool = True):
    """配置全局日志。生产环境用 JSON，开发用 human-readable。"""
    root = logging.getLogger()
    root.setLevel(level)
    
    handler = logging.StreamHandler(sys.stdout)
    if json_output:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
    
    root.handlers.clear()
    root.addHandler(handler)


class TraceContext:
    """Pipeline trace context — 贯穿整个分析流程的 trace_id。

    WARNING: 当前实现使用类变量存储，不支持并发 pipeline。
    如需并发安全，应改为 contextvars.ContextVar。
    Sprint 6 TODO: 迁移到 contextvars 实现。
    """
    
    _current: dict[str, Any] = {}

    @classmethod
    def set(cls, trace_id: str, symbol: str):
        cls._current = {"trace_id": trace_id, "symbol": symbol}

    @classmethod
    def get(cls) -> dict[str, Any]:
        return cls._current.copy()

    @classmethod
    def clear(cls):
        cls._current = {}