#!/usr/bin/env python
"""
Script pour créer des données de test pour le dashboard admin
"""
import os
import sys
import django
import random
from datetime import datetime, timedelta
from django.utils import timezone

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lostfound.settings')
django.setup()

from core.models import Utilisateur, Declaration, Region, Prefecture

def create_dashboard_test_data():
    print("🚀 Création des données de test pour le dashboard admin...")

    # Créer des régions si elles n'existent pas
    regions_data = [
        {'nom': 'Lomé', 'code': 'LM'},
        {'nom': 'Maritime', 'code': 'MR'},
        {'nom': 'Plateaux', 'code': 'PL'},
        {'nom': 'Centrale', 'code': 'CT'},
        {'nom': 'Kara', 'code': 'KR'},
        {'nom': 'Savanes', 'code': 'SV'},
    ]
    
    regions = {}
    for region_data in regions_data:
        region, created = Region.objects.get_or_create(
            nom=region_data['nom'],
            defaults={'code': region_data['code']}
        )
        regions[region.nom] = region
        if created:
            print(f"✅ Région '{region.nom}' créée")

    # Créer des préfectures
    prefectures_data = [
        ('Lomé', 'Golfe'),
        ('Maritime', 'Zio'),
        ('Maritime', 'Yoto'),
        ('Plateaux', 'Ogou'),
        ('Centrale', 'Tchaoudjo'),
        ('Kara', 'Kozah'),
    ]
    
    for region_nom, prefecture_nom in prefectures_data:
        if region_nom in regions:
            Prefecture.objects.get_or_create(
                region=regions[region_nom],
                nom=prefecture_nom
            )
    
    # Créer des agents actifs
    agents_data = [
        {
            'username': 'agent_lome',
            'email': 'agent.lome@togo.gov.tg',
            'first_name': 'Koffi',
            'last_name': 'Mensah',
            'region': regions['Lomé'],
        },
        {
            'username': 'agent_maritime',
            'email': 'agent.maritime@togo.gov.tg',
            'first_name': 'Ama',
            'last_name': 'Atsou',
            'region': regions['Maritime'],
        },
        {
            'username': 'agent_plateaux',
            'email': 'agent.plateaux@togo.gov.tg',
            'first_name': 'Yaovi',
            'last_name': 'Komlan',
            'region': regions['Plateaux'],
        },
        {
            'username': 'agent_centrale',
            'email': 'agent.centrale@togo.gov.tg',
            'first_name': 'Efua',
            'last_name': 'Tetteh',
            'region': regions['Centrale'],
        },
        {
            'username': 'agent_kara',
            'email': 'agent.kara@togo.gov.tg',
            'first_name': 'Komla',
            'last_name': 'Agbegninou',
            'region': regions['Kara'],
        }
    ]
    
    agents = []
    for agent_data in agents_data:
        agent, created = Utilisateur.objects.get_or_create(
            username=agent_data['username'],
            defaults={
                'email': agent_data['email'],
                'first_name': agent_data['first_name'],
                'last_name': agent_data['last_name'],
                'role': 'agent',
                'actif': True,
                'region': agent_data['region'],
                'last_login': timezone.now() - timedelta(minutes=random.randint(5, 120))
            }
        )
        agents.append(agent)
        if created:
            print(f"✅ Agent '{agent.get_full_name()}' créé pour {agent.region.nom}")

    # Créer des utilisateurs normaux
    users_data = [
        {'username': 'jean_test', 'first_name': 'Jean', 'last_name': 'Dupont'},
        {'username': 'marie_test', 'first_name': 'Marie', 'last_name': 'Kouassi'},
        {'username': 'pierre_test', 'first_name': 'Pierre', 'last_name': 'Affolabi'},
        {'username': 'fatou_test', 'first_name': 'Fatou', 'last_name': 'Traore'},
        {'username': 'koffi_test', 'first_name': 'Koffi', 'last_name': 'Agbodjan'},
    ]
    
    users = []
    for user_data in users_data:
        user, created = Utilisateur.objects.get_or_create(
            username=user_data['username'],
            defaults={
                'email': f"{user_data['username']}@example.com",
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'role': 'citoyen',
                'actif': True,
                'region': random.choice(list(regions.values()))
            }
        )
        users.append(user)
        if created:
            print(f"✅ Utilisateur '{user.get_full_name()}' créé")
    # Créer des déclarations en attente
    
    objets_perdus = [
        'Téléphone portable Samsung Galaxy S21',
        'Sac à main en cuir noir',
        'Portefeuille marron avec cartes',
        'Clés de voiture Toyota',
        'Ordinateur portable Dell',
        'Montre Casio dorée',
        'Lunettes de soleil Ray-Ban',
        'Carte d\'identité nationale',
        'Permis de conduire',
        'Passeport togolais'
    ]
    
    lieux_perte = [
        'Marché de Lomé',
        'Gare routière d\'Akodesséwa',
        'Université de Lomé',
        'Centre-ville Lomé',
        'Port autonome de Lomé',
        'Aéroport international de Lomé',
        'Stade de Kégué',
        'Hôpital CHU Tokoin'
    ]
    
    for i in range(8):
        declaration = Declaration.objects.create(
            declarant=random.choice(users),
            nom_objet=random.choice(objets_perdus),
            description=f"J'ai perdu mon {objets_perdus[i % len(objets_perdus)]} le {(timezone.now() - timedelta(days=random.randint(1, 5))).strftime('%d/%m/%Y')}. Merci de m'aider à le retrouver.",
            type_declaration=random.choice(['perdu', 'trouve']),
            lieu_precis=random.choice(lieux_perte),
            date_incident=timezone.now() - timedelta(days=random.randint(1, 7)),
            statut='cree',
            prefecture=Prefecture.objects.order_by('?').first(),
            region=random.choice(list(regions.values()))
        )
        print(f"✅ Déclaration '{declaration.nom_objet}' créée en attente")

    print("\n🎉 Données de test créées avec succès!")
    print(f"📊 Résumé:")
    print(f"   - {len(regions)} régions")
    print(f"   - {len(agents)} agents actifs")
    print(f"   - {len(users)} utilisateurs")
    print(f"   - 8 déclarations en attente")

if __name__ == '__main__':
    create_dashboard_test_data()