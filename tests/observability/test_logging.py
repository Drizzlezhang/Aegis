import json
import logging
from src.observability.logging import JSONFormatter, TraceContext, setup_logging


def test_json_formatter_output():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="test message",
        args=(),
        exc_info=None
    )
    
    output = formatter.format(record)
    parsed = json.loads(output)
    
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_logger"
    assert parsed["message"] == "test message"
    assert "timestamp" in parsed


def test_trace_context_set_get_clear():
    TraceContext.clear()
    assert TraceContext.get() == {}
    
    TraceContext.set("trace-123", "AAPL")
    ctx = TraceContext.get()
    
    assert ctx["trace_id"] == "trace-123"
    assert ctx["symbol"] == "AAPL"
    
    TraceContext.clear()
    assert TraceContext.get() == {}


def test_setup_logging_json_mode():
    setup_logging(level="DEBUG", json_output=True)
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    
    # Root logger should have one handler with JSONFormatter
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, JSONFormatter)