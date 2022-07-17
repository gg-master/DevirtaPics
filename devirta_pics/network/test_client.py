import websockets
import asyncio
import json


reg_data = {
    'status': 'registration',
    'type': 'glasses',
    'token': 123456
}


async def start_client():
    url = 'ws://127.0.0.1:1234'
    async with websockets.connect(url) as websocket:
        glasses_data = json.dumps(reg_data)
        await websocket.send(glasses_data)
        async for message in websocket:
            answer = json.loads(message)
            print(answer)
            if answer['answer'] == 'Pair has been established':
                await websocket.send(json.dumps({'status': 'I am ready to get'}))
            elif answer['answer'] == 'sharing':
                print('Yahoo')
            elif answer['answer'] == 'Client forcibly terminated the connection':
                exit()


if __name__ == '__main__':
    print('>>> Glasses start connection')
    asyncio.get_event_loop().run_until_complete(start_client())
    asyncio.get_event_loop().run_forever()
