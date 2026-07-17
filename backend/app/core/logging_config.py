import json
import logging
import sys
from contextvars import ContextVar

RESERVED_LOG_RECORD_ATTRS = set(logging.makeLogRecord({}).__dict__.keys())

# Set by the request-id middleware around each HTTP request; unset (None) in the
# scheduler/worker processes, which have no request context of their own.
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in RESERVED_LOG_RECORD_ATTRS and key != "message":
                if key == "request_id" and value is None:
                    continue
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(RequestIdFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
