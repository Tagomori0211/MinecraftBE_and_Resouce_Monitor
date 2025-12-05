from flask import Flask, jsonify
import requests
import os

app = Flask(__name__)

# PrometheusのURL定義 (Docker Compose内のサービス名解決)
PROMETHEUS_URL = "http://prometheus:9090"

def query_prometheus(query):
    """
    Prometheus APIにクエリを投げ、結果の最初の要素を返すヘルパー関数
    Args:
        query (str): PromQLクエリ文字列
    Returns:
        dict or None: 取得したメトリクスデータ、失敗時はNone
    """
    try:
        # PrometheusのAPIエンドポイントへGETリクエスト
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={'query': query})
        data = response.json()
        # ステータスがsuccessかつデータが存在する場合のみ返す
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
    # 1. Prometheusからメトリクス収集 (mc-monitor由来を優先)
    # -------------------------------------------------
    
    # [A] オンライン人数 (mc-monitor: Port 30001)
    # 以前のバージョンで動作実績のある mc-monitor の数値を正とします。
    # Log Watcherは補助的な役割（誰が入ったか等）で使用可能です。
    online_res = query_prometheus('minecraft_status_players_online_count')
    
    # [B] 最大人数 (mc-monitor)
    max_res = query_prometheus('minecraft_status_players_max_count')
    
    # [C] サーバーの健全性とバージョン (mc-monitor)
    # このメトリクスは {version="1.20.xx", ...} というラベルを持っています。
    healthy_res = query_prometheus('minecraft_status_healthy')
    
    # [D] 応答速度 Ping (mc-monitor)
    # 秒単位で返ってくるため、後でミリ秒に変換します。
    ping_res = query_prometheus('minecraft_status_response_time_seconds')

    # [E] リソース情報 (cAdvisor: Port 30002)
    # CPU使用率 (%)
    cpu_query = 'sum(rate(container_cpu_usage_seconds_total{container_label_io_kubernetes_container_name="minecraft"}[1m])) * 100'
    cpu_res = query_prometheus(cpu_query)

    # メモリ使用量 (Bytes)
    mem_query = 'sum(container_memory_working_set_bytes{container_label_io_kubernetes_container_name="minecraft"})'
    mem_res = query_prometheus(mem_query)

    # メモリ制限値 (Bytes)
    limit_query = 'sum(container_spec_memory_limit_bytes{container_label_io_kubernetes_container_name="minecraft"})'
    limit_res = query_prometheus(limit_query)

    # -------------------------------------------------
    # 2. データの整形
    # -------------------------------------------------
    # 初期値 (Offline想定)
    players_online = 0
    players_max = 0
    version = "Unknown"
    latency = 0
    status_text = "Offline"
    
    cpu_usage = "N/A"
    mem_usage_str = "N/A"
    mem_limit_str = "N/A"
    mem_percent_str = ""

    # --- ステータス判定ロジック ---
    # minecraft_status_healthy が 1 であればオンラインとみなす
    is_online = False
    
    if healthy_res:
        # 値を取得 (文字列なのでfloat経由でintへ)
        val = int(float(healthy_res['value'][1]))
        if val == 1:
            is_online = True
            status_text = "Online"
            
            # バージョン情報の抽出 (Prometheusのラベルから)
            # mc-monitorのバージョンによってラベルキーが異なる場合があるため安全策を取る
            if 'metric' in healthy_res:
                version = healthy_res['metric'].get('version', 'Unknown') 
                if version == 'Unknown':
                    version = healthy_res['metric'].get('server_version', 'Unknown')

    # オンライン時の追加データ取得処理
    if is_online:
        # 人数取得
        if online_res:
            players_online = int(float(online_res['value'][1]))
        
        # 最大人数
        if max_res:
            players_max = int(float(max_res['value'][1]))
            
        # Ping (秒 -> ミリ秒変換)
        if ping_res:
            val = float(ping_res['value'][1])
            latency = int(val * 1000)

    # --- リソース整形 (Grafana用データのAPI提供) ---
    if cpu_res:
        val = float(cpu_res['value'][1])
        cpu_usage = f"{val:.1f}%"
    
    if mem_res:
        mem_val = float(mem_res['value'][1])
        mem_usage_str = f"{mem_val / 1048576:.0f} MB" # MB変換
        
    if limit_res:
        limit_val = float(limit_res['value'][1])
        mem_limit_str = f"{limit_val / 1073741824:.1f} GB" # GB変換

    # メモリ使用率の計算
    if mem_res and limit_res:
        m_val = float(mem_res['value'][1])
        l_val = float(limit_res['value'][1])
        if l_val > 0:
            percent = (m_val / l_val) * 100
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
    # 開発環境用起動設定 (本番はGunicorn経由)
    app.run(host='0.0.0.0', port=5000)