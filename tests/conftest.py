"""
Pytest configuration for defrag tests.
"""

import logging
import sys


def pytest_configure(config):
    """Configure logging for tests."""
    # Set up logging to show API connection details
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    # Ensure defrag logger outputs
    logger = logging.getLogger("defrag")
    logger.setLevel(logging.DEBUG)
