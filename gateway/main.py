import json
from hashlib import sha256

from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis

from tasks import send_request

app = FastAPI()
redis = Redis(host="localhost", port=6379, db=0)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def hash_request(data):
    return sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


@app.post("/gateway")
async def gateway(data=Body(embed=True)):
    request_hash = hash_request(data)

    if redis.get(request_hash):
        return {"status": "duplicate request"}

    # Кеш ???
    redis.set(name=request_hash, value=1, ex=300)

    # Отправка запроса в очередь
    send_request.apply_async(queue='message', kwargs={'data': data})
    return {"status": "request accepted"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
