#!/bin/bash

download_directory=$(mktemp -d)
filename=kubernetes-node-linux-amd64.tar.gz
download_destination=$download_directory/$filename
url="https://dl.k8s.io/v$KUBERNETES_VERSION/$filename"

if ! [[ -f /opt/kubernetes/bin/kubelet ]]; then
  echo "Downloading $url..."
  until curl -sL "https://dl.k8s.io/v$KUBERNETES_VERSION/$filename" -o "$download_destination"; do
    sleep 1
  done

  echo "Extracting $filename..."
  if ! tar xf "$download_destination" -C /opt/kubernetes/bin kubernetes/node/bin; then
    echo "An error occurred while extracting $download_destination"
    exit 1
  fi
fi
