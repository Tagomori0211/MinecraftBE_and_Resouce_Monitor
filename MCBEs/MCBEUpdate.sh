#!/bin/bash

# 設定
DEPLOYMENT_NAME="mc-bedrock"
NAMESPACE="default"
# ローカルバージョンファイルの場所（前回チェックしたバージョンを保存）
VERSION_FILE="/var/lib/minecraft-monitor/current_version.txt"

# 1. 最新バージョンの確認 (マイクラ公式サイトのヘッダー情報などをスクレイピング)
# ※ここでは例として、itzgイメージの最新タグが変わったかをチェックする仮定のロジック
# 実際には `curl` でMojangのページからバージョン文字列をgrepしてくるのが一般的
LATEST_VERSION=$(curl -s -I https://www.minecraft.net/en-us/download/server/bedrock | grep -i "bedrock-server-" | head -n 1)

# 初回起動時などのファイル作成
if [ ! -f "$VERSION_FILE" ]; then
    echo "$LATEST_VERSION" > "$VERSION_FILE"
    exit 0
fi

CURRENT_VERSION=$(cat "$VERSION_FILE")

# 2. アップデート検知
if [ "$LATEST_VERSION" != "$CURRENT_VERSION" ]; then
    echo "🚀 New version detected: $LATEST_VERSION"
    
    # Podの名前を取得（kubectl execするため）
    POD_NAME=$(kubectl get pods -l app=minecraft-bedrock -o jsonpath="{.items[0].metadata.name}")

    # 3. 【UX向上】チャットで予告通知 (RCONを使用)
    echo "📢 Sending chat notification..."
    
    # 20秒前の通知
    kubectl exec $POD_NAME -- rcon-cli say "§e[System] §cNew Update Detected!"
    kubectl exec $POD_NAME -- rcon-cli say "§e[System] §fServer will restart in §b20 seconds§f."
    
    sleep 10
    
    # 10秒前のカウントダウン（オプション）
    kubectl exec $POD_NAME -- rcon-cli say "§e[System] §fRestarting in §c10 seconds§f..."
    
    sleep 10
    
    # 直前の通知
    kubectl exec $POD_NAME -- rcon-cli say "§e[System] §cServer is restarting NOW. Back in ~1 min."
    
    # 4. 安全な停止と再起動
    # rollout restart を叩くと、k8sは自動で「新しいPod作成 -> 古いPod停止」を行う
    # ※Recreate戦略にしているので、一度停止してから新しいのが立ち上がる
    echo "🔄 Triggering rollout restart..."
    kubectl rollout restart deployment/$DEPLOYMENT_NAME
    
    # バージョン情報を更新
    echo "$LATEST_VERSION" > "$VERSION_FILE"
    
else
    echo "✅ No update found. (Current: $CURRENT_VERSION)"
fi