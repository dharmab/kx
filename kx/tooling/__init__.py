#!/usr/bin/env python3
#
# This package manages installation of some extra command lines tools needed by
# the project.

import dataclasses
import kx.configuration.project
import kx.logging
import kx.utility
import requests
import typing

logger = kx.logging.get_logger(__name__)


@dataclasses.dataclass()
class Tool:
    "Contains metadata about a CLI tool"
    # Name of the tool's binary
    filename: str
    # The tool's website
    homepage: str
    # The URL to download the tool
    download_url: str

    def __post_init__(self):
        self.path = kx.utility.project_directory().joinpath(f"bin/{self.filename}")


def _tools_registry(
    *, project_configuration: kx.configuration.project.ProjectConfiguration
) -> typing.Tuple[Tool, ...]:
    return (
        Tool(
            filename="fcct",
            homepage="https://docs.fedoraproject.org/en-US/fedora-coreos/using-fcct/",
            download_url="https://github.com/coreos/fcct/releases/download/v0.5.0/fcct-x86_64-unknown-linux-gnu",
        ),
        Tool(
            filename="kubectl",
            homepage="https://kubernetes.io/docs/reference/kubectl/overview/",
            download_url=f"https://storage.googleapis.com/kubernetes-release/release/v{project_configuration.kubernetes_version}/bin/linux/amd64/kubectl",
        ),
    )


def install_tooling(
    *, project_configuration: kx.configuration.project.ProjectConfiguration
) -> None:
    for tool in _tools_registry(project_configuration=project_configuration):
        if not tool.path.exists():
            logger.info(f"Downloading {tool.path}...")
            response = requests.get(tool.download_url)
            response.raise_for_status()
            logger.info(f"Installing {tool.path}...")
            with open(tool.path, "wb") as f:
                f.write(response.content)
        tool.path.chmod(0o755)


def uninstall_tooling(
    *, project_configuration: kx.configuration.project.ProjectConfiguration
) -> None:
    for tool in _tools_registry(project_configuration=project_configuration):
        if tool.path.exists():
            logger.info(f"Uninstalling {tool.path}...")
            tool.path.unlink()
