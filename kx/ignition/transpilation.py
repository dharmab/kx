#!/usr/bin/env python3

import json
import kx.logging
import subprocess
import yaml

logger = kx.logging.get_logger(__name__)


def transpile_ignition(fcc: dict) -> dict:
    try:
        fcct_process = subprocess.run(
            ["fcct", "--pretty", "--strict"],
            text=True,
            input=yaml.dump(fcc),
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"fcct process failed: {e.stderr}")
        raise
    return json.loads(fcct_process.stdout)
