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

  # 【修正】vga設定 (これはOK)
  vga {
    type = "std"
  }

  # 【削除】cloudinit_cdrom_storage = "local-lvm" は消す！

  # 【追加】Cloud-Initドライブを disk ブロックとして定義！
  disk {
    slot    = "ide2"
    type    = "cloudinit"
    storage = "local-lvm"
  }

  # メインディスク
  disk {
    slot     = "scsi0"
    size     = "32G"
    type     = "disk"
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

  # 【修正】vga設定
  vga {
    type = "std"
  }

  # 【追加】Cloud-Initドライブ
  disk {
    slot    = "ide2"
    type    = "cloudinit"
    storage = "local-lvm"
  }

  # メインディスク
  disk {
    slot     = "scsi0"
    size     = "50G"
    type     = "disk"
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
# main.tf の末尾に追記

# ---------------------------------------------------------
# 3. Dev Workstation (新しい開発拠点 / code-server)
# ---------------------------------------------------------
resource "proxmox_vm_qemu" "dev_workstation" {
  name        = "dev-workstation"
  target_node = "pve"
  clone       = "ubuntu-2204-cloudinit-template"
  
  full_clone = true # 開発機なので独立させる

  # 自宅サーバーの富豪スペックを活かす！
  cores   = 8       # 8コア！
  sockets = 1
  memory  = 32768   # 32GB RAM！ (GCWより強い！)
  scsihw  = "virtio-scsi-pci"
  bootdisk = "scsi0"

  # 画面設定
  vga {
    type = "std"
  }

  # Cloud-Initドライブ
  disk {
    slot    = "ide2"
    type    = "cloudinit"
    storage = "local-lvm"
  }

  # メインディスク (開発用なので少し大きめに)
  disk {
    slot     = "scsi0"
    size     = "100G"
    type     = "disk"
    storage  = "local-lvm"
    iothread = true
  }

  network {
    id     = 0
    model  = "virtio"
    bridge = "vmbr0"
  }

  os_type = "cloud-init"
  # 固定IP: .22 を割り当て
  ipconfig0 = "ip=192.168.0.22/24,gw=192.168.0.1"
  ciuser  = "tagomori"
  cipassword = "password123"
  sshkeys = <<EOF
  ${var.ssh_public_key}
  EOF
}