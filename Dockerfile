FROM python:3.11-slim-bullseye

# Définir le répertoire de travail
WORKDIR /app

# Empêcher Python d'écrire des fichiers .pyc sur le disque
ENV PYTHONDONTWRITEBYTECODE=1
# Ne pas bufferiser stdout/stderr
ENV PYTHONUNBUFFERED=1

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root pour la sécurité
RUN addgroup --system appuser && adduser --system --group appuser

# Copier et installer les dépendances Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
# Gunicorn est nécessaire pour le déploiement sur Railway
RUN pip install --no-cache-dir gunicorn whitenoise

# Copier le reste du code de l'application
COPY . /app/

# ------------ CONFIGURATION DU VOLUME ------------------
# Créer le dossier pour le volume SQLite (/app/data) et donner les droits
USER root
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data && chmod 777 /app/data

# Revenir à l'utilisateur non-root
USER appuser
# -------------------------------------------------------

# Créer le répertoire pour les fichiers statiques
RUN mkdir -p /app/staticfiles

# Collecter les fichiers statiques (WhiteNoise s'en chargera pour la distribution)
RUN python manage.py collectstatic --noinput

# Exposer le port par défaut (Railway gérera la variable d'environement PORT)
EXPOSE 8000

# Lancer l'application avec Gunicorn
# Remarque: assurez-vous que 'lostfound' est bien le nom de votre projet/dossier contenant wsgi.py
CMD ["gunicorn", "lostfound.wsgi:application", "--bind", "0.0.0.0:$PORT"]
