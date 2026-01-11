import json
import os

file_path = r"C:\Users\dgar\.gemini\tmp\f535d4977bb3d317ff6e0465b07d4e4e0337013c6b6caacfef3e260f6e2d3b28\chats\session-2026-01-11T11-13-c6299816.json"

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
    all_messages = data.get("messages", [])
    
    limit = None
    offset = 0
    total = len(all_messages)
    if limit is not None:
        start = max(0, total - offset - limit)
        end = max(0, total - offset)
        messages_to_process = all_messages[start:end]
    else:
        messages_to_process = all_messages
    
    messages = []
    for msg in messages_to_process:
        content = msg.get("content", "")
        print(f"DEBUG: msg content: '{content}' type: {msg.get('type')}")
        if not content or content.strip() == "":
            continue
        messages.append({
            "role": "user" if msg.get("type") == "user" else "bot",
            "content": content
        })

print(f"Final messages list: {messages}")