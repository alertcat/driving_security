import asyncio
import json
import websockets

async def test_websocket(websocket, path):
    while True:
        await websocket.send(json.dumps({"test": "Hello from server"}))
        print("Sent test message")
        await asyncio.sleep(1)  # Send every second

async def main():
    print("Starting test WebSocket server...")
    async with websockets.serve(test_websocket, "localhost", 5000):
        print("Server running on ws://localhost:5000")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())