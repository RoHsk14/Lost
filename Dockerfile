# Utiliser une image Python officielle légère
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Définir les variables d'environnement
# PYTHONDONTWRITEBYTECODE 1 : Empêche Python d'écrire des fichiers .pyc
# PYTHONUNBUFFERED 1 : Assure que les logs sont envoyés directement à la sortie standard
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Installer les dépendances système nécessaires
# libpq-dev : pour psycopg2 (PostgreSQL)
# gcc : pour compiler certaines dépendances Python
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copier le fichier requirements.txt
COPY requirements.txt /app/

# Installer les dépendances Python
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copier le reste du code du projet
COPY . /app/

# Collecter les fichiers statiques (optionnel, peut être fait au runtime ou dans une étape de build séparée)
# RUN python manage.py collectstatic --noinput

# Exposer le port sur lequel l'application va tourner
EXPOSE 8000

# Commande par défaut pour lancer l'application (peut être surchargée par docker-compose)
CMD ["gunicorn", "lostfound.wsgi:application", "--bind", "0.0.0.0:8000"]
