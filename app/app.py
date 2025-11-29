from flask import Flask, jsonify
import requests
import os
from mcstatus import BedrockServer
import socket

app = Flask(__name__)

# PrometheusのURL
PROMETHEUS_URL = "http://prometheus:9090"

# マイクラサーバーの接続情報 (DevOps VMから見たIP)
MC_SERVER_IP = "192.168.0.20"
MC_SERVER_PORT = 30000

def query_prometheus(query):
    """
    Prometheusからデータを取得するヘルパー関数
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

def get_real_status():
    """
    mcstatusを使ってサーバーに直接問い合わせる関数
    """
    try:
        server = BedrockServer.lookup(f"{MC_SERVER_IP}:{MC_SERVER_PORT}")
        # 【修正】タイムアウトを 3.0秒 に延長！ (UDPは不安定なため)
        status = server.status(timeout=3.0)
        return status
    except Exception as e:
        # 【追加】失敗理由をログに出力 (docker compose logs app で確認可能に)
        print(f"MCStatus Error: {e}")
        return None

@app.route('/')
def hello():
    return jsonify({"message": "Minecraft Monitor API OK", "status": "Running"})

@app.route('/api/status')
def get_status():
    # 1. Prometheusからメトリクス収集
    online_res = query_prometheus('minecraft_status_players_online_count')
    max_res = query_prometheus('minecraft_status_players_max_count')
    
    cpu_query = 'sum(rate(container_cpu_usage_seconds_total{container_label_io_kubernetes_container_name="minecraft"}[1m])) * 100'
    cpu_res = query_prometheus(cpu_query)

    mem_query = 'sum(container_memory_working_set_bytes{container_label_io_kubernetes_container_name="minecraft"})'
    mem_res = query_prometheus(mem_query)

    limit_query = 'sum(container_spec_memory_limit_bytes{container_label_io_kubernetes_container_name="minecraft"})'
    limit_res = query_prometheus(limit_query)

    # 2. データの整形
    players_online = 0
    players_max = 0
    version = "Unknown"
    latency = 0
    status_text = "Offline"
    
    cpu_usage = "N/A"
    mem_usage_str = "N/A"
    mem_limit_str = "N/A"
    mem_percent_str = ""

    # mcstatusで生データを取得
    mc_status = get_real_status()
    
    if mc_status:
        status_text = "Online"
        version = mc_status.version.name
        latency = int(mc_status.latency * 1000) 
        
        # プレイヤー数: Prometheus優先、なければmcstatus
        if online_res:
            players_online = int(online_res['value'][1])
        else:
            players_online = mc_status.players_online
            
        if max_res:
            players_max = int(max_res['value'][1])
        else:
            players_max = mc_status.players_max
            
    else:
        # フォールバック処理 (mcstatus失敗時)
        if online_res:
            status_text = "Online"
            players_online = int(online_res['value'][1])
            version = "Detecting..." 
            
            # 【バグ修正】ここで最大人数もPrometheusから取る！
            if max_res:
                players_max = int(max_res['value'][1])

    # CPU整形
    if cpu_res:
        val = float(cpu_res['value'][1])
        cpu_usage = f"{val:.1f}%"
    
    # メモリ整形
    mem_val = 0
    limit_val = 0
    
    if mem_res:
        mem_val = float(mem_res['value'][1])
        mem_usage_str = f"{mem_val / 1048576:.0f} MB"
        
    if limit_res:
        limit_val = float(limit_res['value'][1])
        mem_limit_str = f"{limit_val / 1073741824:.1f} GB"

    if mem_val > 0 and limit_val > 0:
        percent = (mem_val / limit_val) * 100
        mem_percent_str = f"({percent:.1f}%)"

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
    app.run(host='0.0.0.0', port=5000)