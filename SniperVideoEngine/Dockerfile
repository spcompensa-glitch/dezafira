FROM python:3.10-slim

WORKDIR /app

# Instalar dependências do sistema e do Playwright
RUN apt-get update && apt-get install -y \
    curl \
    git \
    ffmpeg \
    libnss3 \
    libatk-bridge2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libclutter-1.0-0 \
    libxkbcommon0 \
    libxfixes3 \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar navegadores do Playwright (Chromium)
RUN playwright install chromium

# Copiar código do backend
COPY . .

# Expor a porta que o Railway definirá dinamicamente
EXPOSE 8000

# Comando para rodar com Uvicorn
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
