import json
import os
import httpx

payload = {
    "event": "messages.upsert",
    "instance": "UFPB-STI-CAU_PROD",
    "data": {
        "key": {
            "remoteJid": "558994622272@s.whatsapp.net",
            "remoteJidAlt": "558994622272@s.whatsapp.net",
            "fromMe": False,
            "id": "3A9F875FA25E080DAD4F",
            "participant": "",
            "addressingMode": "lid"
        },
        "pushName": "Matheus Vieira",
        "status": "DELIVERY_ACK",
        "message": {
            "documentMessage": {
                "url": "https://mmg.whatsapp.net/v/t62.7119-24/616452435_1264230115290655_4034970709370018404_n.enc?ccb=11-4&oh=01_Q5Aa4QFM9EvrCAs31u8Pvy4OjFyO8ebH_3tLL-SOv22VVwGWDg&oe=69FDBC58&_nc_sid=5e03e0&mms3=true",
                "mimetype": "application/pdf",
                "title": "Edital.pdf"
            }
        }
    },
    "destination": "https://workflow.sti.ufpb.br/webhook/entrada_chat_UFPB",
    "date_time": "2026-04-08T09:25:36.196Z",
    "sender": "558332167336@s.whatsapp.net",
    "server_url": "https://evolution.example.com",
    "apikey": os.getenv("EVOLUTION_API_KEY", "CHANGE_ME_EVOLUTION_API_KEY")
}

resp = httpx.post('http://127.0.0.1:8000/api/inbox', json=payload)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text}")
