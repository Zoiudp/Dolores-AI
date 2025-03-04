# Dolores-AI

Trabalho de Conclusão de Curso que implementa uma assistente virtual baseada em IA.

## Pré-requisitos
- Docker
- Docker Compose

## Instalação e Configuração

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/Dolores-AI.git
   cd Dolores-AI

## Inicie os containers com Docker Compose:

docker compose up -d

## Configure o modelo Whisper:

Acesse o container do backend:
docker exec -it dolores-backend bash

Execute o script de inicialização:
python init.py

## Usando a Aplicação
Após a configuração, acesse a interface web através do navegador:
    https://192.168.X.X:3000

## Observações
Substitua 192.168.X.X pelo IP da sua máquina na rede local
Certifique-se de que as portas necessárias estejam liberadas no firewall
## Arquitetura
Frontend: Porta 3000
Backend: Serviço em Python com modelo Whisper para trasncrição de áudio na porta 5000, serviço ollama na porta 11434 para controle dos modelos e inferência em imagem e texto.
