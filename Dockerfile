# Usamos una versión ligera y rápida de Python
FROM python:3.10-slim

# Le ordenamos a la máquina virtual que instale el FFmpeg de Linux
RUN apt-get update && apt-get install -y ffmpeg

# Preparamos tu mesa de trabajo
WORKDIR /app

# Copiamos tus librerías y las instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos tu código maestro
COPY . .

# Encendemos el cerebro de la IA
CMD ["python", "main.py"]