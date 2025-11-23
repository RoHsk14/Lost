from django.contrib.auth.models import AbstractUser
from django.db import models



# class Region(models.Model):
#     nom = models.CharField(max_length=100, unique=True)

#     def __str__(self):
#         return self.nom


# class Prefecture(models.Model):
#     region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='prefectures')
#     nom = models.CharField(max_length=100)

#     def __str__(self):
#         return f"{self.nom} ({self.region.nom})"

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



# class Utilisateur(AbstractUser):
#     telephone = models.CharField(max_length=20, blank=True, null=True)
#     ROLE_CHOICES = [
#         ('citoyen', 'Citoyen'),
#         ('admin', 'Administrateur'),
#         ('agent', 'Agent de gestion'),
#     ]
#     role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='citoyen')
#     zone = models.CharField(max_length=100, blank=True, null=True)  # <-- Ajouter ce champ

#     def __str__(self):
#         return f"{self.username} ({self.role})"

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
    lieu_trouve = models.CharField(max_length=200, blank=True)  # correspond au champ "Lieu"
    date_trouve = models.DateField(blank=True, null=True)        # correspond au champ "Date"
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom




class ObjetPerdu(models.Model):
    nom = models.CharField(max_length=100)
    lieu = models.CharField(max_length=100)
    date_perte = models.DateField()
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nom} - {self.lieu}"

# class Signalement(models.Model):
#     STATUT_CHOICES = [
#         ('perdu', 'Perdu'),
#         ('trouve', 'Trouvé'),
#         ('retourne', 'Retourné à son propriétaire'),
#     ]

#     objet = models.ForeignKey(Objet, on_delete=models.CASCADE, related_name='signalements')
#     utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='signalements')
#     statut = models.CharField(max_length=12, choices=STATUT_CHOICES, default='perdu')
#     lieu = models.CharField(max_length=200, blank=True)
#     date_signalement = models.DateTimeField(auto_now_add=True)
#     commentaire = models.TextField(blank=True)
#     photo = models.ImageField(upload_to='signalements/', blank=True, null=True)  # ← ajouté

#     def __str__(self):
#         return f"{self.objet.nom} - {self.statut} par {self.utilisateur.username}"


# class Signalement(models.Model):
#     TYPE_CHOICES = [
#         ('Perdu', 'Perdu'),
#         ('Retrouvé', 'Retrouvé')
#     ]
#     objet = models.ForeignKey(Objet, on_delete=models.CASCADE)
#     statut = models.CharField(max_length=50)
#     # signalement_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
#     lieu = models.CharField(max_length=200)
#     commentaire = models.TextField(blank=True)
#     date_signalement = models.DateTimeField(auto_now_add=True)
#     utilisateur = models.ForeignKey('Utilisateur', on_delete=models.CASCADE, null=True, blank=True)
#     photo = models.ImageField(upload_to='signalements/', blank=True, null=True)
#     # signalement_type = models.CharField(max_length=20, choices=[('Perdu','Perdu'),('Retrouvé','Retrouvé')])
#     zone = models.CharField(max_length=100, blank=True, null=True)
#     signalement_type = models.CharField(
#         max_length=20, 
#         choices=TYPE_CHOICES, 
#         default='Perdu'   # <-- valeur par défaut
#     )


class CommentaireAnonyme(models.Model):
    """Commentaires anonymes sur les signalements"""
    signalement = models.ForeignKey(Signalement, on_delete=models.CASCADE, related_name='commentaires_anonymes')
    contenu = models.TextField(max_length=1000, help_text="Votre commentaire (max 1000 caractères)")
    pseudo = models.CharField(max_length=50, blank=True, help_text="Pseudo optionnel (ou laissez vide pour 'Anonyme')")
    email = models.EmailField(blank=True, help_text="Email optionnel (ne sera pas affiché publiquement)")
    date_creation = models.DateTimeField(auto_now_add=True)
    est_approuve = models.BooleanField(default=True, help_text="Commentaire approuvé pour affichage")
    
    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Commentaire anonyme"
        verbose_name_plural = "Commentaires anonymes"
    
    def __str__(self):
        pseudo = self.pseudo or "Anonyme"
        return f"Commentaire de {pseudo} sur {self.signalement.objet.nom}"
    
    def get_display_name(self):
        """Retourne le nom d'affichage (pseudo ou 'Anonyme')"""
        return self.pseudo or "Anonyme"
