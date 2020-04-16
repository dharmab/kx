#!/usr/bin/env python3
#
# This module contains utility functions for logging.

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Get a module-scoped logger which logs to stdout. This function must always
    be invoked as follows:

    get_logger(__name__)
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)s %(filename)s:%(lineno)d %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
