#!/usr/bin/env python3
#
# This is the CLI entrypoint. It parses arguments and runs the various
# subcommands.

import argparse
import enum
import json
import kx.configuration
import kx.ignition.fcc
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

    configuration_path = os.getenv("CLUSTER_CONFIG")
    if not configuration_path:
        logger.error("CLUSTER_CONFIG not defined")
        sys.exit(0)

    logger.info(f"Loading configuration from {configuration_path}...")
    with open(configuration_path) as f:
        cluster_configuration = kx.configuration.load_cluster_configuration(f)

    provider: kx.infrastructure.InfrastructureProvider
    if cluster_configuration.provider == "Vagrant":
        from kx.vagrant.provider import Vagrant

        provider = Vagrant(cluster_configuration=cluster_configuration,)

    if arguments.action == Action.INSTALL_TOOLING:
        logger.info(f"Installing tools...")
        kx.tooling.install_tooling(cluster_configuration=cluster_configuration)
    elif arguments.action == Action.PREPARE_PROVIDER:
        logger.info(f"Preparing {cluster_configuration.provider} provider...")
        provider.prepare_provider()
    elif arguments.action == Action.CREATE_CLUSTER:
        logger.info(f"Creating {cluster_configuration.provider} cluster...")

        logger.info(f"Creating blob storage infrastructure...")
        provider.create_blob_storage()

        logger.info("Creating network infrastructure...")
        provider.create_network_resources()

        logger.info("Generating Ignition data...")
        universal_fcc_provider = kx.ignition.fcc.UniversalFCCProvider(
            cluster_configuration=cluster_configuration,
            etcd_peers=provider.query_etcd_peers(),
        )
        unstable_fcc_provider = kx.ignition.fcc.UnstableFCCProvider(
            etcd_pki=kx.tls.pki.create_etcd_pki(
                etcd_peer_ip_addresses=list(provider.query_etcd_peers().values()),
                etcd_server_ip_addresses=provider.query_etcd_server_names(),
            ),
            kubernetes_pki=kx.tls.pki.create_kubernetes_pki(
                apiserver_names=provider.query_apiserver_names(),
            ),
        )

        stable_etcd_ignition_data = kx.utility.merge_complex_dictionaries(
            universal_fcc_provider.generate_etcd_configuration(),
            provider.generate_etcd_configuration(),
        )
        stable_etcd_ignition_hash = kx.utility.sha512_hash(stable_etcd_ignition_data)
        etcd_ignition_data = kx.ignition.transpilation.transpile_ignition(
            kx.utility.merge_complex_dictionaries(
                stable_etcd_ignition_data,
                unstable_fcc_provider.generate_etcd_configuration(),
            )
        )
        etcd_ignition_verification_hash = kx.utility.sha512_hash(etcd_ignition_data)

        stable_master_ignition_data = kx.utility.merge_complex_dictionaries(
            universal_fcc_provider.generate_master_configuration(),
            provider.generate_master_configuration(),
        )
        stable_master_ignition_hash = kx.utility.sha512_hash(
            stable_master_ignition_data
        )
        master_ignition_data = kx.ignition.transpilation.transpile_ignition(
            kx.utility.merge_complex_dictionaries(
                stable_master_ignition_data,
                unstable_fcc_provider.generate_master_configuration(),
            )
        )
        master_ignition_verification_hash = kx.utility.sha512_hash(master_ignition_data)

        worker_pool_names = ["worker"]
        worker_ignition_data = {}
        worker_stable_hashes = {}
        worker_verification_hashes = {}
        for pool_name in worker_pool_names:
            stable_worker_ignition_data = kx.utility.merge_complex_dictionaries(
                unstable_fcc_provider.generate_worker_configuration(
                    pool_name=pool_name
                ),
                provider.generate_worker_configuration(pool_name=pool_name),
            )
            worker_stable_hashes[pool_name] = kx.utility.sha512_hash(
                stable_worker_ignition_data
            )
            worker_ignition_data[
                pool_name
            ] = kx.ignition.transpilation.transpile_ignition(
                kx.utility.merge_complex_dictionaries(
                    stable_worker_ignition_data,
                    unstable_fcc_provider.generate_worker_configuration(
                        pool_name=pool_name
                    ),
                )
            )
            worker_verification_hashes[pool_name] = kx.utility.sha512_hash(
                worker_ignition_data
            )

        logger.info("Uploading Ignition data...")
        ignition_urls = provider.upload_ignition_data(
            etcd_ignition_data=json.dumps(etcd_ignition_data),
            master_ignition_data=json.dumps(master_ignition_data),
            worker_ignition_data={
                k: json.dumps(v) for k, v in worker_ignition_data.items()
            },
        )

        logger.info("Launching compute infrastructure...")
        provider.create_compute_resources(
            ignition_data=kx.infrastructure.Ignition(
                etcd=kx.infrastructure.IgnitionReference(
                    url=ignition_urls.etcd_ignition_url,
                    stable_hash=stable_etcd_ignition_hash,
                    verification_hash=etcd_ignition_verification_hash,
                ),
                master=kx.infrastructure.IgnitionReference(
                    url=ignition_urls.master_ignition_url,
                    stable_hash=stable_master_ignition_hash,
                    verification_hash=master_ignition_verification_hash,
                ),
                worker={
                    n: kx.infrastructure.IgnitionReference(
                        url=ignition_urls.worker_ignition_urls[n],
                        stable_hash=worker_stable_hashes[pool_name],
                        verification_hash=worker_verification_hashes[pool_name],
                    )
                    for n in worker_pool_names
                },
            )
        )

        logger.info(f"{cluster_configuration.provider} cluster created!")
    elif arguments.action == Action.DELETE_CLUSTER:
        logger.info(f"Deleting {cluster_configuration.provider} cluster...")
        provider.delete_cluster()
    elif arguments.action == Action.CLEAN_PROVIDER:
        logger.info(f"Cleaning {cluster_configuration.provider} provider...")
        provider.clean_provider()
    elif arguments.action == Action.UNINSTALL_TOOLING:
        logger.info(f"Deleting tools...")
        kx.tooling.uninstall_tooling(cluster_configuration=cluster_configuration)
    else:
        logger.error(f"{arguments.action} is not a valid command")
        sys.exit(1)


if __name__ == "__main__":
    main()
