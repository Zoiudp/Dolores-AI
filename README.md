# Dolores-AI

Trabalho de Conclusão de Curso que implementa uma assistente virtual baseada em IA.

## Pré-requisitos
- Docker
- Docker Compose

## Instalação e Configuração

1. Clone o repositório:
    ```bash
    git clone https://github.com/seu-usuario/Dolores-AI.git
    ```

    1.1 Caminhe até o diretório do projeto:
    ```bash
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


# Configuração do Chromium para Iniciar Automaticamente na TvBOX

Este guia explica como configurar uma máquina Linux para abrir automaticamente o navegador Chromium via Snap em um endereço específico ao iniciar o sistema.

## 1. Instalar o Chromium via Snap

### **1.1 Verificar se o Snap está instalado**
O Snap geralmente vem pré-instalado em distribuições como Ubuntu, mas em outras pode ser necessário instalá-lo.

Para verificar se o Snap está instalado, execute:
```bash
snap --version
```
Se o comando retornar uma versão, o Snap está instalado. Caso contrário, instale-o com:

- **Ubuntu/Debian**:
  ```bash
  sudo apt update && sudo apt install snapd -y
  ```
  
- **Fedora**:
  ```bash
  sudo dnf install snapd -y
  sudo ln -s /var/lib/snapd/snap /snap  # Criar link simbólico para compatibilidade
  ```

- **Arch Linux**:
  ```bash
  sudo pacman -S snapd
  sudo systemctl enable --now snapd
  ```

Após a instalação, reinicie o Snap para garantir que está ativo:
```bash
sudo systemctl restart snapd
```

### **1.2 Instalar o Chromium via Snap**
Com o Snap instalado, instale o Chromium com:
```bash
sudo snap install chromium
```
Esse comando baixa e instala a versão mais recente do navegador.

### **1.3 Verificar a Instalação**
Para confirmar que o Chromium foi instalado corretamente, execute:
```bash
snap list chromium
```
Se o Chromium aparecer na lista, ele foi instalado com sucesso.

### **1.4 Executar o Chromium**
Para abrir o Chromium via Snap, use:
```bash
snap run chromium
```
Ou simplesmente:
```bash
chromium
```
Se quiser executar em **modo kiosk** (tela cheia e sem barra de ferramentas), use:
```bash
snap run chromium --kiosk
```

## 2. Descobrir o Usuário Atual
Antes de configurar a inicialização do Chromium, é necessário saber o nome do usuário logado. Para isso, abra um terminal e execute:

```bash
whoami
```

Anote o nome do usuário retornado, pois ele será utilizado nas etapas seguintes.

## 3. Criar o Script de Inicialização
Crie um script que abrirá o Chromium na URL desejada ao iniciar o sistema.

```bash
nano ~/start_chromium.sh
```

Adicione o seguinte conteúdo ao arquivo:

```bash
#!/bin/bash
# Obtém o IPv4 da interface Wi-Fi
IP=$(ip -4 addr show wlan0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
# Abre o Chromium com Snap em modo kiosk
snap run chromium --start-fullscreen --kiosk "https://$IP:3000"
```

Caso a interface Wi-Fi não seja `wlan0`, substitua pelo nome correto. Para verificar o nome da interface, use:

```bash
ip a
```

Salve o arquivo (`CTRL + X`, `Y`, `ENTER`) e dê permissão de execução:

```bash
chmod +x ~/start_chromium.sh
```

## 4. Criar um Serviço Systemd
Para garantir que o Chromium inicie automaticamente sem precisar de login, crie um serviço do `systemd`.

```bash
sudo nano /etc/systemd/system/chromium-start.service
```

Adicione o seguinte conteúdo, substituindo `seu_usuario` pelo nome do usuário obtido na etapa 2:

```ini
[Unit]
Description=Iniciar Chromium na URL desejada via Snap
After=network.target

[Service]
User=seu_usuario
ExecStart=/home/seu_usuario/start_chromium.sh
Restart=always
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/1000

[Install]
WantedBy=graphical.target
```

Salve (`CTRL + X`, `Y`, `ENTER`) e recarregue o `systemd`:

```bash
sudo systemctl daemon-reload
sudo systemctl enable chromium-start.service
sudo systemctl start chromium-start.service
```

## 5. Testar
Reinicie o sistema para testar a configuração:

```bash
sudo reboot
```

O Chromium deve abrir automaticamente na página `https://[ipv4]:3000` ao iniciar o sistema.

Caso não funcione, verifique o status do serviço:

```bash
systemctl status chromium-start.service
```

Agora, o navegador será aberto automaticamente na inicialização! 🚀

