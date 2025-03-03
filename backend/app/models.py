from openai import OpenAI
from flask import current_app

def set_client(new_client):
    global client
    client = new_client

def set_session(rag_object):
    global session
    assistants = rag_object.list_chats(name="Tesla")
    assistant = assistants[0]
    session = assistant.create_session()
    # print("\n===== Miss R ====\n")
    # print("Hello. What can I do for you?")

    # while True:
    #     question = input("\n===== User ====\n> ")
    #     print("\n==== Miss R ====\n")
        
    #     cont = ""
    #     for ans in session.ask(question, stream=True):
    #         print(ans.content[len(cont):], end='', flush=True)
    #         cont = ans.content

def intent_detect(user_prompt):
    if client is None:
        raise ValueError("Client not initialized!")
    system_prompt = current_app.config['INTENT_DETECT_PROMPT']
    response = client.chat.completions.create(
        model=current_app.config['MODEL_NAME'],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={'type': 'json_object'},
    )
    return response.choices[0].message.content
    # messages = [
    #     ("system", system_prompt),
    #     ("user", user_prompt)
    # ]
    # response = client.invoke(messages)
    # return response

def json_summarize(json_response):
    if client is None:
        raise ValueError("Client not initialized!")
    system_prompt = current_app.config['JSON_SUMMARIZE_PROMPT']
    response = client.chat.completions.create(
        model=current_app.config['MODEL_NAME'],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json_response}
        ],
    )
    print(response)
    content = response.choices[0].message.content
    # 找到 `<think>` 部分的结束位置
    think_end = content.find('</think>') + len('</think>')

    # 提取并输出 `<think>` 之后的内容
    result = content[think_end:].strip()
    return result
    # messages = [
    #     ("system", system_prompt),
    #     ("user", json_response)
    # ]
    # response = client.invoke(messages)
    # return response

def manual_refer(user_prompt):
    return