# Kubernetes X

## Up and Running

Install `make` and Python 3.

Set up a virtualenv and install the dependencies in `requirements.txt`.

### Vagrant

[Install vagrant-libvirt](https://github.com/vagrant-libvirt/vagrant-libvirt#installation).

Configure passwordless authentication for libvirt. Adding yourself to the
`libvirt` group is usually sufficient:

```bash
useradd -a -G libvirt $USER
```

Run `virt-manager` at least once to set up the default storage pool.

Configure the example configuration for Vagrant:

```bash
export CLUSTER_CONFIG=config/examples/vagrant.yaml
```

Run `make prepare-provider` to download Fedora CoreOS and package a Vagrant box.
