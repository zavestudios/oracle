"""Main application entry point for oracle."""

import os
import logging

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """Main application logic."""
    logger.info("Starting oracle...")

    # TODO: Implement your application logic here

    logger.info("oracle is running")


if __name__ == "__main__":
    main()
