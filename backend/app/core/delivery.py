class DeliverySendError(Exception):
    """Base for channel-specific send failures (email, webhook, ...). The
    worker's retry/backoff/dead-letter logic catches this, not the individual
    subclasses, so adding a new channel never requires touching worker.py's
    except clause."""
