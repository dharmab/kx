#!/usr/bin/env python3

import io
import json
import kx.configuration.cluster
import kx.configuration.project
import kx.ignition.fcc
import kx.ignition.transpilation
import kx.infrastructure
import kx.logging
import kx.utility
import kx.vagrant.commands
import lzma
import pathlib
import requests
import tarfile
import time

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


class Vagrant(kx.infrastructure.InfrastructureProvider):
    def __init__(
        self,
        *,
        project_configuration: kx.configuration.project.ProjectConfiguration,
        cluster_configuration: kx.configuration.cluster.ClusterConfiguration,
    ):
        self.__project_configuration = project_configuration
        self.__cluster_configuration = cluster_configuration

    @staticmethod
    def box_directory_path() -> pathlib.Path:
        return kx.utility.project_directory().joinpath("vagrant/")

    def prepare_provider(self) -> None:
        # Preparation: We need to create a vagrant-libvirtd Fedora CoreOS box

        # Create directory for Vagrant Box
        box_directory_path = Vagrant.box_directory_path()
        if not box_directory_path.exists():
            logger.info(
                f"Creating directory {box_directory_path} to store Vagrant box..."
            )
            box_directory_path.mkdir(parents=True)
        assert box_directory_path.is_dir()

        box_file_path = box_directory_path.joinpath(
            f"fedora-coreos-{self.__project_configuration.operating_system_version}.tar.gz"
        )
        if not box_file_path.exists():
            # Download the Fedora CoreOS QEMU image
            download_url = f"https://builds.coreos.fedoraproject.org/prod/streams/stable/builds/{self.__project_configuration.operating_system_version}/x86_64/fedora-coreos-{self.__project_configuration.operating_system_version}-qemu.x86_64.qcow2.xz"
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
        box_symlink_path = box_directory_path.joinpath("fedora-coreos.tar.gz")

        logger.info(f"Updating symbolic link {box_symlink_path}...")
        if box_symlink_path.exists():
            box_symlink_path.unlink()
        box_symlink_path.symlink_to(box_file_path)

        logger.info("Vagrant ready to launch!")

    def __generate_ignition_file(self, role: str, *, ignition_data: dict) -> None:
        ignition_path = Vagrant.box_directory_path().joinpath(f"{role}-ignition.json")
        logger.info(f"Generating {ignition_path}...")
        if ignition_path.exists():
            ignition_path.unlink()
        with open(ignition_path, "w") as f:
            json.dump(ignition_data, f)

    def __generate_ignition_files(self) -> None:
        # Write Ignition files to disk where libvirt can see them
        logger.info("Generating Ignition data...")

        # An extra jump box is needed as a utility host
        jump_ignition_data = kx.ignition.transpilation.transpile_ignition(
            kx.utility.merge_complex_dictionaries(
                kx.ignition.fcc.skeletal_fcc(), self.__generate_vagrant_fcc_overlay()
            )
        )
        self.__generate_ignition_file("jump", ignition_data=jump_ignition_data)

        etcd_ignition_data = kx.ignition.transpilation.transpile_ignition(
            kx.utility.merge_complex_dictionaries(
                kx.ignition.fcc.generate_common_etcd_fcc(
                    cluster_configuration=self.__cluster_configuration
                ),
                self.generate_etcd_fcc_overlay(
                    cluster_configuration=self.__cluster_configuration
                ),
            )
        )
        self.__generate_ignition_file("etcd", ignition_data=etcd_ignition_data)

        master_ignition_data = kx.ignition.transpilation.transpile_ignition(
            kx.utility.merge_complex_dictionaries(
                kx.ignition.fcc.generate_common_master_fcc(
                    cluster_configuration=self.__cluster_configuration
                ),
                self.generate_master_fcc_overlay(
                    cluster_configuration=self.__cluster_configuration
                ),
            )
        )
        self.__generate_ignition_file("master", ignition_data=master_ignition_data)

    def launch_cluster(self) -> None:
        self.__generate_ignition_files()
        logger.info("Launching virtual machines...")
        kx.vagrant.commands.vagrant_up()
        logger.info("Virtual machines launched! Use `vagrant ssh`")

    def delete_cluster(self) -> None:
        logger.info("Destroying virtual machines...")
        kx.vagrant.commands.vagrant_destroy()

    def clean_provider(self) -> None:
        box_directory_path = Vagrant.box_directory_path()
        logger.info(f"Cleaning {box_directory_path}...")
        for box_path in box_directory_path.glob("fedora-coreos*.tar.gz"):
            logger.info(f"Deleting {box_path}...")
            box_path.unlink()
        for ignition_path in box_directory_path.glob("*-ignition.json"):
            logger.info(f"Deleting {ignition_path}...")
            ignition_path.unlink()

    def __generate_vagrant_fcc_overlay(self) -> dict:
        return {
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
                    {
                        "path": "/etc/sudoers.d/vagrant",
                        "contents": {"inline": "vagrant ALL=(ALL) NOPASSWD: ALL"},
                    }
                ]
            },
        }

    def generate_etcd_fcc_overlay(
        self, cluster_configuration: kx.configuration.cluster.ClusterConfiguration
    ) -> dict:
        return self.__generate_vagrant_fcc_overlay()

    def generate_master_fcc_overlay(
        self, cluster_configuration: kx.configuration.cluster.ClusterConfiguration
    ) -> dict:
        return self.__generate_vagrant_fcc_overlay()

    def generate_worker_fcc_overlay(
        self,
        pool_name: str,
        cluster_configuration: kx.configuration.cluster.ClusterConfiguration,
    ) -> dict:
        return self.__generate_vagrant_fcc_overlay()
