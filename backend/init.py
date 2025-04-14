
import whisper
from BD_memory_utils import init_db, is_initialized
import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification


def init():
    # if not is_initialized():
    #     init_db()

    model_size = 'medium'
    model = whisper.load_model(model_size, download_root='~/.cache/whisper')
    return print('Iniciado com sucesso')

init()

