# core/fixtures.py
from django.contrib.auth import get_user_model
from .models import Objet, Signalement

User = get_user_model()

def run():
    # -------- Utilisateurs test --------
    if not User.objects.filter(username='superadmin').exists():
        User.objects.create_superuser(
            username='superadmin',
            email='superadmin@test.com',
            password='admin123',
            role='superadmin'
        )

    if not User.objects.filter(username='admin1').exists():
        User.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='admin123',
            role='admin',
            # zone='Zone A'  # Commenté car le modèle utilise maintenant region/prefecture
        )

    if not User.objects.filter(username='admin2').exists():
        User.objects.create_user(
            username='admin2',
            email='admin2@test.com',
            password='admin123',
            role='admin',
            zone='Zone B'
        )

    if not User.objects.filter(username='user1').exists():
        User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='user123',
            role='citoyen',
            zone='Zone A'
        )

    if not User.objects.filter(username='user2').exists():
        User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='user123',
            role='citoyen',
            zone='Zone B'
        )

    # -------- Objets test --------
    obj1, _ = Objet.objects.get_or_create(
        nom="Carte d'identité",
        defaults={'description': "Carte d'identité perdue"}
    )

    obj2, _ = Objet.objects.get_or_create(
        nom="Téléphone",
        defaults={'description': "iPhone perdu"}
    )

    obj3, _ = Objet.objects.get_or_create(
        nom="Sac",
        defaults={'description': "Sac à dos noir"}
    )

    # -------- Signalements test --------
    Signalement.objects.get_or_create(
        objet=obj1,
        signalement_type='Perdu',
        zone='Zone A',
        statut='En attente'
    )

    Signalement.objects.get_or_create(
        objet=obj2,
        signalement_type='Perdu',
        zone='Zone B',
        statut='Retrouvé'
    )

    Signalement.objects.get_or_create(
        objet=obj3,
        signalement_type='Retrouvé',
        zone='Zone A',
        statut='En attente'
    )

    print("✅ Utilisateurs, objets et signalements test créés avec succès !")
