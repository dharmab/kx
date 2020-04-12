Vagrant.configure('2') do |config|
  box_file = File.join(File.dirname(__FILE__), 'vagrant', 'fedora-coreos.tar.gz')
  jump_ignition_file = File.join(File.dirname(__FILE__), 'vagrant', 'jump-ignition.json')

  config.vagrant.plugins = ["vagrant-libvirt"]

  config.vm.box = 'fedora-coreos'
  config.vm.box_url = "file://#{box_file}"
  config.vm.synced_folder '.', '/vagrant', disabled: true

  config.vm.provider :libvirt do |libvirt|
    libvirt.memory = 1024
    libvirt.cpus = 1
    libvirt.qemuargs :value => '-fw_cfg'
    libvirt.qemuargs :value => "name=opt/com.coreos/config,file=#{jump_ignition_file}"
    end
end
