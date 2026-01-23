FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir pyTelegramBotAPI schedule

# Copy source code
COPY src/ .

# Jalankan inisialisasi database lalu bot
CMD ["python3", "bot.py"]