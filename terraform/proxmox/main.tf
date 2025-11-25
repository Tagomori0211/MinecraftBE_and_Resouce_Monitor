# ---------------------------------------------------------
# 1. DevOps VM (Linked Clone)
# ---------------------------------------------------------
resource "proxmox_vm_qemu" "devops_vm" {
  name        = "dev-ops-vm"
  target_node = "pve"
  clone       = "ubuntu-2204-cloudinit-template"
  
  full_clone = false

  cores   = 4
  sockets = 1
  memory  = 8192
  scsihw  = "virtio-scsi-pci"
  bootdisk = "scsi0"

  disk {
    slot     = "scsi0"      # 【修正】0 -> "scsi0"
    size     = "32G"
    type     = "disk"       # 【修正】"scsi" -> "disk"
    storage  = "local-lvm"
    iothread = true
  }

  network {
    id     = 0
    model  = "virtio"
    bridge = "vmbr0"
  }

  os_type = "cloud-init"
  ipconfig0 = "ip=192.168.0.21/24,gw=192.168.0.1"
  ciuser  = "tagomori"
  cipassword = "password123"
  sshkeys = <<EOF
  ${var.ssh_public_key}
  EOF
}

# ---------------------------------------------------------
# 2. Minecraft VM (Full Clone)
# ---------------------------------------------------------
resource "proxmox_vm_qemu" "mcbe_server_vm" {
  name        = "mcbe-server-vm"
  target_node = "pve"
  clone       = "ubuntu-2204-cloudinit-template"

  full_clone = true

  cores   = 4
  sockets = 1
  memory  = 16384
  scsihw  = "virtio-scsi-pci"
  bootdisk = "scsi0"

  disk {
    slot     = "scsi0"      # 【修正】0 -> "scsi0"
    size     = "50G"
    type     = "disk"       # 【修正】"scsi" -> "disk"
    storage  = "local-lvm"
    iothread = true
  }

  network {
    id     = 0
    model  = "virtio"
    bridge = "vmbr0"
  }

  os_type = "cloud-init"
  ipconfig0 = "ip=192.168.0.20/24,gw=192.168.0.1"
  ciuser  = "tagomori"
  cipassword = "password123"
  sshkeys = <<EOF
  ${var.ssh_public_key}
  EOF
}
