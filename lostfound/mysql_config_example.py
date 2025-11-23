# Configuration MySQL avec utilisateur dédié (plus sécurisé pour la production)
# Remplacez la section DATABASES dans settings.py par cette configuration si vous créez un utilisateur dédié

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'lostfound_db',
        'USER': 'lostfound_user',  # Utilisateur dédié
        'PASSWORD': 'votre_mot_de_passe_securise',  # Changez ce mot de passe !
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'sql_mode': 'traditional',
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Variables d'environnement recommandées pour la production:
# import os
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': os.getenv('DB_NAME', 'lostfound_db'),
#         'USER': os.getenv('DB_USER', 'lostfound_user'),
#         'PASSWORD': os.getenv('DB_PASSWORD', ''),
#         'HOST': os.getenv('DB_HOST', 'localhost'),
#         'PORT': os.getenv('DB_PORT', '3306'),
#         'OPTIONS': {
#             'sql_mode': 'traditional',
#             'charset': 'utf8mb4',
#             'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
#         },
#     }
# }
