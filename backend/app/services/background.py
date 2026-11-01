import logging
import threading

from django.conf import settings
from django.db import close_old_connections

log = logging.getLogger(__name__)


def run(fn, *args) -> None:
    """Run `fn(*args)` after the response is sent: on a daemon thread, or inline when BACKGROUND_SYNC is set (tests)."""
    if settings.BACKGROUND_SYNC:
        fn(*args)
        return

    def target() -> None:
        try:
            fn(*args)
        except Exception:  # noqa: BLE001 - a background thread must not die silently
            log.exception("background task %s failed", getattr(fn, "__name__", fn))
        finally:
            close_old_connections()

    threading.Thread(target=target, daemon=True).start()
