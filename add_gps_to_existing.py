"""
Script pour ajouter des coordonnées GPS aux signalements existants
Utilisation: python manage.py shell < add_gps_to_existing.py
"""

from core.models import Declaration
from decimal import Decimal

# Coordonnées de différents quartiers de Lomé, Togo
locations = [
    {"name": "Centre-ville Lomé", "lat": Decimal("6.1319"), "lon": Decimal("1.2228")},
    {"name": "Aéroport de Lomé", "lat": Decimal("6.1656"), "lon": Decimal("1.2545")},
    {"name": "Marché de Tokoin", "lat": Decimal("6.1467"), "lon": Decimal("1.2314")},
    {"name": "Université de Lomé", "lat": Decimal("6.1701"), "lon": Decimal("1.2116")},
    {"name": "Port de Lomé", "lat": Decimal("6.1372"), "lon": Decimal("1.2789")},
    {"name": "Stade de Kégué", "lat": Decimal("6.1189"), "lon": Decimal("1.2156")},
    {"name": "Marché de Hedzranawoé", "lat": Decimal("6.1256"), "lon": Decimal("1.2089")},
    {"name": "Boulevard du 13 Janvier", "lat": Decimal("6.1278"), "lon": Decimal("1.2167")},
]

# Récupérer tous les signalements sans coordonnées GPS
signalements = Declaration.objects.filter(latitude__isnull=True, longitude__isnull=True)

print(f"\n🔍 Trouvé {signalements.count()} signalement(s) sans coordonnées GPS")

if signalements.count() == 0:
    print("✅ Tous les signalements ont déjà des coordonnées GPS !")
else:
    print("\n📍 Ajout de coordonnées GPS aléatoires...\n")
    
    for i, signalement in enumerate(signalements):
        # Utiliser une localisation différente pour chaque signalement
        location = locations[i % len(locations)]
        
        signalement.latitude = location["lat"]
        signalement.longitude = location["lon"]
        signalement.save(update_fields=['latitude', 'longitude'])
        
        print(f"✅ {signalement.nom_objet[:30]:30} → {location['name']:25} ({location['lat']}, {location['lon']})")
    
    print(f"\n🎉 {signalements.count()} signalement(s) mis à jour avec succès !")
    print("\n💡 Vous pouvez maintenant voir ces signalements sur la carte à http://localhost:8000/signalements/")
