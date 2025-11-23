# core/fixtures.py
from django.contrib.auth import get_user_model
from .models import Objet, Signalement, Region, Prefecture

User = get_user_model()

def run():
    print("🚀 Création des données de test...")
    
    # -------- Régions et préfectures test --------
    region_maritime, _ = Region.objects.get_or_create(nom='Région Maritime')
    region_plateaux, _ = Region.objects.get_or_create(nom='Région des Plateaux')
    
    prefecture_lome, _ = Prefecture.objects.get_or_create(
        nom='Lomé',
        region=region_maritime
    )
    prefecture_kpalime, _ = Prefecture.objects.get_or_create(
        nom='Kpalimé',
        region=region_plateaux
    )

    # -------- Utilisateurs test --------
    if not User.objects.filter(username='superadmin').exists():
        User.objects.create_superuser(
            username='superadmin',
            email='superadmin@test.com',
            password='admin123',
            role='superadmin'
        )
        print("✅ Superadmin créé")

    if not User.objects.filter(username='admin1').exists():
        User.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='admin123',
            role='admin',
            region=region_maritime,
            prefecture=prefecture_lome
        )
        print("✅ Admin1 créé (Lomé)")

    if not User.objects.filter(username='admin2').exists():
        User.objects.create_user(
            username='admin2',
            email='admin2@test.com',
            password='admin123',
            role='admin',
            region=region_plateaux,
            prefecture=prefecture_kpalime
        )
        print("✅ Admin2 créé (Kpalimé)")

    if not User.objects.filter(username='user1').exists():
        User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='user123',
            role='citoyen',
            region=region_maritime,
            prefecture=prefecture_lome
        )
        print("✅ User1 créé (Citoyen Lomé)")

    if not User.objects.filter(username='user2').exists():
        User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='user123',
            role='citoyen',
            region=region_plateaux,
            prefecture=prefecture_kpalime
        )
        print("✅ User2 créé (Citoyen Kpalimé)")

    # -------- Objets test --------
    obj1, created = Objet.objects.get_or_create(
        nom="Carte d'identité",
        defaults={
            'description': "Carte d'identité perdue",
            'lieu_trouve': 'Marché de Lomé'
        }
    )
    if created:
        print("✅ Objet 'Carte d'identité' créé")

    obj2, created = Objet.objects.get_or_create(
        nom="Téléphone",
        defaults={
            'description': "iPhone perdu",
            'lieu_trouve': 'Université de Kpalimé'
        }
    )
    if created:
        print("✅ Objet 'Téléphone' créé")

    obj3, created = Objet.objects.get_or_create(
        nom="Sac",
        defaults={
            'description': "Sac à dos noir",
            'lieu_trouve': 'Gare routière'
        }
    )
    if created:
        print("✅ Objet 'Sac' créé")

    # -------- Signalements test --------
    admin1 = User.objects.get(username='admin1')
    user1 = User.objects.get(username='user1')
    user2 = User.objects.get(username='user2')

    signalement1, created = Signalement.objects.get_or_create(
        objet=obj1,
        defaults={
            'statut': 'perdu',
            'region': region_maritime,
            'prefecture': prefecture_lome,
            'lieu': 'Marché de Lomé',
            'commentaire': 'Carte perdue hier soir',
            'utilisateur': user1
        }
    )
    if created:
        print("✅ Signalement 'Carte perdue' créé")

    signalement2, created = Signalement.objects.get_or_create(
        objet=obj2,
        defaults={
            'statut': 'trouve',
            'region': region_plateaux,
            'prefecture': prefecture_kpalime,
            'lieu': 'Université de Kpalimé',
            'commentaire': 'Trouvé en salle de classe',
            'utilisateur': user2
        }
    )
    if created:
        print("✅ Signalement 'Téléphone trouvé' créé")

    signalement3, created = Signalement.objects.get_or_create(
        objet=obj3,
        defaults={
            'statut': 'perdu',
            'region': region_maritime,
            'prefecture': prefecture_lome,
            'lieu': 'Gare routière de Lomé',
            'commentaire': 'Sac oublié dans le bus',
            'utilisateur': admin1
        }
    )
    if created:
        print("✅ Signalement 'Sac perdu' créé")

    print("🎉 Toutes les données de test ont été créées avec succès !")
    print(f"📊 Résumé:")
    print(f"   Utilisateurs: {User.objects.count()}")
    print(f"   Régions: {Region.objects.count()}")
    print(f"   Préfectures: {Prefecture.objects.count()}")
    print(f"   Objets: {Objet.objects.count()}")
    print(f"   Signalements: {Signalement.objects.count()}")

if __name__ == "__main__":
    run()
