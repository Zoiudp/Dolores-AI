import os
from pydoc import text
import re
import asyncio
from edge_tts import Communicate

# RATE = 16000
# CHANNELS = 1
# CHUNK = 1024
# DURATION = 5


# def record_ambient_sound(rate=RATE, channels=CHANNELS, chunk=CHUNK, duration=DURATION):
#     # Initialize PyAudio and open stream
#     p = pyaudio.PyAudio()
#     stream = p.open(format=pyaudio.paInt16, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)

#     ambient_frames = []
#     for _ in range(0, int(rate / chunk * duration)):
#         data = stream.read(chunk)
#         audio_data = np.frombuffer(data, dtype=np.int16)
#         ambient_frames.append(audio_data)

#     stream.stop_stream()
#     stream.close()
#     p.terminate()

#     # Calculate the mean amplitude of ambient sound
#     ambient_audio = np.hstack(ambient_frames)
#     ambient_mean = np.abs(ambient_audio).mean()

#     return ambient_audio, ambient_mean

# Example usage
#ambient_audio, ambient_mean = record_ambient_sound()

# Função para gerar e reproduzir o áudio
def text_to_speech(text):

    if not os.path.exists("model_output"):
        os.makedirs("model_output")

    async def synthesize():
        communicate = Communicate(text, voice="pt-BR-ThalitaMultilingualNeural")
        await communicate.save("model_output/output.mp3")

    asyncio.run(synthesize())
    print("Áudio gerado com sucesso!")
    return


# Gera e toca o áudio
#text_to_speech('Olá, tudo bem?')

# Função para remover caracteres especiais
def remove_special_characters(text):
    # Remove caracteres especiais como '*', etc.
    return re.sub(r'[^\w\s.,!?]', '', text)  # Mantém apenas letras, números, espaços e alguns sinais de pontuação


# #Exemplo de uso
# text = """
# A programação é uma habilidade essencial no mundo moderno.
# Python é uma linguagem versátil e poderosa.
# Aprender a programar abre muitas portas profissionais.
# A inteligência artificial está transformando o mundo.
# O desenvolvimento de software requer prática constante.
# Algoritmos são fundamentais para resolver problemas.
# Estruturas de dados são blocos de construção importantes.
# O pensamento lógico é crucial na programação.
# Boas práticas de código fazem diferença.
# A documentação é vital para projetos de software.
# Testes automatizados garantem qualidade do código.
# Git é essencial para controle de versão.
# APIs permitem integração entre sistemas.
# Segurança é prioridade no desenvolvimento.
# Performance do código deve ser considerada.
# Frameworks aceleram o desenvolvimento.
# Clean code facilita a manutenção.
# Debugging é uma habilidade importante.
# Bibliotecas expandem as possibilidades.
# O aprendizado em programação é contínuo.
# """
# clean_text = remove_special_characters(text)
# text_to_speech(clean_text)