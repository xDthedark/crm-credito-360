FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8501

WORKDIR /app

# dependências do sistema (se necessário) e instalação de requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE ${PORT}

# usar forma shell para permitir expansão de variáveis de ambiente em runtime
CMD streamlit run app.py --server.port $PORT --server.headless true
