"""Structured logging with Loguru."""
import sys
import io
from loguru import logger
from app.core.config import settings


def _make_safe_sink():
    """
    Returns a safe callable sink for loguru that handles the case where
    uvicorn's multiprocess reloader has closed stdout in the subprocess.
    Falls back to writing directly to the buffer with UTF-8 encoding on Windows
    to prevent emoji/cp1252 crashes.
    """
    # Try to get a UTF-8 wrapper around stdout buffer
    try:
        if hasattr(sys.stdout, "buffer") and not sys.stdout.closed:
            stream = io.TextIOWrapper(
                sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
            )
        else:
            stream = sys.stdout
    except Exception:
        stream = sys.stdout

    def _sink(message):
        try:
            stream.write(message)
            stream.flush()
        except (ValueError, OSError):
            # stdout is closed (happens in uvicorn subprocess reloader) — ignore silently
            pass

    return _sink


def setup_logging():
    logger.remove()
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    logger.add(
        _make_safe_sink(),
        format=log_format,
        level="DEBUG" if settings.DEBUG else "INFO",
        colorize=True,
    )
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        level="INFO",
        format=log_format,
        encoding="utf-8",
    )

