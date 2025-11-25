#!/usr/bin/env python
"""
Script pour créer des déclarations variées à valider dans l'interface admin
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

from core.models import Utilisateur, Declaration, Region, Prefecture, CategorieObjet

def create_validation_declarations():
    print("🎯 Création de déclarations variées pour validation...")

    # Récupérer les utilisateurs existants
    users = list(Utilisateur.objects.filter(role='citoyen'))
    if not users:
        print("❌ Aucun utilisateur trouvé. Exécutez d'abord create_dashboard_test_data.py")
        return

    regions = list(Region.objects.all())
    prefectures = list(Prefecture.objects.all())

    # Créer quelques catégories d'objets si elles n'existent pas
    categories_data = [
        {'nom': 'Électronique', 'description': 'Appareils électroniques'},
        {'nom': 'Vêtements', 'description': 'Vêtements et accessoires'},
        {'nom': 'Documents', 'description': 'Papiers officiels et documents'},
        {'nom': 'Bijoux', 'description': 'Bijoux et objets précieux'},
        {'nom': 'Bagages', 'description': 'Sacs, valises et bagages'},
        {'nom': 'Véhicules', 'description': 'Motos, vélos et véhicules'},
    ]
    
    categories = []
    for cat_data in categories_data:
        category, created = CategorieObjet.objects.get_or_create(
            nom=cat_data['nom'],
            defaults={'description': cat_data['description']}
        )
        categories.append(category)
        if created:
            print(f"✅ Catégorie '{category.nom}' créée")

    # Déclarations d'objets perdus
    objets_perdus = [
        {
            'nom': 'iPhone 14 Pro Max bleu',
            'description': 'Téléphone Apple iPhone 14 Pro Max de couleur bleu nuit, avec coque transparente et PopSocket. Contient mes photos de famille importantes. Récompense offerte.',
            'categorie': 'Électronique',
            'lieu': 'Marché de Lomé, près du stand de légumes',
            'type': 'perdu'
        },
        {
            'nom': 'Sac à main en cuir rouge',
            'description': 'Sac à main de marque Michael Kors, couleur rouge bordeaux. Contient portefeuille, clés de maison, carte d\'identité et permis de conduire. Très sentimental.',
            'categorie': 'Bagages',
            'lieu': 'Taxi collectif direction Kpalimé',
            'type': 'perdu'
        },
        {
            'nom': 'Portefeuille en cuir marron',
            'description': 'Portefeuille en cuir marron vieilli, contenant carte d\'identité au nom de MENSAH Koffi, permis de conduire, cartes bancaires et 25 000 FCFA en espèces.',
            'categorie': 'Documents',
            'lieu': 'Université de Lomé, amphithéâtre 500',
            'type': 'perdu'
        },
        {
            'nom': 'Montre Casio G-Shock noire',
            'description': 'Montre Casio G-Shock modèle GA-2100 noire. Cadeau de mon père pour mes 25 ans. Très attaché sentimentalement. Récompense 50 000 FCFA.',
            'categorie': 'Bijoux',
            'lieu': 'Plage de Lomé, près du phare',
            'type': 'perdu'
        },
        {
            'nom': 'Ordinateur portable Dell',
            'description': 'PC portable Dell Inspiron 15 3000, couleur gris. Contient tous mes documents de travail et projets universitaires. Autocollants de marques tech sur le couvercle.',
            'categorie': 'Électronique',
            'lieu': 'Café internet de Tokoin',
            'type': 'perdu'
        },
        {
            'nom': 'Clés de moto Yamaha',
            'description': 'Trousseau de clés avec clé de contact moto Yamaha NMAX 155cc bleue, clé de maison et porte-clés en forme d\'aigle doré. Moto immatriculée TG-5647-LM.',
            'categorie': 'Véhicules',
            'lieu': 'Gare routière d\'Akodesséwa',
            'type': 'perdu'
        }
    ]

    # Déclarations d'objets trouvés
    objets_trouves = [
        {
            'nom': 'Carte d\'identité ATSOU Marie',
            'description': 'Carte nationale d\'identité togolaise au nom de ATSOU Marie, née le 15/08/1985 à Lomé. Trouvée en bon état, pas de dégâts.',
            'categorie': 'Documents',
            'lieu': 'Parking du Grand Marché de Lomé',
            'type': 'trouve'
        },
        {
            'nom': 'Lunettes de vue rectangulaires',
            'description': 'Paire de lunettes de vue avec monture rectangulaire noire, verres progressifs. Trouvées dans un étui noir de marque Optic 2000.',
            'categorie': 'Vêtements',
            'lieu': 'Bus SOTRAL ligne 2, siège arrière',
            'type': 'trouve'
        },
        {
            'nom': 'Bracelet en or avec gravure',
            'description': 'Bracelet en or jaune avec une petite gravure "Pour ma fille chérie - Papa". Semble être un bijou de famille précieux.',
            'categorie': 'Bijoux',
            'lieu': 'Jardin public de Lomé, près de la fontaine',
            'type': 'trouve'
        },
        {
            'nom': 'Sac d\'école d\'enfant',
            'description': 'Cartable d\'école primaire rose avec motifs de licornes. Contient cahiers au nom de KOFI Ama, classe CE2. École Sainte-Marie inscrite à l\'intérieur.',
            'categorie': 'Bagages',
            'lieu': 'Arrêt de bus devant la Poste centrale',
            'type': 'trouve'
        },
        {
            'nom': 'Téléphone Samsung Galaxy A52',
            'description': 'Smartphone Samsung Galaxy A52 blanc avec coque de protection transparente. Écran de verrouillage affiche photo de famille. Batterie faible.',
            'categorie': 'Électronique',
            'lieu': 'Restaurant "Chez Maman" à Bè',
            'type': 'trouve'
        }
    ]

    # Créer les déclarations
    all_declarations = objets_perdus + objets_trouves
    
    for i, item in enumerate(all_declarations):
        # Trouver la catégorie
        categorie = next((cat for cat in categories if cat.nom == item['categorie']), None)
        
        # Créer la déclaration
        declaration = Declaration.objects.create(
            declarant=random.choice(users),
            type_declaration=item['type'],
            nom_objet=item['nom'],
            description=item['description'],
            categorie=categorie,
            lieu_precis=item['lieu'],
            date_incident=timezone.now().date() - timedelta(days=random.randint(1, 10)),
            statut='cree',
            region=random.choice(regions) if regions else None,
            prefecture=random.choice(prefectures) if prefectures else None,
        )
        
        type_emoji = "🔍" if item['type'] == 'perdu' else "✨"
        print(f"{type_emoji} Déclaration '{item['nom']}' créée ({item['type']})")

    print(f"\n🎉 {len(all_declarations)} déclarations créées avec succès!")
    print("\n📋 Résumé des déclarations :")
    print(f"   🔍 {len(objets_perdus)} objets perdus")
    print(f"   ✨ {len(objets_trouves)} objets trouvés")
    print("\n🎯 Vous pouvez maintenant les valider depuis l'interface admin :")
    print("   👉 http://localhost:8000/togoretrouve-admin/")

if __name__ == '__main__':
    create_validation_declarations()