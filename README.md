# bot-subscribe

## How to deploy

Install `requirements.txt`

```shell
pip install -r requirements.txt
```

Fill `.env` with real values

Run `main.py`

## Subscribe to channel

```shell
curl -X POST http://10.10.126.2:8000/subscribe \
     -H "Content-Type: application/json" \
     -d '{"channel": "https://t.me/vnedvnedr8"}'
```

Change `10.10.126.2` with your own IP and `https://t.me/vnedvnedr8` with channel *url* you want subscribe to

## Send to `handle-name` service

It will wend all comming news to `localhost:8080/add/news`
