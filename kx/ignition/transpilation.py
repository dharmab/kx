#!/usr/bin/env python3

import json
import kx.logging
import subprocess
import yaml

logger = kx.logging.get_logger(__name__)


def transpile_ignition(fcc: dict) -> dict:
    assert _is_fcc_valid(fcc)
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


def _is_fcc_valid(fcc: dict) -> bool:
    file_paths = set()
    for _file in fcc.get("storage", {}).get("files", []):
        path = _file["path"]
        if path in file_paths:
            logger.error(f"Found duplicate file path: {path}")
            return False
        file_paths.add(path)
    return True
