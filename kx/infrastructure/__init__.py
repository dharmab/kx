#!/usr/bin/env python3
#
# This module contains cross-provider interfaces.

import abc
import enum


class NodeRole(enum.Enum):
    ETCD = enum.auto()
    MASTER = enum.auto()
    WORKER = enum.auto()


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
    def create_cluster(self) -> None:
        """
        This function is called when a cluster is initially created. It should
        create all of the cluster's infrastructure.

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
