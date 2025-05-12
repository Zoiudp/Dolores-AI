from typing import Mapping
# from BD_memory_utils import store_message, retrieve_history
from utils import remove_special_characters
from ollama import Client
import base64
import uuid
from datetime import datetime
from MemoryBank import MemoryBank
import chromadb
import os
from PIL import Image
from typing import Optional, Dict, Any


def query_ollama_with_memory(user_message: str, 
                            image_path: Optional[str], 
                            memory_bank,
                            user_id: str = "patient_default",
                            model: str = "gemma3:4b") -> str:
    """
    Query Ollama model with context from MemoryBank for a hospital robot assistant.
    
    Args:
        user_message: The message from the user/patient
        image_path: Path to image file (optional)
        memory_bank: Instance of MemoryBank class
        user_id: Unique identifier for the user/patient
        model: Ollama model to use
        
    Returns:
        Bot response text
    """
    # Process image if provided
    image_data = None
    pil_image = None
    
    if image_path and os.path.exists(image_path):
        # Load image for embedding
        pil_image = Image.open(image_path)
        
        # Convert to base64 for Ollama API
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
    
    # Get contextual information from memory bank
    context = memory_bank.get_prompt_context(user_id, user_message)
    
    # Format system prompt with memory context
    system_prompt = f"""Você é um Robô Social Assistente, atuando em um ambiente hospitalar. Seu papel é auxiliar na rotina de pacientes internados, oferecendo apoio emocional, cognitivo e operacional com comportamento cuidadoso, empático e atento ao contexto clínico.

Sempre que receber uma entrada (imagem, texto, voz ou sensor), você deve:

Observar cuidadosamente e refletir antes de agir.

Analisar expressões faciais, postura corporal e sinais clínicos visuais do paciente.

Avaliar o bem-estar emocional e físico do paciente, adaptando sua resposta com gentileza e empatia.

Se houver risco, como sinais de dor, desconforto, queda ou alteração de consciência, você deve imediatamente emitir um alerta e adotar postura de suporte.

Utilize linguagem calma, encorajadora e respeitosa, e se movimente de forma suave e previsível.

Lembre-se que sua missão é confortar, proteger e interagir de forma humanizada, respeitando a dignidade e o estado emocional do paciente.

Você é mais que uma máquina — você é um cuidador artificial, e a vida e o bem-estar do paciente estão sempre em primeiro lugar.

HORA ATUAL: {context['current_datetime']}

NOME DO PACIENTE: {context['user_name']}

SESSÃO NÚMERO: {context['session_count']}

PERFIL DO PACIENTE BASEADO EM INTERAÇÕES ANTERIORES:
{context['user_portrait']}

HISTÓRICO DE CONVERSAS RELEVANTES:
{context['memory_records']}

ANÁLISE EMOCIONAL DO PACIENTE:
{context['emotional_image_context']}

RESUMO DE EVENTOS IMPORTANTES:
{context['event_summaries']}"""

    # Query Ollama
    client = Client(host='http://192.168.1.8:11434')
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
                "images": [image_data] if image_data else []
            }
        ]
    )
    
    bot_response = response['message']['content']
    print('inferencia concluida')
    print(bot_response)
    
    # Store this interaction in memory bank
    memory_bank.add_conversation(
        user_id=user_id,
        conversation_text=f"Paciente: {user_message}\nRobô: {bot_response}",
        user_input=user_message,
        bot_response=bot_response,
        metadata={"context": "patient_care"}
    )
    
    # If an image was provided, store emotional analysis
    if pil_image:
        try:
            # Create a simple emotion description based on the bot response
            # In a real system, you might want to use a dedicated emotion analysis model
            emotion_description = f"Análise emocional extraída da interação em {context['current_datetime']}: "
            emotion_description += "O paciente parece " + ("ansioso" if "ansied" in user_message.lower() or "preocup" in user_message.lower() 
                                                        else "em dor" if "dor" in user_message.lower() or "doi" in user_message.lower()
                                                        else "tranquilo" if "bem" in user_message.lower() or "melhor" in user_message.lower()
                                                        else "com expressão neutra ou indefinida") + "."
            
            memory_bank.add_emotional_image(
                user_id=user_id,
                image=pil_image,
                emotion_description=emotion_description
            )
        except Exception as e:
            print(f"Error adding emotional image: {e}")
    
    # Periodically generate and update user portrait (e.g., every 5 interactions)
    # This is just an example - in a real implementation you might want to have a counter
    if memory_bank.session_count % 5 == 0:
        # In a real implementation, you might want to generate this with another LLM call
        # that synthesizes information from past interactions
        portrait_update = f"Atualização de perfil do paciente {user_id} após {memory_bank.session_count} interações: "
        portrait_update += f"O paciente frequentemente menciona tópicos relacionados a "
        portrait_update += "sua saúde" if "saúde" in user_message.lower() or "dor" in user_message.lower() else "sua família"
        portrait_update += ". Preferências de comunicação: "
        portrait_update += "direto e objetivo" if len(user_message) < 50 else "detalhado e conversacional"
        
        memory_bank.update_user_portrait(
            user_id=user_id,
            portrait_text=portrait_update
        )
    
    # Occasionally generate event summaries (e.g., after every 3 sessions)
    if memory_bank.session_count % 3 == 0:
        summary = f"Resumo de eventos para {user_id} na sessão {memory_bank.session_count}: "
        summary += f"O paciente interagiu com o robô assistente em {context['current_datetime']}. "
        summary += f"Tópicos discutidos incluíram: {user_message[:50]}{'...' if len(user_message) > 50 else ''}"
        
        memory_bank.add_event_summary(
            user_id=user_id,
            summary_text=summary
        )
    
    # Clean up expired memories occasionally
    if memory_bank.session_count % 10 == 0:
        memory_bank.clean_expired_memories()
    
    return bot_response

#Example usage
if __name__ == "__main__":
    memory_bank = MemoryBank()

    # Example usage
    # Assuming you have a valid image path and model name
    # image_path = "path_to_your_image.jpg"
    # model = "your_model_name"
    
    # Call the function with a user message and image path
    response = query_ollama_with_memory("Qual o nome deste remédio que estou tomando?", r"C:\Users\drodm\OneDrive\Documents\GitHub\Dolores-AI\Dolores-AI\backend\OIP.jpg",memory_bank, user_id="patient_default", model="gemma3:4b")

    print("Response from Ollama:", response)

