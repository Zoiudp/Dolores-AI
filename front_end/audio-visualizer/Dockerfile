# Usa a imagem oficial do Ubuntu como base
FROM ubuntu:latest

# Atualiza pacotes e instala dependências básicas
RUN apt-get update && apt-get install -y \
    curl \
    openssl

# Instala o Node.js 20 e o npm
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g npm@latest

# Define o diretório de trabalho
WORKDIR /front_end/audio-visualizer

# Copia os arquivos package.json e package-lock.json
COPY package*.json ./

# Instala as dependências do projeto
RUN npm install

# Copia o código para dentro do container
COPY . .

# Gera certificados SSL autoassinados
RUN mkdir certs && \
  openssl req -nodes -new -x509 -keyout certs/server.key -out certs/server.cert -subj "/CN=localhost"

# Constrói a aplicação
RUN npm run build

# Instala 'serve' para rodar os arquivos estáticos
RUN npm install -g serve

# Expõe a porta 3000 para acesso externo
EXPOSE 3000

# Inicia o servidor HTTPS
CMD ["serve", "-s", "build", "-l", "3000", "--ssl-cert", "certs/server.cert", "--ssl-key", "certs/server.key"]
