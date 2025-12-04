from flask import Flask, jsonify
import requests
import os

app = Flask(__name__)

# PrometheusのURL定義
PROMETHEUS_URL = "http://prometheus:9090"

def query_prometheus(query):
    """
    Prometheus APIにクエリを投げ、結果の最初の要素を返すヘルパー関数
    """
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={'query': query})
        data = response.json()
        if data["status"] == "success" and len(data["data"]["result"]) > 0:
            return data["data"]["result"][0]
        return None
    except Exception as e:
        print(f"Error querying Prometheus: {e}")
        return None

@app.route('/')
def hello():
    return jsonify({"message": "Minecraft Monitor API OK", "status": "Running"})

@app.route('/api/status')
def get_status():
    # -------------------------------------------------
    # 1. Prometheusから全メトリクス収集
    # -------------------------------------------------
    
    # 【修正】オンライン人数の取得ロジック変更
    # log_watcher.py は 'minecraft_player_online_status' (1=Online, 0=Offline) をユーザーごとに出力します。
    # そのため、sum() を使って value が 1 の合計値を計算することでオンライン人数を算出します。
    #
    online_query = 'sum(minecraft_player_online_status)' 
    online_res = query_prometheus(online_query)

    # 既存のエクスポーター(Port 30001)が生きていればそこから最大人数を取得
    # なければデフォルト値や別途設定が必要ですが、一旦既存維持
    max_res = query_prometheus('minecraft_status_players_max_count')
    
    # サーバーの健全性（バージョン情報など）
    healthy_res = query_prometheus('minecraft_status_healthy')
    
    # 応答速度
    ping_res = query_prometheus('minecraft_status_response_time_seconds')

    # リソース情報 (cAdvisor)
    cpu_query = 'sum(rate(container_cpu_usage_seconds_total{container_label_io_kubernetes_container_name="minecraft"}[1m])) * 100'
    cpu_res = query_prometheus(cpu_query)

    mem_query = 'sum(container_memory_working_set_bytes{container_label_io_kubernetes_container_name="minecraft"})'
    mem_res = query_prometheus(mem_query)

    limit_query = 'sum(container_spec_memory_limit_bytes{container_label_io_kubernetes_container_name="minecraft"})'
    limit_res = query_prometheus(limit_query)

    # -------------------------------------------------
    # 2. データの整形
    # -------------------------------------------------
    # 初期値の設定
    players_online = 0
    players_max = 0
    version = "Unknown"
    latency = 0
    status_text = "Offline"
    
    cpu_usage = "N/A"
    mem_usage_str = "N/A"
    mem_limit_str = "N/A"
    mem_percent_str = ""

    # オンライン判定ロジック
    # online_res が取得できた時点で、Prometheusまでデータが来ている＝監視システムは正常
    if online_res:
        status_text = "Online"
        
        # クエリ結果の値を整数化 (例: "1" -> 1)
        players_online = int(float(online_res['value'][1]))
        
        # バージョン情報 (既存のエクスポーター依存)
        if healthy_res and 'metric' in healthy_res:
            version = healthy_res['metric'].get('server_version', 'Unknown')
            
        # 最大人数 (既存のエクスポーター依存)
        if max_res:
            players_max = int(max_res['value'][1])
            
        # Ping (秒 -> ミリ秒)
        if ping_res:
            val = float(ping_res['value'][1])
            latency = int(val * 1000)
    else:
        # データが取れない場合でも、log-watcherが動いていれば '0' が返る可能性がある。
        # 全く取れない場合はPrometheus接続エラーか、データ未着。
        pass

    # CPU使用率の整形
    if cpu_res:
        val = float(cpu_res['value'][1])
        cpu_usage = f"{val:.1f}%"
    
    # メモリ使用量の整形
    mem_val = 0
    limit_val = 0
    
    if mem_res:
        mem_val = float(mem_res['value'][1])
        # Byte -> MB 変換
        mem_usage_str = f"{mem_val / 1048576:.0f} MB"
        
    if limit_res:
        limit_val = float(limit_res['value'][1])
        # Byte -> GB 変換
        mem_limit_str = f"{limit_val / 1073741824:.1f} GB"

    if mem_val > 0 and limit_val > 0:
        percent = (mem_val / limit_val) * 100
        mem_percent_str = f"({percent:.1f}%)"

    # -------------------------------------------------
    # 3. レスポンス生成
    # -------------------------------------------------
    return jsonify({
        "status": status_text,
        "players": {
            "online": players_online,
            "max": players_max
        },
        "server": {
            "version": version,
            "latency": latency,
            "cpu_usage": cpu_usage,
            "memory_usage": mem_usage_str,
            "memory_limit": mem_limit_str,
            "memory_percent": mem_percent_str
        }
    })

if __name__ == '__main__':
    # 開発用サーバー起動
    app.run(host='0.0.0.0', port=5000)