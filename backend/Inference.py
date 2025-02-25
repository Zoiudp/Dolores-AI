from typing import Mapping
# from BD_memory_utils import store_message, retrieve_history
from utils import remove_special_characters
from ollama import Client
import base64

def query_ollama_with_memory(user_message, image_path, model="llava:7B"):
    
    # history = retrieve_history()
    # context = "\n".join([f"Usuário: {msg[0]}\nBot: {msg[1]}" for msg in history])

    # history_messages = []
    # for i, msg in enumerate(history):
    #     history_messages.append({
    #         'role': 'user' if i % 2 == 0 else 'assistant',
    #         'content': msg[0] if i % 2 == 0 else msg[1]
    #     })
    
    system_prompt = f"""Você é um robô de compania em um hospital.
    Histórico da conversa:"""
    #{context}"""
    
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    client = Client(host='http://ollama-server:11434')
    response = client.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_message,
                "images": [image_data]
            }
        ]
    )
    #store_message(user_message, bot_response)
    print('inferencia concluida')
    print(response['message']['content'])
    
    return response['message']['content']

#Example usage
response = query_ollama_with_memory("Olá, tudo bem?", r"uploads\image_file.png")

