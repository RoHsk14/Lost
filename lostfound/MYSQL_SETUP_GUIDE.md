# Guide d'installation MySQL pour Lost & Found

## Option 1: MySQL Standalone
1. Téléchargez MySQL Community Server: https://dev.mysql.com/downloads/mysql/
2. Installez avec les paramètres par défaut
3. Notez le mot de passe root que vous définissez
4. Démarrez le service MySQL

## Option 2: XAMPP (Recommandé pour développement)
1. Téléchargez XAMPP: https://www.apachefriends.org/download.html
2. Installez XAMPP
3. Démarrez Apache et MySQL depuis le panneau XAMPP
4. Accédez à phpMyAdmin: http://localhost/phpmyadmin
5. Créez la base de données 'lostfound_db'

## Option 3: Docker MySQL (Pour développeurs avancés)
```bash
docker run --name mysql-lostfound -e MYSQL_ROOT_PASSWORD=password -e MYSQL_DATABASE=lostfound_db -p 3306:3306 -d mysql:8.0
```

## Configuration après installation:
1. Exécutez le script create_mysql_db.sql dans votre interface MySQL
2. Modifiez le mot de passe dans settings.py si nécessaire
3. Testez avec: python manage.py migrate

## Variables d'environnement (Recommandé):
Créez un fichier .env:
```
DB_NAME=lostfound_db
DB_USER=root
DB_PASSWORD=votre_mot_de_passe
DB_HOST=localhost
DB_PORT=3306
```
