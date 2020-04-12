ENV["TERM"] = "xterm-256color"
ENV["LC_ALL"] = "en_US.UTF-8"

Vagrant.configure('2') do |config|
  box_file = File.join(File.dirname(__FILE__), 'vagrant', 'fedora-coreos.tar.gz')
  etcd_ignition_file = File.join(File.dirname(__FILE__), 'vagrant', 'etcd-ignition.json')
  master_ignition_file = File.join(File.dirname(__FILE__), 'vagrant', 'master-ignition.json')
  worker_ignition_file = File.join(File.dirname(__FILE__), 'vagrant', 'worker-ignition.json')

  config.vagrant.plugins = ["vagrant-libvirt"]

  config.vm.box = 'fedora-coreos'
  config.vm.box_url = "file://#{box_file}"
  config.vm.synced_folder '.', '/vagrant', disabled: true

  for i in 0..2
    config.vm.define "etcd-#{i}" do |etcd|
      etcd.vm.network "private_network", ip: "10.13.13.#{i}"
      config.vm.provider :libvirt do |libvirt|
        libvirt.cpus = 1
        libvirt.memory = 2048
        libvirt.qemuargs :value => '-fw_cfg'
        libvirt.qemuargs :value => "name=opt/com.coreos/config,file=#{etcd_ignition_file}"
      end
    end
  end

  for i in 0..1
    config.vm.define "master-#{i}" do |etcd|
      config.vm.provider :libvirt do |libvirt|
        libvirt.cpus = 1
        libvirt.memory = 1024
        libvirt.qemuargs :value => '-fw_cfg'
        libvirt.qemuargs :value => "name=opt/com.coreos/config,file=#{master_ignition_file}"
      end
    end
  end
end
