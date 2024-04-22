from flask import Flask, request, jsonify
import threading
import socket
import time
import redis
from jose import jwt, JWTError

app = Flask(__name__)
redis_conn = redis.Redis(host='redis', port=6379, db=0)
# host = 'tcp_server'
# port = 3000

# Update host to point to NGINX
host = 'nginx'
port = 81  # NGINX listens on port 81 for TCP traffic in the stream block

SECRET_KEY = "django-insecure-)v2*^p%@pzfpv9f@#c_fj_8zg2f+pgq%1uptaxei_i9$w=4xp0"  # Use the same key as configured in Django's SIMPLE_JWT settings
ALGORITHMS = ["HS256"]

def validate_token(auth_token):
    try:
        # Decode the token using the same secret key and algorithm used in Django
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=ALGORITHMS)
        return payload  # Returning the payload which includes user info
    except JWTError:
        return None

def send_data(user_id):
    client_socket = None
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
        while True:
            is_sending = redis_conn.get(f"{user_id}_is_sending")
            if is_sending and is_sending.decode() == 'True':
                MV = int(redis_conn.get(f"{user_id}_MV") or 1)
                current_value = int(redis_conn.get(f"{user_id}_current_value") or 0)
                current_value += MV
                redis_conn.set(f"{user_id}_current_value", current_value)
                message = f"{user_id}:{current_value}".encode()
                client_socket.send(message)
                time.sleep(1)
            else:
                time.sleep(1)
    except ConnectionRefusedError:
        print("No TCP server listening at", host, port)
    finally:
        if client_socket:
            client_socket.close()

@app.route('/command', methods=['POST'])
def command():
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith("Bearer "):
        auth_token = auth_header.split()[1]
        user_info = validate_token(auth_token)
        if user_info:
            user_id = str(user_info['user_id'])  # Assuming 'user_id' is part of the JWT payload
            data = request.get_json()
            if data and "command" in data:
                cmd = data["command"]
                if cmd == "start":
                    redis_conn.set(f"{user_id}_is_sending", 'True')
                    threading.Thread(target=send_data, args=(user_id,), daemon=True).start()
                    return jsonify({"status": "started"})
                elif cmd == "stop":
                    redis_conn.set(f"{user_id}_is_sending", 'False')
                    return jsonify({"status": "stopped"})
                elif cmd == "updateValue" and "MV" in data:
                    redis_conn.set(f"{user_id}_MV", data["MV"])
                    return jsonify({"status": "updated", "MV": data["MV"]})
            else:
                return jsonify({"error": "Invalid command"}), 400
        else:
            return jsonify({"error": "Unauthorized"}), 401
    else:
        return jsonify({"error": "Unauthorized - No token provided"}), 401

# if __name__ == '__main__':
#     app.run(debug=True, port=5000)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
