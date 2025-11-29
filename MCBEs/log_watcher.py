from kubernetes import client, config, watch
import re
import datetime

# K8s内部(Pod内)で動くための設定読み込み
# これだけでServiceAccountのトークンを使って認証してくれる！
config.load_incluster_config()

v1 = client.CoreV1Api()
w = watch.Watch()

# 監視対象のラベル (マイクラサーバーのラベルに合わせてね)
POD_LABEL_SELECTOR = "app=minecraft-bedrock" 
NAMESPACE = "default"

print(f"👀 Start watching logs for pods with label: {POD_LABEL_SELECTOR}")

# Pod名を探す
pods = v1.list_namespaced_pod(NAMESPACE, label_selector=POD_LABEL_SELECTOR)
if not pods.items:
    print("❌ Minecraft Pod not found!")
    exit(1)

pod_name = pods.items[0].metadata.name
print(f"🎯 Target Pod found: {pod_name}")

# ストリーミング開始！ (tail -f みたいなもの)
for line in w.stream(v1.read_namespaced_pod_log, name=pod_name, namespace=NAMESPACE, follow=True):
    log_line = line.strip()
    
    # --- ここに解析ロジックを書く！ ---
    
    # パターンA: ログイン検知
    if "Player connected" in log_line:
        # 例: [2025-11-30 08:00:00 INFO] Player Tagomori connected: xuid:...
        # 正規表現でユーザー名を抽出
        match = re.search(r"Player (.+) connected", log_line)
        if match:
            user = match.group(1)
            print(f"✅ LOGIN DETECTED: {user} at {datetime.datetime.now()}")
            # TODO: ここでDevOps VMのDBやPrometheusにデータを飛ばす！

    # パターンB: ログアウト検知
    elif "Player disconnected" in log_line:
        match = re.search(r"Player (.+) disconnected", log_line)
        if match:
            user = match.group(1)
            print(f"🚪 LOGOUT DETECTED: {user} at {datetime.datetime.now()}")
            # TODO: ここで滞在時間を計算して送信！
