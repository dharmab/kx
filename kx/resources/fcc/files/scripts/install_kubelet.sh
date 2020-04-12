#!/bin/bash

kubernetes_version="{{project_configuration.kubernetes_version}}"

download_directory=$(mktemp -d)
filename=kubernetes-node-linux-amd64.tar.gz
url="https://dl.k8s.io/v$kubernetes_version/$filename"
download_destination=$download_directory/$filename

function cleanup() {
  rm -rf "$download_directory"
}

trap cleanup SIGINT SIGTERM

if ! [[ -f /opt/kubernetes/bin/kubelet ]]; then
  echo "Downloading $url..."
  until curl -sL "$url" -o "$download_destination"; do
    sleep 1
  done

  echo "Extracting $filename..."
  if ! tar xf "$download_destination" -C /opt/kubernetes/bin --strip-components 3 kubernetes/node/bin; then
    echo "An error occurred while extracting $download_destination"
    exit 1
  fi
fi

cleanup
