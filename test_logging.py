"""
Test script for the effects logging system.

This script demonstrates the independent effects logger configuration
and shows how it can be controlled separately from the main simulator logger.
"""

import logging
from simulator.core.logging import setup_logging, effects_logger, logger


def test_basic_logging():
    """Test basic logging functionality."""
    print("=== Basic Logging Test ===")

    # Test with default levels
    setup_logging(logging.INFO)
    print("1. Default setup (INFO level):")
    logger.info("Main logger: INFO message")
    logger.debug("Main logger: DEBUG message (should not appear)")
    effects_logger.info("Effects logger: INFO message")
    effects_logger.debug("Effects logger: DEBUG message (should not appear)")

    print("\n2. With effects logger set to DEBUG:")
    setup_logging(logging.WARNING, {'simulator.effects': logging.DEBUG})
    logger.info("Main logger: INFO (should not appear - WARNING level)")
    logger.warning("Main logger: WARNING (should appear)")
    effects_logger.info("Effects logger: INFO (should appear - DEBUG allows INFO)")
    effects_logger.debug("Effects logger: DEBUG (should appear)")
    effects_logger.warning("Effects logger: WARNING (should appear)")


def test_independence():
    """Test that effects logger is independent from main logger."""
    print("\n=== Logger Independence Test ===")

    print("1. Main logger at ERROR, effects at INFO:")
    setup_logging(logging.ERROR, {'simulator.effects': logging.INFO})
    logger.warning("Main logger: WARNING (should not appear)")
    logger.error("Main logger: ERROR (should appear)")
    effects_logger.info("Effects logger: INFO (should appear)")
    effects_logger.debug("Effects logger: DEBUG (should not appear)")

    print("\n2. Main logger at DEBUG, effects at WARNING:")
    setup_logging(logging.DEBUG, {'simulator.effects': logging.WARNING})
    logger.debug("Main logger: DEBUG (should appear)")
    logger.info("Main logger: INFO (should appear)")
    effects_logger.info("Effects logger: INFO (should not appear - WARNING level)")
    effects_logger.warning("Effects logger: WARNING (should appear)")


def test_command_line_simulation():
    """Simulate command line usage."""
    print("\n=== Command Line Simulation ===")

    # Simulate: python main.py --log-level WARNING --effects-log-level DEBUG
    print("Simulating: --log-level WARNING --effects-log-level DEBUG")
    setup_logging(logging.WARNING, {'simulator.effects': logging.DEBUG})

    logger.info("Combat event (should not appear)")
    logger.warning("Important combat event (should appear)")

    effects_logger.debug("Effect application details (should appear)")
    effects_logger.info("Effect summary (should appear)")
    effects_logger.warning("Effect error (should appear)")


if __name__ == "__main__":
    test_basic_logging()
    test_independence()
    test_command_line_simulation()

    print("\n=== Test Complete ===")
    print("The effects logger is now available throughout the codebase as 'effects_logger'")
    print("and can be configured independently via --effects-log-level command line argument.")