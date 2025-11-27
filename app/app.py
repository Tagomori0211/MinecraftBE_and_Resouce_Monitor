from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return jsonify({
        "message": "Hello from DevOps VM!",
        "status": "Running",
        "pod": os.uname().nodename
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)