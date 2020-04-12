#!/usr/bin/env python3

import kx.utility
import kx.logging
import requests
import dataclasses
import typing


logger = kx.logging.get_logger(__name__)


@dataclasses.dataclass()
class Tool:
    filename: str
    download_url: str

    def __post_init__(self):
        self.path = kx.utility.project_directory().joinpath(f"bin/{self.filename}")


def _tools_registry() -> typing.Tuple[Tool, ...]:
    return (
        Tool(
            filename="fcct",
            download_url="https://github.com/coreos/fcct/releases/download/v0.5.0/fcct-x86_64-unknown-linux-gnu",
        ),
    )


def install_tooling() -> None:
    for tool in _tools_registry():
        if not tool.path.exists():
            logger.info(f"Downloading {tool.path}...")
            response = requests.get(tool.download_url)
            response.raise_for_status()
            logger.info(f"Installing {tool.path}...")
            with open(tool.path, "wb") as f:
                f.write(response.content)
        tool.path.chmod(0o755)


def uninstall_tooling() -> None:
    for tool in _tools_registry():
        if tool.path.exists():
            logger.info(f"Uninstalling {tool.path}...")
            tool.path.unlink()
