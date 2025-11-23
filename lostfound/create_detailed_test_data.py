import os
import sys
import django

# Chemin vers le projet Django
sys.path.append('c:/Users/MR/Desktop/Stage 2/Lost/lostfound')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lostfound.settings')

django.setup()

from core.models import *
from django.contrib.auth import get_user_model

User = get_user_model()

# Créer des régions et préfectures de test
print("🌍 Création des régions et préfectures...")

# Région Maritime
region_maritime, _ = Region.objects.get_or_create(nom="Maritime")
Prefecture.objects.get_or_create(nom="Golfe", region=region_maritime)
Prefecture.objects.get_or_create(nom="Lacs", region=region_maritime)

# Région des Plateaux  
region_plateaux, _ = Region.objects.get_or_create(nom="Plateaux")
Prefecture.objects.get_or_create(nom="Ogou", region=region_plateaux)

print("🏛️ Régions et préfectures créées !")

# Créer des utilisateurs de test
print("👥 Création des utilisateurs...")
utilisateur1, _ = User.objects.get_or_create(
    username="marie_lomé",
    defaults={
        'email': 'marie@test.com',
        'telephone': '22890123456',
        'role': 'citoyen',
        'region': region_maritime
    }
)

utilisateur2, _ = User.objects.get_or_create(
    username="kevin_plateau",
    defaults={
        'email': 'kevin@test.com', 
        'telephone': '22892345678',
        'role': 'citoyen',
        'region': region_plateaux
    }
)

utilisateur3, _ = User.objects.get_or_create(
    username="fatou_golfe",
    defaults={
        'email': 'fatou@test.com',
        'telephone': '22893456789', 
        'role': 'citoyen',
        'region': region_maritime
    }
)

print("✅ Utilisateurs créés !")

# Créer des objets avec différentes catégories
print("📦 Création des objets...")

# Objets trouvés
objet1, _ = Objet.objects.get_or_create(
    nom="iPhone 14 Pro Bleu",
    defaults={
        'description': 'iPhone 14 Pro couleur bleu sierra avec coque transparente. Quelques rayures sur l\'écran.',
        'categorie': 'electronique',
        'lieu_trouve': 'Marché du Grand Lomé',
        'date_trouve': '2024-11-20'
    }
)

objet2, _ = Objet.objects.get_or_create(
    nom="Portefeuille en cuir noir",
    defaults={
        'description': 'Portefeuille en cuir noir marque Lacoste, contient des cartes et quelques billets.',
        'categorie': 'accessoire',
        'lieu_trouve': 'Université de Lomé',
        'date_trouve': '2024-11-19'
    }
)

objet3, _ = Objet.objects.get_or_create(
    nom="Clés Toyota avec porte-clés rouge",
    defaults={
        'description': 'Trousseau de clés Toyota avec porte-clés rouge en forme de cœur. 3 clés au total.',
        'categorie': 'cles',
        'lieu_trouve': 'Pharmacie Togolaise',
        'date_trouve': '2024-11-21'
    }
)

# Objets perdus
objet4, _ = Objet.objects.get_or_create(
    nom="Sac à dos Nike noir",
    defaults={
        'description': 'Sac à dos Nike noir avec logo blanc. Contient des documents importants et un ordinateur portable.',
        'categorie': 'accessoire',
        'lieu_trouve': '',  # Pas trouvé, c'est un objet perdu
        'date_trouve': None
    }
)

objet5, _ = Objet.objects.get_or_create(
    nom="Samsung Galaxy S23",
    defaults={
        'description': 'Téléphone Samsung Galaxy S23 couleur crème avec coque violette et autocollant papillon.',
        'categorie': 'electronique',
        'lieu_trouve': '',
        'date_trouve': None
    }
)

objet6, _ = Objet.objects.get_or_create(
    nom="Documents CNI + Permis",
    defaults={
        'description': 'Pochette contenant carte d\'identité nationale et permis de conduire au nom de AKOTO Koffi.',
        'categorie': 'document',
        'lieu_trouve': '',
        'date_trouve': None
    }
)

print("📱 Objets créés !")

# Créer des signalements d'objets TROUVÉS
print("😊 Création des signalements d'objets trouvés...")

signalement1, _ = Signalement.objects.get_or_create(
    objet=objet1,
    utilisateur=utilisateur1,
    defaults={
        'statut': 'trouve',
        'region': region_maritime,
        'prefecture': Prefecture.objects.get(nom="Golfe"),
        'lieu': 'Marché du Grand Lomé, secteur des téléphones',
        'commentaire': 'J\'ai trouvé ce téléphone ce matin vers 8h30 près d\'un vendeur de fruits. Il semble en bon état malgré quelques rayures.',
    }
)

signalement2, _ = Signalement.objects.get_or_create(
    objet=objet2,
    utilisateur=utilisateur2,
    defaults={
        'statut': 'trouve',
        'region': region_maritime,
        'prefecture': Prefecture.objects.get(nom="Golfe"),
        'lieu': 'Université de Lomé, amphithéâtre 500',
        'commentaire': 'Portefeuille trouvé sous un banc après le cours de 14h. Contient des cartes d\'identité.',
    }
)

signalement3, _ = Signalement.objects.get_or_create(
    objet=objet3,
    utilisateur=utilisateur3,
    defaults={
        'statut': 'trouve',
        'region': region_maritime,
        'prefecture': Prefecture.objects.get(nom="Golfe"),
        'lieu': 'Pharmacie Togolaise, Bè-Klikamé',
        'commentaire': 'Clés trouvées dans le parking de la pharmacie. Le propriétaire les a probablement fait tomber.',
    }
)

print("✅ Signalements d'objets trouvés créés !")

# Créer des signalements d'objets PERDUS  
print("😞 Création des signalements d'objets perdus...")

signalement4, _ = Signalement.objects.get_or_create(
    objet=objet4,
    utilisateur=utilisateur1,
    defaults={
        'statut': 'perdu',
        'region': region_maritime,
        'prefecture': Prefecture.objects.get(nom="Golfe"),
        'lieu': 'Bus SOTRAM, ligne Lomé-Agoè',
        'commentaire': 'J\'ai perdu mon sac dans le bus ce matin. Il contenait mon laptop et des documents de travail très importants. Récompense proposée !',
    }
)

signalement5, _ = Signalement.objects.get_or_create(
    objet=objet5,
    utilisateur=utilisateur2,
    defaults={
        'statut': 'perdu',
        'region': region_plateaux,
        'prefecture': Prefecture.objects.get(nom="Ogou"),
        'lieu': 'Centre-ville de Atakpamé',
        'commentaire': 'Téléphone perdu hier soir vers 19h près du marché central. Toutes mes photos de famille sont dessus !',
    }
)

signalement6, _ = Signalement.objects.get_or_create(
    objet=objet6,
    utilisateur=utilisateur3,
    defaults={
        'statut': 'perdu',
        'region': region_maritime,
        'prefecture': Prefecture.objects.get(nom="Lacs"),
        'lieu': 'Aného, près de la plage',
        'commentaire': 'Documents perdus pendant une sortie à la plage. CNI et permis de conduire dans une pochette plastique bleue.',
    }
)

print("✅ Signalements d'objets perdus créés !")

print("\n🎉 Données de test créées avec succès !")
print(f"📊 Résumé :")
print(f"   - {Region.objects.count()} régions")
print(f"   - {Prefecture.objects.count()} préfectures") 
print(f"   - {User.objects.filter(role='citoyen').count()} utilisateurs citoyens")
print(f"   - {Objet.objects.count()} objets")
print(f"   - {Signalement.objects.filter(statut='trouve').count()} signalements d'objets trouvés")
print(f"   - {Signalement.objects.filter(statut='perdu').count()} signalements d'objets perdus")
print("\n🌐 Vous pouvez maintenant tester la page d'accueil !")
