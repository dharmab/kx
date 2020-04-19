#!/usr/bin/env python3
#
# The module contains the main implementation of the Vagrant infrastructure
# provider.

import io
import ipaddress
import json
import kx.configuration
import kx.ignition.fcc
import kx.ignition.transpilation
import kx.infrastructure
import kx.logging
import kx.utility
import kx.vagrant.commands
import lzma
import requests
import tarfile
import time
import typing
import yarl

logger = kx.logging.get_logger(__name__)

# https://github.com/vagrant-libvirt/vagrant-libvirt/blob/master/example_box/Vagrantfile
LIBVIRT_VAGRANTFILE = """
Vagrant.configure("2") do |config|
  config.vm.provider :libvirt do |libvirt|
    libvirt.driver = "kvm"
    libvirt.connect_via_ssh = false
    libvirt.username = "root"
    libvirt.storage_pool_name = "default"
  end
end
"""


class Vagrant(
    kx.infrastructure.InfrastructureProvider,
    kx.ignition.fcc.FedoraCoreOSConfigurationProvider,
):
    def __init__(
        self, *, cluster_configuration: kx.configuration.ClusterConfiguration,
    ):
        self.__cluster_configuration = cluster_configuration

    def prepare_provider(self) -> None:
        # Preparation: We need to create a vagrant-libvirtd Fedora CoreOS box

        # Create directory for Vagrant Box
        box_directory_path = kx.utility.project_directory().joinpath("vagrant/boxes")
        if not box_directory_path.exists():
            box_directory_path.mkdir(parents=True)
        assert box_directory_path.is_dir()

        box_file_path = box_directory_path.joinpath(
            f"fedora-coreos-{self.__cluster_configuration.operating_system_version}.tar.gz"
        )
        if not box_file_path.exists():
            # Download the Fedora CoreOS QEMU image
            download_url = f"https://builds.coreos.fedoraproject.org/prod/streams/stable/builds/{self.__cluster_configuration.operating_system_version}/x86_64/fedora-coreos-{self.__cluster_configuration.operating_system_version}-qemu.x86_64.qcow2.xz"
            logger.info(f"Downloading {download_url}...")
            response = requests.get(download_url)
            response.raise_for_status()
            # TODO verify hash
            logger.info("Extracting image...")
            image = lzma.LZMADecompressor().decompress(data=response.content)

            # Package the QEMU image in vagrant-libvirt format
            # https://github.com/vagrant-libvirt/vagrant-libvirt#box-format
            logger.info(f"Packaging {box_file_path}...")
            with tarfile.open(name=box_file_path, mode="w:gz") as a:

                def add_file_to_tarball(name: str, data: bytes):
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.mode = 0o644
                    info.mtime = int(time.time())
                    a.addfile(info, io.BytesIO(data))

                add_file_to_tarball("box.img", image)

                # https://github.com/vagrant-libvirt/vagrant-libvirt/tree/master/example_box#box-metadata
                metadata = {
                    "provider": "libvirt",
                    "format": "qcow2",
                    "virtual_size": 16,
                }
                add_file_to_tarball("metadata.json", str.encode(json.dumps(metadata)))

                add_file_to_tarball("Vagrantfile", str.encode(LIBVIRT_VAGRANTFILE))

        # Create a stable symlink to the box so we don't have to update the
        # box URL in the project's Vagrantfile
        box_symlink_path = box_directory_path.joinpath("fedora-coreos.tar.gz")
        logger.info(f"Updating symbolic link {box_symlink_path}...")
        if box_symlink_path.exists():
            box_symlink_path.unlink()
        box_symlink_path.symlink_to(box_file_path)

        logger.info("Vagrant ready to launch!")

    def __generate_ignition_file(self, role: str, *, ignition_data: dict) -> None:
        ignition_path = kx.utility.project_directory().joinpath(
            f"vagrant/ignition/{role}-ignition.json"
        )
        logger.info(f"Generating {ignition_path}...")
        if ignition_path.exists():
            ignition_path.unlink()
        with open(ignition_path, "w") as f:
            json.dump(ignition_data, f)

    def create_blob_storage(self) -> None:
        for directory in ("ignition", "tls"):
            path = kx.utility.project_directory().joinpath(f"vagrant/{directory}/")
            if not path.exists():
                logger.info(f"Creating {path}...")
                path.mkdir()
            assert path.is_dir()

    def create_network_resources(self) -> None:
        load_balancer_ignition_data = kx.ignition.transpilation.transpile_ignition(
            self.__generate_load_balancer_configuration()
        )
        load_balancer_ignition_path = kx.utility.project_directory().joinpath(
            "vagrant/ignition/load-balancer-ignition.json"
        )
        logger.info(f"Writing {load_balancer_ignition_path}...")
        with open(load_balancer_ignition_path, "w") as f:
            json.dump(load_balancer_ignition_data, f)

        logger.info("Running `vagrant up load-balancer`...")
        kx.vagrant.commands.vagrant_up("load-balancer")

    def create_cluster(self) -> None:
        logger.info("Creating virtual machines...")
        kx.vagrant.commands.vagrant_up()
        logger.info("Show VMs with `vagrant status`")
        logger.info("SSH to a VM with `vagrant ssh`")

    def delete_cluster(self) -> None:
        logger.info("Destroying virtual machines...")
        kx.vagrant.commands.vagrant_destroy()
        ignition_directory_path = kx.utility.project_directory().joinpath(
            "vagrant/ignition"
        )
        for file_path in ignition_directory_path.glob("*-ignition.json"):
            logger.info(f"Deleting {file_path}...")
            file_path.unlink()

    def query_etcd_peer_names(
        self,
    ) -> typing.List[typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
        # IP addresses are hardcoded in Vagrantfile
        return [
            ipaddress.IPv4Address(ip)
            for ip in ("10.13.13.2", "10.13.13.3", "10.13.13.4")
        ]

    def query_etcd_server_names(
        self,
    ) -> typing.List[typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
        return self.query_etcd_peer_names() + [ipaddress.IPv4Address("10.13.13.5")]

    def query_apiserver_names(
        self,
    ) -> typing.List[
        typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address, yarl.URL]
    ]:
        # IP addresses are hardcoded in Vagrantfile
        return [
            ipaddress.IPv4Address(ip)
            for ip in ("10.13.13.5", "10.13.13.6", "10.13.13.7", "10.13.13.8")
        ]

    def upload_tls_certificates(
        self,
        *,
        etcd_pki: kx.tls.pki.EtcdPublicKeyInfrastructure,
        kubernetes_pki: kx.tls.pki.KubernetesPublicKeyInfrastructure,
    ) -> kx.tls.pki.PublicKeyInfrastructureCatalog:
        base_url = yarl.URL("http://10.13.1.5:8080/tls/")

        tls_directory = kx.utility.project_directory().joinpath("vagrant/tls")

        def write_file(filename: str, content: str) -> yarl.URL:
            with open(tls_directory.joinpath(filename), "w") as f:
                f.write(content)
            return base_url.join(yarl.URL(filename))

        return kx.tls.pki.PublicKeyInfrastructureCatalog(
            kubernetes_certificate_authority=write_file(
                "kubernetes-ca.pem", kubernetes_pki.certificate_authority.public_key
            ),
            kubernetes_signing_key=write_file(
                "kubernetes_ca.key", kubernetes_pki.certificate_authority.private_key
            ),
            apiserver_certificate=write_file(
                "kube-apiserver.pem", kubernetes_pki.apiserver_keypair.public_key
            ),
            apiserver_private_key=write_file(
                "kube-apierver.key", kubernetes_pki.apiserver_keypair.private_key
            ),
            controller_manager_certificate=write_file(
                "kube-controller-manager.pem",
                kubernetes_pki.controller_manager_keypair.public_key,
            ),
            controller_manager_private_key=write_file(
                "kube-controller-manager.key",
                kubernetes_pki.controller_manager_keypair.private_key,
            ),
            scheduler_certificate=write_file(
                "kube-scheduler.pem", kubernetes_pki.scheduler_keypair.public_key
            ),
            scheduler_private_key=write_file(
                "kube-scheduler.key", kubernetes_pki.scheduler_keypair.private_key
            ),
            etcd_certificate_authority=write_file(
                "etcd-ca.pem", etcd_pki.certificate_authority.public_key
            ),
            etcd_peer_certificate=write_file(
                "etcd-peer.pem", etcd_pki.etcd_peer_keypair.public_key
            ),
            etcd_peer_private_key=write_file(
                "etcd-peer.key", etcd_pki.certificate_authority.private_key
            ),
            etcd_server_certificate=write_file(
                "etcd-server.pem", etcd_pki.etcd_server_keypair.public_key
            ),
            etcd_server_private_key=write_file(
                "etcd-server.key", etcd_pki.etcd_server_keypair.private_key
            ),
            etcd_apiserver_client_certificate=write_file(
                "etcd-kube-apiserver-client.pem",
                etcd_pki.etcd_apiserver_client_keypair.private_key,
            ),
            etcd_apiserver_client_private_key=write_file(
                "etcd-kube-apiserver-client.key",
                etcd_pki.etcd_apiserver_client_keypair.private_key,
            ),
        )

    def upload_ignition_data(
        self,
        *,
        etcd_ignition_data: str,
        master_ignition_data: str,
        worker_ignition_data: typing.Dict[str, str],
    ) -> kx.infrastructure.IgnitionURLCatalog:
        ignition_path = kx.utility.project_directory().joinpath("vagrant/ignition/")

        etcd_path = ignition_path.joinpath("etcd-ignition.json")
        with open(etcd_path, 'w') as f:
            logger.info(f"Writing {etcd_path}...")
            f.write(etcd_ignition_data)

        master_path = ignition_path.joinpath("master-ignition.json")
        with open(master_path, 'w') as f:
            logger.info(f"Writing {master_path}...")
            f.write(master_ignition_data)

        # TODO multiworker
        worker_path = ignition_path.joinpath("worker-ignition.json")
        with open(worker_path, 'w') as f:
            logger.info(f"Writing {worker_path}...")
            f.write(worker_ignition_data["worker"])

        # Ignition distributed through filesystem, so catalog is a no-op
        return kx.infrastructure.IgnitionURLCatalog(
            etcd_ignition_url=yarl.URL("http://example.com"),
            master_ignition_url=yarl.URL("http://example.com"),
            worker_ignition_urls={
                n: yarl.URL("http://example.com") for n in worker_ignition_data
            },
        )

    def create_compute_resources(
        self, *, ignition_data: kx.infrastructure.Ignition
    ) -> None:
        logger.info("Running `vagrant up`...")
        kx.vagrant.commands.vagrant_up()

    def clean_provider(self) -> None:
        box_directory_path = kx.utility.project_directory().joinpath("vagrant/boxes")
        logger.info(f"Cleaning {box_directory_path}...")
        for box_path in box_directory_path.glob("fedora-coreos*.tar.gz"):
            logger.info(f"Deleting {box_path}...")
            box_path.unlink()

    def __generate_base_fcc_configuration(self) -> dict:
        return {
            "variant": "fcos",
            "version": "1.0.0",
            "ignition": {},
            "passwd": {
                "users": [
                    {
                        "name": "vagrant",
                        "ssh_authorized_keys": [
                            "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA6NF8iallvQVp22WDkTkyrtvp9eWW6A8YVr+kz4TjGYe7gHzIw+niNltGEFHzD8+v1I2YJ6oXevct1YeS0o9HZyN1Q9qgCgzUFtdOKLv6IedplqoPkcmF0aYet2PkEDo3MlTBckFXPITAMzF8dJSIFo9D8HfdOV0IAdx4O7PtixWKn5y2hMNG0zQPyUecp4pzC6kivAIhyfHilFR61RGL+GPXQ2MWZWFYbAGjyiYJnAmCP3NOTd0jMZEnDkbUvxhMmBYSdETk1rRgm+R4LOzFUGaHqHDLKLX+FIPKcF96hrucXzcWyLbIbEgE98OHlnVYCzRdK8jlqm8tehUc9c9WhQ== vagrant insecure public key"
                        ],
                    }
                ]
            },
            "storage": {
                "files": [
                    kx.ignition.fcc.file_from_content(
                        "/etc/selinux/config",
                        kx.ignition.fcc.content_from_lines(
                            "SELINUX=permissive", "SELINUXTYPE=targeted"
                        ),
                    ),
                    kx.ignition.fcc.file_from_content(
                        "/etc/sudoers.d/vagrant",
                        contents=kx.ignition.fcc.content_from_lines(
                            "vagrant ALL=(ALL) NOPASSWD: ALL"
                        ),
                    )
                ]
            },
        }

    def __generate_load_balancer_configuration(self) -> dict:
        return kx.utility.merge_complex_dictionaries(
            self.generate_worker_configuration(pool_name="worker"),
            {
                "systemd": {
                    "units": [
                        {
                            "name": "nginx.service",
                            "enabled": True,
                            "contents": kx.ignition.fcc.content_from_repository(
                                "systemd/vagrant/nginx-l4.service"
                            ),
                        }
                    ]
                },
                "storage": {
                    "files": [
                        kx.ignition.fcc.file_from_content(
                            "/etc/nginx/nginx.conf",
                            contents=kx.ignition.fcc.content_from_repository(
                                "files/vagrant/nginx-l4.conf"
                            ),
                        ),
                    ]
                },
            },
        )

    def generate_etcd_configuration(self) -> dict:
        return self.__generate_base_fcc_configuration()

    def generate_master_configuration(self) -> dict:
        storage_fcc = kx.utility.merge_complex_dictionaries(
            self.__generate_base_fcc_configuration(),
            {
            },
        )
        return storage_fcc

    def generate_worker_configuration(self, *, pool_name) -> dict:
        return self.__generate_base_fcc_configuration()
