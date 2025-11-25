variable "proxmox_api_token_id" {
  type        = string
  description = "Proxmox API Token ID (ex: root@pam!terraform)"
}

variable "proxmox_api_token_secret" {
  type        = string
  sensitive   = true # ログに出力されないように保護
  description = "Proxmox API Secret"
}
variable "ssh_public_key" {
  type        = string
  description = "Public SSH Key for VMs"
}
