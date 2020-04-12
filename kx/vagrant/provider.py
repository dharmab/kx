#!/usr/bin/env python3

from kx import infrastructure
from kx import utility
from kx import log
import kx.configuration.cluster
import kx.ignition.transpilation
import kx.ignition.fcc
import pathlib
import kx.configuration.project
import requests
import lzma
import tarfile
import io
import json
import time


logger = log.get_logger(__name__)

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


class Vagrant(infrastructure.InfrastructureProvider):
    def __init__(self, *, project_configuration: kx.configuration.project.ProjectConfiguration, cluster_configuration: kx.configuration.cluster.ClusterConfiguration):
        self.__project_configuration = project_configuration
        self.__cluster_configuration = cluster_configuration

    @staticmethod
    def box_directory_path() -> pathlib.Path:
        return utility.project_directory().joinpath("vagrant/")

    def prepare_provider(self) -> None:
        # Preparation: We need to create a vagrant-libvirtd Fedora CoreOS box

        # Create directory for Vagrant Box
        box_directory_path = Vagrant.box_directory_path()
        if not box_directory_path.exists():
            logger.info(f"Creating directory {box_directory_path} to store Vagrant box...")
            box_directory_path.mkdir(parents=True)
        assert box_directory_path.is_dir()

        box_file_path = box_directory_path.joinpath(f"fedora-coreos-{self.__project_configuration.operating_system_version}.tar.gz")
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

    def launch_cluster(self) -> None:
        # Write Ignition files to disk where libvirt can see them
        jump_ignition_path = Vagrant.box_directory_path().joinpath("jump-ignition.json")
        logger.info(f"Generating {jump_ignition_path}")
        jump_ignition = kx.ignition.transpilation.transpile_ignition(utility.merge_complex_dictionaries(
            kx.ignition.fcc.skeletal_fcc(),
            self.__generate_vagrant_fcc_overlay()
        ))
        with open(jump_ignition_path, 'w') as f:
            json.dump(jump_ignition, f)
        jump_ignition_path.chmod(0o600)

        etcd_ignition = kx.ignition.transpilation.transpile_ignition(utility.merge_complex_dictionaries(
            kx.ignition.fcc.generate_common_etcd_fcc(self.__cluster_configuration),
            self.generate_etcd_fcc_overlay(self.__cluster_configuration)
        ))

        etcd_ignition_path = Vagrant.box_directory_path().joinpath("etcd-ignition.json")
        logger.info(f"Generating {etcd_ignition_path}")
        with open(etcd_ignition_path, 'w') as f:
            json.dump(etcd_ignition, f)
        etcd_ignition_path.chmod(0o600)

    def delete_cluster(self) -> None:
        raise NotImplementedError

    def clean_provider(self) -> None:
        box_directory_path = Vagrant.box_directory_path()
        logger.info(f"Cleaning {box_directory_path}...")
        for box_path in box_directory_path.glob("fedora-coreos-*.tar.gz"):
            logger.info(f"Deleting {box_path}...")
            box_path.unlink()
        for ignition_path in box_directory_path.glob("*-ignition.json"):
            logger.info(f"Deleting {ignition_path}...")
            ignition_path.unlink()

    def __generate_vagrant_fcc_overlay(self) -> dict:
        return {
            "passwd": {
                "users": [{
                    "name": "vagrant",
                    "ssh_authorized_keys": [
                        "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA6NF8iallvQVp22WDkTkyrtvp9eWW6A8YVr+kz4TjGYe7gHzIw+niNltGEFHzD8+v1I2YJ6oXevct1YeS0o9HZyN1Q9qgCgzUFtdOKLv6IedplqoPkcmF0aYet2PkEDo3MlTBckFXPITAMzF8dJSIFo9D8HfdOV0IAdx4O7PtixWKn5y2hMNG0zQPyUecp4pzC6kivAIhyfHilFR61RGL+GPXQ2MWZWFYbAGjyiYJnAmCP3NOTd0jMZEnDkbUvxhMmBYSdETk1rRgm+R4LOzFUGaHqHDLKLX+FIPKcF96hrucXzcWyLbIbEgE98OHlnVYCzRdK8jlqm8tehUc9c9WhQ== vagrant insecure public key"
                    ]
                }]
            },
            'storage': {
                'files': [
                    {
                        "path": '/etc/sudoers.d/vagrant',
                        "contents": {
                            "inline": "vagrant ALL=(ALL) NOPASSWD: ALL"
                        }
                    }
                ]
            }
        }

    def generate_etcd_fcc_overlay(self, cluster_configuration: kx.configuration.cluster.ClusterConfiguration) -> dict:
        return self.__generate_vagrant_fcc_overlay()
