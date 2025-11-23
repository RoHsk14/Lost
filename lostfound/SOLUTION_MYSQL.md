# 🔧 SOLUTION: Configuration MySQL pour Lost & Found

## ✅ ÉTAT ACTUEL
- Le projet fonctionne parfaitement avec SQLite
- MySQL est configuré mais la connexion échoue

## 🎯 SOLUTIONS POUR MYSQL

### Option 1: Vérifier MySQL avec XAMPP
Si vous utilisez XAMPP:
1. Ouvrir le panneau XAMPP
2. Cliquer sur "Start" pour MySQL
3. Vérifier que le voyant devient vert
4. Aller sur http://localhost/phpmyadmin
5. Créer la base de données:
   ```sql
   CREATE DATABASE lostfound_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

### Option 2: Vérifier MySQL Service
Si vous avez MySQL Community Server:
1. Ouvrir Services Windows (services.msc)
2. Chercher "MySQL" et démarrer le service
3. Ou utiliser: `net start mysql80`

### Option 3: Test de connexion manuel
1. Ouvrir cmd/PowerShell
2. Tester: `mysql -u root -p`
3. Si ça marche, créer la BD:
   ```sql
   CREATE DATABASE lostfound_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   SHOW DATABASES;
   EXIT;
   ```

## 🔄 MIGRATION VERS MYSQL (une fois MySQL démarré)

### Étape 1: Modifier settings.py
Décommentez la configuration MySQL et ajoutez votre mot de passe:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'lostfound_db',
        'USER': 'root',
        'PASSWORD': 'VOTRE_MOT_DE_PASSE_ICI',  # ⚠️ Important !
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'sql_mode': 'traditional',
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}
```

### Étape 2: Tester et migrer
```bash
python mysql_diagnostic.py  # Diagnostic
python manage.py check --database default  # Test connexion
python manage.py migrate  # Migration
python manage.py createsuperuser  # Créer admin
python manage.py runserver  # Démarrer
```

## ⚡ SOLUTION RAPIDE (Garder SQLite)
Si vous voulez continuer avec SQLite (recommandé pour développement):
- Le projet fonctionne parfaitement
- Aucune configuration supplémentaire nécessaire
- Changez vers MySQL plus tard pour la production

## 🆘 EN CAS DE PROBLÈME
1. Utilisez SQLite (configuration actuelle)
2. MySQL sera configuré plus tard
3. Le projet fonctionne dans tous les cas !
