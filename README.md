# Kubernetes X

An experimental project for managing opinionated multi-tenant Kubernetes
clusters across multiple clouds.

## Up and Running

Install `make` and Python.

Install `fcct` and `kubectl`. See [the tools README](bin/README.md) for a quick
install method.

Set up a virtualenv and install the dependencies in `requirements.txt`.

### Vagrant

Make sure you have ~6GB of free RAM.

[Install Vagrant, libvirt, QEMU and
vagrant-libvirt](https://github.com/vagrant-libvirt/vagrant-libvirt#installation).

Configure passwordless authentication for libvirt. Adding yourself to the
`libvirt` group is usually sufficient:

```bash
useradd -a -G libvirt $USER
```

Run `virt-manager` at least once to set up the default storage pool.

Configure the example configuration for Vagrant:

```bash
export CLUSTER_CONFIG=$(pwd)/config/examples/vagrant.yaml
```

Run `make prepare-provider` to download Fedora CoreOS and package a Vagrant
box.

Run `make create-cluster` to launch the cluster.
