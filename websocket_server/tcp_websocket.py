import asyncio
import websockets
import aioredis

websocket_clients = []

# Initialize Redis connection asynchronously
async def get_redis():
    # Connect to Redis using a URL
    return await aioredis.from_url("redis://127.0.0.1:6379", encoding="utf-8", decode_responses=True)

async def handle_tcp_client(reader, writer, redis_conn):
    port = writer.get_extra_info('peername')[1]
    print(f"New TCP client connected on port {port}")
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                print(f"Received no data from TCP client on port {port}. Closing connection.")
                break
            message = data.decode()
            print(f"Received from TCP client on port {port}: {message}")

            # Fetch user-specific multiplier MV from Redis
            user_id, _, message_content = message.partition(':')
            MV = await redis_conn.get(f"{user_id}_MV")
            MV = int(MV) if MV else 1

            # Generate and send the next value based on MV
            current_value = int(message_content)
            next_value = current_value + MV
            message_to_send = f"{user_id}:{next_value}"

            # Forward the new message to all WebSocket clients
            if websocket_clients:
                print(f"Forwarding message to {len(websocket_clients)} WebSocket clients.")
                for ws in websocket_clients:
                    await ws.send(message_to_send)
            else:
                print("No WebSocket clients connected to forward the message.")
    except Exception as e:
        print(f"TCP client error on port {port}: {e}")
    finally:
        print(f"Closing TCP client connection on port {port}")
        writer.close()

async def tcp_server(port, redis_conn):
    server = await asyncio.start_server(
        lambda r, w: handle_tcp_client(r, w, redis_conn), '0.0.0.0', port)
    print(f"TCP server listening on 0.0.0.0:{port}")
    async with server:
        await server.serve_forever()

async def websocket_server(websocket, path):
    print(f"New WebSocket client connected: {websocket.remote_address}")
    websocket_clients.append(websocket)
    try:
        await websocket.wait_closed()
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        print(f"WebSocket client disconnected: {websocket.remote_address}")
        websocket_clients.remove(websocket)

async def main():
    redis_conn = await get_redis()
    print("Starting TCP servers and WebSocket server")
    await asyncio.gather(
        tcp_server(3000, redis_conn),
        tcp_server(3001, redis_conn),
        tcp_server(3002, redis_conn),
        websockets.serve(websocket_server, '0.0.0.0', 3003)
    )

asyncio.run(main())
