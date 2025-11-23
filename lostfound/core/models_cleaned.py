from django.contrib.auth.models import AbstractUser
from django.db import models

class Region(models.Model):
    nom = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nom

class Prefecture(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='prefectures')
    nom = models.CharField(max_length=100)

    class Meta:
        unique_together = ('region', 'nom')

    def __str__(self):
        return f"{self.nom} ({self.region.nom})"

class StructureLocale(models.Model):
    TYPE_CHOICES = [
        ('commissariat', 'Commissariat'),
        ('mairie', 'Mairie'),
        ('autre', 'Autre structure locale'),
    ]
    nom = models.CharField(max_length=150)
    type_structure = models.CharField(max_length=20, choices=TYPE_CHOICES)
    prefecture = models.ForeignKey(Prefecture, on_delete=models.CASCADE, related_name='structures_locales')

    def __str__(self):
        return f"{self.nom} - {self.prefecture.nom}"

class Utilisateur(AbstractUser):
    telephone = models.CharField(max_length=20, blank=True, null=True)

    ROLE_CHOICES = [
        ('citoyen', 'Citoyen'),
        ('admin', 'Administrateur'),
        ('agent', 'Agent de gestion'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='citoyen')

    region = models.ForeignKey('Region', on_delete=models.SET_NULL, blank=True, null=True)
    prefecture = models.ForeignKey('Prefecture', on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

class Objet(models.Model):
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    categorie = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to='objets/', blank=True, null=True)
    lieu_trouve = models.CharField(max_length=200, blank=True)
    date_trouve = models.DateField(blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom

class Signalement(models.Model):
    TYPE_CHOICES = [
        ('perdu', 'Perdu'),
        ('trouve', 'Trouvé'),
        ('retourne', 'Retourné au propriétaire'),
    ]

    objet = models.ForeignKey('Objet', on_delete=models.CASCADE, related_name='signalements')
    utilisateur = models.ForeignKey('Utilisateur', on_delete=models.CASCADE, related_name='signalements', null=True, blank=True)
    statut = models.CharField(max_length=20, choices=TYPE_CHOICES, default='perdu')
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    prefecture = models.ForeignKey(Prefecture, on_delete=models.SET_NULL, null=True, blank=True)
    structure_locale = models.ForeignKey(StructureLocale, on_delete=models.SET_NULL, null=True, blank=True)
    lieu = models.CharField(max_length=200, blank=True)
    commentaire = models.TextField(blank=True)
    photo = models.ImageField(upload_to='signalements/', blank=True, null=True)
    date_signalement = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.objet.nom} - {self.get_statut_display()} ({self.region})"

class ObjetPerdu(models.Model):
    nom = models.CharField(max_length=100)
    lieu = models.CharField(max_length=100)
    date_perte = models.DateField()
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nom} - {self.lieu}"
