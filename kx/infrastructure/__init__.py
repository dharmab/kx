#!/usr/bin/env python3
#
# This module contains cross-provider interfaces.

import abc
import dataclasses
import enum
import ipaddress
import kx.tls.pki
import typing
import yarl


@dataclasses.dataclass
class IgnitionURLCatalog:
    etcd_ignition_url: yarl.URL
    master_ignition_url: yarl.URL
    worker_ignition_urls: typing.Dict[str, yarl.URL]


@dataclasses.dataclass
class IgnitionReference:
    url: yarl.URL
    stable_hash: str
    verification_hash: str


@dataclasses.dataclass
class Ignition:
    etcd: IgnitionReference
    master: IgnitionReference
    worker: typing.Dict[str, IgnitionReference]


class InfrastructureProvider(abc.ABC):
    """
    Abstract class which must be implemented by an infrastructure provider.
    """

    @abc.abstractmethod
    def prepare_provider(self) -> None:
        """
        This function is called prior to cluster launch and is intended for
        infrequent setup actions, such as baking OS images and enabling cloud
        features.

        This function must be idempotent.
        """
        pass

    @abc.abstractmethod
    def create_blob_storage(self) -> None:
        """
        This function is called when a cluster is initially created. It should
        create the cluster's blob storage infrastructure.

        This function may be non-idempotent.
        """
        pass

    @abc.abstractmethod
    def create_network_resources(self) -> None:
        """
        This function is called when a cluster is initially created. It should
        create all of the cluster's network infrastructure.

        This function may be non-idempotent.
        """
        pass

    @abc.abstractmethod
    def query_etcd_peers(
        self,
    ) -> typing.Dict[str, typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
        """
        Return a dict mapping the names of all etcd peers in the cluster to
        their corresponding etcd peer IP addresses
        """
        pass

    @abc.abstractmethod
    def query_etcd_server_names(
        self,
    ) -> typing.List[typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
        """
        Return a list of all etcd server IP addresses in the cluster. This
        should include both the etcd Nodes and the etcd load balancer.
        """
        pass

    @abc.abstractmethod
    def query_apiserver_names(
        self,
    ) -> typing.List[
        typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address, yarl.URL]
    ]:
        """
        Return a list of all Kubernetes API IP addresses and URLs in the cluster.
        This should include the apiserver load balancer, but should not include
        the apiserver Nodes.
        """
        pass

    @abc.abstractmethod
    def upload_ignition_data(
        self,
        *,
        etcd_ignition_data: str,
        master_ignition_data: str,
        worker_ignition_data: typing.Dict[str, str]
    ) -> IgnitionURLCatalog:
        """
        Upload the given Ignition data to a blob storage provider. Return a
        catalog of URLs from which the Ignition data may be downloaded. The
        catalog should contain only secure URLs, e.g. signed URLs.
        """
        pass

    @abc.abstractmethod
    def create_compute_resources(self, *, ignition_data: Ignition) -> None:
        """
        This function is called when a cluster is initially created. It should
        create all of the cluster's compute infrastructure.

        This function may be non-idempotent.
        """
        pass

    @abc.abstractmethod
    def delete_cluster(self) -> None:
        """
        This function is called when a cluster is deleted. It should
        delete all of the cluster's infrastructure.

        This function must be idempotent.
        """
        pass

    @abc.abstractmethod
    def clean_provider(self) -> None:
        """
        This function should delete any infrastructure or files created by
        prepare_provider() or not deleted by delete_cluster().

        This function must be idempotent.
        """
        pass
