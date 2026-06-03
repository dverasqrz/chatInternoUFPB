import json
import httpx
import sys

payload = json.loads(sys.stdin.read())

server_url = payload.get("server_url")
apikey = payload.get("apikey")
instance = payload.get("instance")
root = payload.get("data") or payload.get("body") or payload
key = root.get("key", {})
# In _first_text_value logic:
message_id = root.get("id") or root.get("messageId") or key.get("id")

print(f"server_url: {server_url}")
print(f"apikey: {apikey}")
print(f"instance: {instance}")
print(f"message_id: {message_id}")

download_url = f"{str(server_url).rstrip('/')}/chat/getBase64FromMediaMessage/{instance}"
print(f"download_url: {download_url}")

with httpx.Client(timeout=30.0) as client:
    resp = client.post(
        download_url,
        json={"message": {"key": {"id": message_id}}},
        headers={"apikey": str(apikey)}
    )
    print(f"status_code: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print("BASE64 len: ", len(data.get("base64") or ""))
    else:
        print(resp.text)
