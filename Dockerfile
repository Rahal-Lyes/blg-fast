FROM python:3.11-slim

# dossier de travail
WORKDIR /app

# dépendances système nécessaires (psycopg2, pillow, cryptography)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# copier requirements en premier (cache Docker optimisé)
COPY requirements.txt .

# installer dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# copier tout le projet
COPY . .

# exposer port Render
EXPOSE 10000

# lancer FastAPI (IMPORTANT: main.py est à la racine)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
