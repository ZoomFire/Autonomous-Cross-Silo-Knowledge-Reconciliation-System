import logging

from config import LOG_LEVEL


def configure_logging() -> logging.Logger:
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    return logging.getLogger("driftguard")


logger = configure_logging()

