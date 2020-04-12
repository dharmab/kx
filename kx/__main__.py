#!/usr/bin/env python3
#
# This is the CLI entrypoint. It parses arguments and runs the various
# subcommands.

import argparse
import enum
import kx.configuration.cluster
import kx.configuration.project
import kx.logging
import kx.tooling
import os
import sys

logger = kx.logging.get_logger(__name__)


class Action(enum.Enum):
    "Enumerates the things this CLI tool can do."
    INSTALL_TOOLING = enum.auto()
    PREPARE_PROVIDER = enum.auto()
    CREATE_CLUSTER = enum.auto()
    DELETE_CLUSTER = enum.auto()
    CLEAN_PROVIDER = enum.auto()
    UNINSTALL_TOOLING = enum.auto()


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage a Kubernetes cluster")

    subparsers = parser.add_subparsers()

    prepare_provider_parser = subparsers.add_parser(
        "install-tooling", help="Install command-line tools"
    )
    prepare_provider_parser.set_defaults(action=Action.INSTALL_TOOLING)

    prepare_provider_parser = subparsers.add_parser(
        "prepare-provider", help="Prepare the infrastructure provider environment"
    )
    prepare_provider_parser.set_defaults(action=Action.PREPARE_PROVIDER)

    create_cluster_parser = subparsers.add_parser(
        "create-cluster", help="Create a Kubernetes cluster"
    )
    create_cluster_parser.set_defaults(action=Action.CREATE_CLUSTER)

    delete_cluster_parser = subparsers.add_parser(
        "delete-cluster", help="Delete a Kubernetes cluster"
    )
    delete_cluster_parser.set_defaults(action=Action.DELETE_CLUSTER)

    clean_provider_parser = subparsers.add_parser(
        "clean-provider", help="Clean the infrastructure provider environment"
    )
    clean_provider_parser.set_defaults(action=Action.CLEAN_PROVIDER)

    prepare_provider_parser = subparsers.add_parser(
        "uninstall-tooling", help="Uninstall command-line tools"
    )
    prepare_provider_parser.set_defaults(action=Action.UNINSTALL_TOOLING)

    return parser.parse_args()


def main() -> None:
    arguments = _parse_arguments()

    project_configuration = kx.configuration.project.ProjectConfiguration()

    configuration_path = os.getenv("CLUSTER_CONFIG")
    if not configuration_path:
        logger.error("CLUSTER_CONFIG not defined")
        sys.exit(0)

    logger.info(f"Loading configuration from {configuration_path}...")
    with open(configuration_path) as f:
        cluster_configuration = kx.configuration.cluster.load_cluster_configuration(f)

    provider: kx.infrastructure.InfrastructureProvider
    if cluster_configuration.provider == "Vagrant":
        from kx.vagrant.provider import Vagrant

        provider = Vagrant(
            project_configuration=project_configuration,
            cluster_configuration=cluster_configuration,
        )

    if arguments.action == Action.INSTALL_TOOLING:
        logger.info(f"Installing tools...")
        kx.tooling.install_tooling(project_configuration=project_configuration)
    elif arguments.action == Action.PREPARE_PROVIDER:
        logger.info(f"Preparing {cluster_configuration.provider} provider...")
        provider.prepare_provider()
    elif arguments.action == Action.CREATE_CLUSTER:
        logger.info(f"Creating {cluster_configuration.provider} cluster...")
        provider.create_cluster()
    elif arguments.action == Action.DELETE_CLUSTER:
        logger.info(f"Deleting {cluster_configuration.provider} cluster...")
        provider.delete_cluster()
    elif arguments.action == Action.CLEAN_PROVIDER:
        logger.info(f"Cleaning {cluster_configuration.provider} provider...")
        provider.clean_provider()
    elif arguments.action == Action.UNINSTALL_TOOLING:
        logger.info(f"Deleting tools...")
        kx.tooling.uninstall_tooling(project_configuration=project_configuration)
    else:
        logger.error(f"{arguments.action} is not a valid command")
        sys.exit(1)


if __name__ == "__main__":
    main()
