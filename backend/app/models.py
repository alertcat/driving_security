from openai import OpenAI
from flask import current_app

def set_client(new_client):
    global client
    client = new_client

def adjust_aircon(user_prompt):
    if client is None:
        raise ValueError("Client not initialized!")
    system_prompt = current_app.config['SYSTEM_PROMPT']
    response = client.chat.completions.create(
        model="deepseek-r1:14b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={'type': 'json_object'},
    )
    return response.choices[0].message.content