terraform {
  required_providers {
    proxmox = {
      source  = "telmate/proxmox"
      version = "3.0.1-rc6" # 安定版を指定
    }
  }
}

provider "proxmox" {
  # 自宅ProxmoxのTailscale URL (ポート8006と /api2/json が重要！)
  pm_api_url = "https://127.0.0.1:8006/api2/json"

  # さっき取得したトークン情報 (変数はあとで注入するよ！)
  pm_api_token_id     = var.proxmox_api_token_id
  pm_api_token_secret = var.proxmox_api_token_secret

  # 自宅サーバーの証明書エラーを無視する (Tailscale経由なら安全！)
  pm_tls_insecure = true

  pm_timeout = 1200   # 20分まで待つ設定
  pm_parallel = 1
}
