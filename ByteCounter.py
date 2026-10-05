import json

message = {
    "message_type": "CONNECT",
    "user_alias": "Sweet Robin"
}

payload = json.dumps(message).encode("utf-8")
payload_length = len(payload)

print(payload_length)