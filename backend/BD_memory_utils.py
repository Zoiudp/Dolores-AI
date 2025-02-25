import sqlite3
from datetime import datetime

# Configura o banco de dados para armazenar o histórico da conversa
def init_db():
    conn = sqlite3.connect("chat_memory.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS conversation_history
                 (id INTEGER PRIMARY KEY, timestamp TEXT, user_message TEXT, bot_response TEXT)''')
    conn.commit()
    conn.close()
# Inicializa o banco de dados
#init_db()

# Função para armazenar uma mensagem no banco de dados
def store_message(user_message, bot_response):
    conn = sqlite3.connect("chat_memory.db")
    c = conn.cursor()
    c.execute("INSERT INTO conversation_history (timestamp, user_message, bot_response) VALUES (?, ?, ?)",
              (datetime.now(), user_message, bot_response))
    conn.commit()
    conn.close()

# Função para recuperar o histórico da conversa
def retrieve_history(limit=5):
    conn = sqlite3.connect("chat_memory.db")
    c = conn.cursor()
    c.execute("SELECT user_message, bot_response FROM conversation_history ORDER BY timestamp DESC LIMIT ?", (limit,))
    history = c.fetchall()
    conn.close()
    return history

def is_initialized():
    conn = sqlite3.connect("chat_memory.db")
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_history'")
    result = c.fetchone()
    conn.close()
    return result is not None