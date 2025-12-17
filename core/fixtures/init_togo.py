from core.models import Region, Prefecture

# 1️⃣ Création des régions
regions = {
    "Maritime": ["Lomé", "Lacs", "Vo", "Yoto", "Zio"],
    "Plateaux": ["Haho", "Amou", "Wawa", "Ogou", "Danyi"],
    "Centrale": ["Blitta", "Sotouboua", "Tchamba", "Tchaoudjo"],
    "Kara": ["Kozah", "Assoli", "Bassar", "Dankpen", "Kéran", "Binah"],
    "Savanes": ["Tône", "Cinkassé", "Kpendjal", "Oti", "Tandjoaré"],
}

for region_nom, prefs in regions.items():
    region, _ = Region.objects.get_or_create(nom=region_nom)
    for pref_nom in prefs:
        Prefecture.objects.get_or_create(nom=pref_nom, region=region)

print("✅ Régions et préfectures ajoutées avec succès !")
