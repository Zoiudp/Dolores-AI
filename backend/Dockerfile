# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install build tools and dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libasound2-dev \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /backend/

# Copy the current directory contents into the container at /app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN pip3 install torch==2.5.1+cu118 torchvision==0.20.1+cu118 torchaudio --index-url https://download.pytorch.org/whl/cu118
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip install -U openai-whisper
RUN apt-get update && apt-get install -y git
RUN pip install --no-cache-dir --upgrade torch torchvision torchaudio

# Gera certificados SSL autoassinados
RUN openssl genrsa -out localhost-key.pem 2048 && \
    openssl req -new -x509 -key localhost-key.pem -out localhost.pem -days 365 -subj "/CN=localhost"

# Make port 5001 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV FLASK_APP=app.py

# Run app.py when the container launches
CMD ["python", "-u", "app.py"]