
import whisper
from BD_memory_utils import init_db, is_initialized


def init():
    if not is_initialized():
        init_db()
    

    model_size = 'turbo'
    model = whisper.load_model(model_size, download_root='~/.cache/whisper')
    
    return print('Iniciado com sucesso')

init()

