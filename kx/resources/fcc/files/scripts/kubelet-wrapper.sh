#!/bin/bash
#
# Wraps the Kubelet process with startup logic

. /etc/profile

# Delay execution until the hostname has been configured to something other
# than localhost.
echo "Waiting for hostname configuration..."
until [[ ! $(hostname) =~ ^localhost.*$ ]]; do
  sleep .1
done

# If necessary, extract CNI binaries
if [[ ! -f /opt/cni/bin/portmap ]]; then
  echo "Extracting CNI binaries..."
  tar xvf /opt/cni/bin/cni-plugins.tar.gz -C /opt/cni/bin
fi

# Configure the node IP. Usually, the node IP is the IP address that is the
# preferred source of the default route.
underlay_subnet=default
# vagrant-libvirt VMs have multiple NICs; we prefer the private networking NIC.
if [[ $CLOUD_PROVIDER == "Vagrant" ]]; then
  underlay_subnet=10.13.13.0/24
fi
node_ip=$(ip -json route show to $underlay_subnet | jq -r .[].prefsrc)
echo "Using Node IP: $node_ip"

echo "Starting Kubelet..."
exec /opt/kubernetes/bin/kubelet \
  --cert-dir=/etc/kubernetes/tls \
  --config=/etc/kubernetes/kubelet.yaml \
  --container-runtime=docker \
  --network-plugin=cni \
  --node-ip="$node_ip"
