FROM python:3.12-alpine

# Set working directory
WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir pyTelegramBotAPI schedule python-dateutil

# Copy source code
COPY src/ .

# Jalankan bot
CMD ["python3", "bot.py"]