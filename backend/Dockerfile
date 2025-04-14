# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libasound2-dev \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    ffmpeg \
    git \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /backend/

# Copy contents and install Python dependencies
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip3 install torch==2.5.1+cu118 torchvision==0.20.1+cu118 torchaudio --index-url https://download.pytorch.org/whl/cu118
RUN pip install -U openai-whisper
RUN pip install --no-cache-dir --upgrade torch torchvision torchaudio

# Gera certificados SSL autoassinados
RUN openssl genrsa -out localhost-key.pem 2048 && \
    openssl req -new -x509 -key localhost-key.pem -out localhost.pem -days 365 -subj "/CN=localhost"

# Expose the port
EXPOSE 5000

# Define environment variable
ENV FLASK_APP=app.py

# Copia e dá permissão de execução ao start.sh
COPY start.sh /backend/start.sh
RUN chmod +x /backend/start.sh

# Run init.py once and then start the app
CMD ["/backend/start.sh"]
