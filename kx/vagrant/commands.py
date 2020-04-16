#!/usr/bin/env python3

import kx.logging
import subprocess
import typing

logger = kx.logging.get_logger(__name__)


def _run_vagrant(*args) -> None:
    command: typing.List[typing.Any] = ["vagrant"] + list(args)
    try:
        subprocess.run(command, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Vagrant command failed: \n{command=} \n{e.stdout=} \n{e.stderr=}".replace(
                "\\n", "\n"
            )
        )
        raise


def vagrant_up(*args) -> None:
    _run_vagrant("up", "--provider", "libvirt", "--parallel", *args)


def vagrant_destroy() -> None:
    _run_vagrant("destroy", "--force", "--parallel")
