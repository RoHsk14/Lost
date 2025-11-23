#!/usr/bin/env python
"""
Script pour créer des données de test pour la page d'accueil
"""

import os
import sys
import django
from django.utils import timezone
from datetime import datetime, timedelta
import random

# Configuration Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lostfound.settings')
django.setup()

from core.models import Objet, Signalement, Utilisateur, Region, Prefecture

def create_test_data():
    print("🚀 Création de données de test...")
    
    # Créer des régions et préfectures si elles n'existent pas
    region_maritime = Region.objects.get_or_create(nom="Région Maritime")[0]
    region_plateaux = Region.objects.get_or_create(nom="Région des Plateaux")[0]
    region_centrale = Region.objects.get_or_create(nom="Région Centrale")[0]
    
    Prefecture.objects.get_or_create(nom="Golfe", region=region_maritime)
    Prefecture.objects.get_or_create(nom="Vo", region=region_maritime)
    Prefecture.objects.get_or_create(nom="Kloto", region=region_plateaux)
    
    # Créer des utilisateurs de test
    test_users = []
    for i in range(5):
        username = f"testuser{i+1}"
        user, created = Utilisateur.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'telephone': f'9001000{i}',
                'role': 'citoyen',
                'region': random.choice([region_maritime, region_plateaux, region_centrale])
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
        test_users.append(user)
    
    print(f"✅ {len(test_users)} utilisateurs créés/vérifiés")
    
    # Données d'objets réalistes
    objets_data = [
        {
            'nom': 'iPhone 13 Pro Bleu',
            'description': 'iPhone 13 Pro de couleur bleu sierra avec étui en cuir noir. Écran fissuré sur le coin supérieur droit.',
            'categorie': 'electronique',
            'lieu_trouve': 'Marché du Grand Lomé, secteur des légumes',
        },
        {
            'nom': 'Portefeuille en cuir marron',
            'description': 'Portefeuille en cuir marron avec carte d\'identité et cartes bancaires. Initiales "A.K." gravées à l\'intérieur.',
            'categorie': 'accessoire',
            'lieu_trouve': 'Bus SOTRAM ligne 2, arrêt Université',
        },
        {
            'nom': 'Clés de voiture Toyota',
            'description': 'Trousseau avec 3 clés : clé de voiture Toyota Corolla, clé de maison et clé de cadenas. Porte-clés \'I ❤️ Togo\'.',
            'categorie': 'cles',
            'lieu_trouve': 'Parking du CHU-SO',
        },
        {
            'nom': 'Sac à dos noir Adidas',
            'description': 'Sac à dos noir Adidas avec 3 rayures blanches. Contient cahiers d\'école, calculatrice et trousse.',
            'categorie': 'accessoire',
            'lieu_trouve': 'Lycée de Tokoin',
        },
        {
            'nom': 'Montre Casio G-Shock rouge',
            'description': 'Montre de sport Casio G-Shock de couleur rouge. Bracelet en caoutchouc, résistante à l\'eau.',
            'categorie': 'accessoire',
            'lieu_trouve': 'Stade de Kégué',
        },
        {
            'nom': 'Carte d\'étudiant UL',
            'description': 'Carte d\'étudiant de l\'Université de Lomé, faculté des sciences. Nom partiellement visible.',
            'categorie': 'document',
            'lieu_trouve': 'Bibliothèque universitaire',
        },
        {
            'nom': 'Écouteurs AirPods',
            'description': 'Écouteurs Apple AirPods dans leur boîtier blanc. Un écouteur manque.',
            'categorie': 'electronique',
            'lieu_trouve': 'Café de la Paix, centre-ville',
        },
        {
            'nom': 'Lunettes de vue',
            'description': 'Lunettes de vue avec monture dorée et verres progressifs. Étui violet inclus.',
            'categorie': 'accessoire',
            'lieu_trouve': 'Marché de Gbadago',
        }
    ]
    
    # Créer les objets
    objets_crees = []
    for i, data in enumerate(objets_data):
        # Dates aléatoires dans les 15 derniers jours
        date_creation = timezone.now() - timedelta(days=random.randint(0, 15))
        date_trouve = date_creation - timedelta(days=random.randint(0, 5))
        
        objet, created = Objet.objects.get_or_create(
            nom=data['nom'],
            defaults={
                'description': data['description'],
                'categorie': data['categorie'],
                'lieu_trouve': data['lieu_trouve'],
                'date_trouve': date_trouve,
                'date_creation': date_creation,
            }
        )
        
        if created:
            objets_crees.append(objet)
    
    print(f"✅ {len(objets_crees)} objets créés")
    
    # Créer des signalements pour ces objets
    signalements_crees = []
    statuts = ['perdu', 'trouve', 'retourne']
    
    for objet in objets_crees[:6]:  # Signalements pour les 6 premiers objets
        user = random.choice(test_users)
        statut = random.choice(statuts)
        
        # Commentaires réalistes selon le statut
        if statut == 'perdu':
            commentaires = [
                f"J'ai perdu mon {objet.nom.lower()} hier soir. C'est très important pour moi, récompense offerte !",
                f"Bonjour, je recherche mon {objet.nom.lower()}. Si vous l'avez trouvé, merci de me contacter.",
                f"URGENT : J'ai perdu mon {objet.nom.lower()}. Contient des documents importants.",
            ]
        elif statut == 'trouve':
            commentaires = [
                f"J'ai trouvé ce {objet.nom.lower()} ce matin. Je le garde en sécurité en attendant le propriétaire.",
                f"Objet trouvé : {objet.nom.lower()}. Contactez-moi pour le récupérer avec une preuve d'identité.",
                f"Quelqu'un a perdu son {objet.nom.lower()} ? Je l'ai trouvé et aimerais le rendre.",
            ]
        else:  # retourne
            commentaires = [
                f"Merci à la personne qui a trouvé mon {objet.nom.lower()} ! Récupéré avec succès.",
                f"Heureux de dire que mon {objet.nom.lower()} a été retrouvé ! Merci à la communauté.",
                f"Objet récupéré ! Grand merci au bon samaritain qui l'a trouvé.",
            ]
        
        commentaire = random.choice(commentaires)
        
        date_signalement = timezone.now() - timedelta(
            days=random.randint(0, 10),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        signalement, created = Signalement.objects.get_or_create(
            objet=objet,
            utilisateur=user,
            defaults={
                'statut': statut,
                'lieu': objet.lieu_trouve,
                'commentaire': commentaire,
                'region': user.region,
                'date_signalement': date_signalement,
            }
        )
        
        if created:
            signalements_crees.append(signalement)
    
    print(f"✅ {len(signalements_crees)} signalements créés")
    
    # Afficher les statistiques
    total_objets = Objet.objects.count()
    total_signalements = Signalement.objects.count()
    signalements_perdus = Signalement.objects.filter(statut='perdu').count()
    signalements_trouves = Signalement.objects.filter(statut='trouve').count()
    
    print("\n📊 STATISTIQUES FINALES :")
    print(f"   📦 Objets total : {total_objets}")
    print(f"   📋 Signalements total : {total_signalements}")
    print(f"   😞 Objets perdus : {signalements_perdus}")
    print(f"   😊 Objets trouvés : {signalements_trouves}")
    print(f"   ✅ Objets rendus : {Signalement.objects.filter(statut='retourne').count()}")
    
    print("\n🎉 Données de test créées avec succès !")
    print("💡 Vous pouvez maintenant voir du contenu sur la page d'accueil")

if __name__ == "__main__":
    create_test_data()
