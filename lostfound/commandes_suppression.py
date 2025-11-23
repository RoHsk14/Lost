# COMMANDES RAPIDES POUR SUPPRIMER LES UTILISATEURS
# Exécutez ces commandes dans le shell Django: python manage.py shell

# 1. Supprimer TOUS les utilisateurs (y compris superusers) ⚠️ DANGEREUX
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.all().delete()

# 2. Supprimer uniquement les utilisateurs normaux (garde les superusers)
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.filter(is_superuser=False).delete()

# 3. Supprimer par rôle
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.filter(role='citoyen').delete()  # Supprime les citoyens
User.objects.filter(role='admin').delete()    # Supprime les admins
User.objects.filter(role='agent').delete()    # Supprime les agents

# 4. Compter les utilisateurs avant suppression
from django.contrib.auth import get_user_model
User = get_user_model()
print(f"Total: {User.objects.count()}")
print(f"Citoyens: {User.objects.filter(role='citoyen').count()}")
print(f"Admins: {User.objects.filter(role='admin').count()}")
print(f"Agents: {User.objects.filter(role='agent').count()}")
print(f"Superusers: {User.objects.filter(is_superuser=True).count()}")

# 5. Suppression avec confirmation dans le shell
from django.contrib.auth import get_user_model
User = get_user_model()
count = User.objects.filter(is_superuser=False).count()
print(f"Suppression de {count} utilisateurs...")
User.objects.filter(is_superuser=False).delete()
print("✅ Suppression terminée")

# 6. Reset complet de toutes les données
from django.contrib.auth import get_user_model
from core.models import Signalement, Objet, ObjetPerdu
User = get_user_model()

User.objects.all().delete()
Signalement.objects.all().delete()
Objet.objects.all().delete()
ObjetPerdu.objects.all().delete()
print("✅ Base de données complètement vidée")
