#!/usr/bin/env python3

import abc
import kx.configuration.cluster


class InfrastructureProvider(abc.ABC):
    @abc.abstractmethod
    def prepare_provider(self) -> None:
        pass

    @abc.abstractmethod
    def launch_cluster(self) -> None:
        pass

    @abc.abstractmethod
    def delete_cluster(self) -> None:
        pass

    @abc.abstractmethod
    def clean_provider(self) -> None:
        pass

    @abc.abstractmethod
    def generate_etcd_fcc_overlay(self, *, cluster_configuration: kx.configuration.cluster.ClusterConfiguration) -> dict:
        pass
