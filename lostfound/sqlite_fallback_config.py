# Configuration temporaire - Garder SQLite en attendant MySQL
# Remplacez la section DATABASES dans settings.py par ceci:

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Une fois MySQL installé, utilisez cette configuration:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'lostfound_db',
#         'USER': 'root',
#         'PASSWORD': 'votre_mot_de_passe',
#         'HOST': 'localhost',
#         'PORT': '3306',
#         'OPTIONS': {
#             'sql_mode': 'traditional',
#             'charset': 'utf8mb4',
#             'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
#         },
#     }
# }
