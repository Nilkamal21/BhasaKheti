import logging
import sys


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Quiet overly chatty loggers if needed
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    return logging.getLogger("bhasakheti")


logger = setup_logging()
