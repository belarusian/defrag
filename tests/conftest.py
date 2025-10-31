"""
Pytest configuration for defrag tests.
"""

import logging
import sys


def pytest_configure(config):
    """Configure logging for tests."""
    # Set up logging - only WARNING and above
    logging.basicConfig(
        level=logging.WARNING,
        format="%(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
