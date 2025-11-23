#!/usr/bin/env python3
"""
Script pour créer des utilisateurs de test avec les nouvelles données
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lostfound.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from core.models import Region, Prefecture

User = get_user_model()

def create_test_data():
    print("🚀 Création des données de test pour Lost & Found...")
    
    # Créer les régions
    region_maritime, _ = Region.objects.get_or_create(nom='Région Maritime')
    region_plateaux, _ = Region.objects.get_or_create(nom='Région des Plateaux')
    
    # Créer les préfectures
    prefecture_lome, _ = Prefecture.objects.get_or_create(
        nom='Lomé',
        region=region_maritime
    )
    prefecture_kpalime, _ = Prefecture.objects.get_or_create(
        nom='Kpalimé',
        region=region_plateaux
    )
    
    print("✅ Régions et préfectures créées")
    
    # Créer des utilisateurs de test
    if not User.objects.filter(username='admin').exists():
        admin = User.objects.create_user(
            username='admin',
            email='admin@lostfound.com',
            password='admin123',
            role='admin',
            region=region_maritime,
            prefecture=prefecture_lome
        )
        print(f"✅ Admin créé: {admin.username}")
    
    if not User.objects.filter(username='citoyen1').exists():
        citoyen = User.objects.create_user(
            username='citoyen1',
            email='citoyen1@test.com',
            password='citoyen123',
            role='citoyen',
            region=region_maritime,
            prefecture=prefecture_lome
        )
        print(f"✅ Citoyen créé: {citoyen.username}")
    
    if not User.objects.filter(username='agent').exists():
        agent = User.objects.create_user(
            username='agent',
            email='agent@lostfound.com',
            password='agent123',
            role='agent',
            region=region_plateaux,
            prefecture=prefecture_kpalime
        )
        print(f"✅ Agent créé: {agent.username}")
    
    print("\n🎉 Données de test créées avec succès !")
    print("\n📋 Comptes disponibles :")
    print("   Admin: admin / admin123")
    print("   Citoyen: citoyen1 / citoyen123")
    print("   Agent: agent / agent123")
    print("\n🌐 Accédez à: http://localhost:8000")

if __name__ == "__main__":
    create_test_data()
