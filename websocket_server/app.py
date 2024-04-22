import asyncio
import websockets
import aioredis

websocket_clients = []

# Initialize Redis connection asynchronously
async def get_redis():
    # Update Redis connection string to use the service name
    return await aioredis.from_url("redis://redis:6379", encoding="utf-8", decode_responses=True)

async def handle_tcp_client(reader, writer, redis_conn):
    port = writer.get_extra_info('peername')[1]
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                print(f"No data received. Closing TCP connection on port {port}.")
                break
            message = data.decode()
            print(f"Received message on TCP port {port}: {message}")

            user_id, _, message_content = message.partition(':')
            MV = await redis_conn.get(f"{user_id}_MV")
            MV = int(MV) if MV else 1
            current_value = int(message_content)
            next_value = current_value + MV

            message_to_send = f"{user_id}:{next_value}"
            print(f"Attempting to forward to WebSocket clients: {message_to_send}")

            if websocket_clients:
                print(f"Forwarding to {len(websocket_clients)} connected WebSocket clients.")
                for ws in websocket_clients:
                    await ws.send(message_to_send)
            else:
                print("Warning: No WebSocket clients connected to receive the message.")
    except Exception as e:
        print(f"Error with TCP client on port {port}: {e}")
    finally:
        writer.close()
        print(f"Closed TCP connection on port {port}")

async def tcp_server(port, redis_conn):
    server = await asyncio.start_server(
        lambda r, w: handle_tcp_client(r, w, redis_conn), '0.0.0.0', port)
    print(f"TCP server listening on 0.0.0.0:{port}")
    async with server:
        await server.serve_forever()

async def websocket_server(websocket, path):
    print(f"WebSocket client connected: {websocket.remote_address}")
    websocket_clients.append(websocket)
    try:
        await websocket.wait_closed()
    finally:
        websocket_clients.remove(websocket)
        print(f"WebSocket client disconnected: {websocket.remote_address}")

async def main():
    redis_conn = await get_redis()
    print("Starting TCP and WebSocket servers")
    await asyncio.gather(
        websockets.serve(websocket_server, '0.0.0.0', 3003),
        tcp_server(3000, redis_conn),
        tcp_server(3001, redis_conn),
        tcp_server(3002, redis_conn)
    )

asyncio.run(main())