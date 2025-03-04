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
    ```

2. Inicie os containers com Docker Compose:
    ```bash
    docker compose up -d
    ```

3. Configure o modelo Whisper:
    
   3.1 Acesse o container do backend:
    ```bash
    docker exec -it dolores-backend bash
    ```
    3.2 Execute o script de inicialização:
    ```bash
    python init.py
    ```
## Usando a Aplicação
4. Após a configuração, acesse a interface web através do navegador:
    ```bash
    https://192.168.X.X:3000

## Observações
Substitua 192.168.X.X pelo IP da sua máquina na rede local
Certifique-se de que as portas necessárias estejam liberadas no firewall
## Arquitetura
Frontend: Porta 3000
Backend: Serviço em Python com modelo Whisper para trasncrição de áudio na porta 5000, serviço ollama na porta 11434 para controle dos modelos e inferência em imagem e texto.
