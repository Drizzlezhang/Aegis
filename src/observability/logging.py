"""Structured JSON logging for Aegis-Trader."""

import contextvars
import json
import logging
import sys
from datetime import UTC
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
        from datetime import datetime
        dt = datetime.fromtimestamp(record.created, tz=UTC)
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


_trace_var: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "trace_context", default=None
)


class TraceContext:
    """Pipeline trace context — per-task isolation via contextvars."""

    @classmethod
    def set(cls, trace_id: str, symbol: str) -> None:
        _trace_var.set({"trace_id": trace_id, "symbol": symbol})

    @classmethod
    def get(cls) -> dict[str, Any]:
        ctx = _trace_var.get()
        return ctx.copy() if ctx is not None else {}

    @classmethod
    def clear(cls) -> None:
        _trace_var.set({})
