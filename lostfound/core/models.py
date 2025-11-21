from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone


# ============================================================================
# MODÈLES AUXILIAIRES (Region, Prefecture, StructureLocale)
# Ces modèles sont conservés pour la compatibilité et utilisés par Localisation
# ============================================================================
class Region(models.Model):
    """Modèle pour les régions du Togo."""
    nom = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'Région'
        verbose_name_plural = 'Régions'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Prefecture(models.Model):
    """Modèle pour les préfectures du Togo."""
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name='prefectures'
    )
    nom = models.CharField(max_length=100)

    class Meta:
        verbose_name = 'Préfecture'
        verbose_name_plural = 'Préfectures'
        unique_together = ('region', 'nom')
        ordering = ['region', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.region.nom})"


class StructureLocale(models.Model):
    """Modèle pour les structures locales (commissariats, mairies, etc.)."""
    TYPE_CHOICES = [
        ('commissariat', 'Commissariat'),
        ('mairie', 'Mairie'),
        ('autre', 'Autre structure locale'),
    ]
    
    nom = models.CharField(max_length=150)
    type_structure = models.CharField(max_length=20, choices=TYPE_CHOICES)
    prefecture = models.ForeignKey(
        Prefecture,
        on_delete=models.CASCADE,
        related_name='structures_locales'
    )

    class Meta:
        verbose_name = 'Structure locale'
        verbose_name_plural = 'Structures locales'
        ordering = ['prefecture', 'nom']

    def __str__(self):
        return f"{self.nom} - {self.prefecture.nom}"


# ============================================================================
# 1. UTILISATEUR (Custom User Model)
# ============================================================================
class Utilisateur(AbstractUser):
    """
    Modèle utilisateur personnalisé pour TogoRetrouve.
    Étend AbstractUser avec des champs supplémentaires et des rôles.
    """
    ROLE_CHOICES = [
        ('citoyen', 'Citoyen'),
        ('agent', 'Agent de gestion'),
        ('admin', 'Administrateur'),
    ]
    
    # Champs de profil
    nom = models.CharField(max_length=100, blank=True)
    prenom = models.CharField(max_length=100, blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    adresse = models.CharField(max_length=255, blank=True)
    
    # Localisation (ForeignKeys pour meilleure normalisation)
    region = models.ForeignKey(
        'Region',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='utilisateurs'
    )
    prefecture = models.ForeignKey(
        'Prefecture',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='utilisateurs'
    )
    
    # Rôle utilisateur
    role = models.CharField(
        max_length=10, 
        choices=ROLE_CHOICES, 
        default='USER',
        db_index=True
    )
    
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
    
    def can_validate_objects(self):
        """Vérifie si l'utilisateur peut valider des objets."""
        return self.role in ['agent', 'admin']
    
    def can_access_admin(self):
        """Vérifie si l'utilisateur peut accéder à l'administration."""
        return self.role == 'admin' or self.is_superuser


# ============================================================================
# 2. LOCALISATION
# ============================================================================
class Localisation(models.Model):
    """
    Modèle pour gérer les informations de localisation des objets.
    """
    region = models.CharField(max_length=100)
    prefecture = models.CharField(max_length=100)
    quartier = models.CharField(max_length=100)
    commissariat = models.CharField(max_length=100, blank=True)
    
    # Coordonnées GPS optionnelles
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Localisation'
        verbose_name_plural = 'Localisations'
        ordering = ['region', 'prefecture', 'quartier']
        indexes = [
            models.Index(fields=['region', 'prefecture']),
            models.Index(fields=['quartier']),
        ]
    
    def __str__(self):
        parts = [self.quartier, self.prefecture, self.region]
        if self.commissariat:
            parts.insert(0, f"Commissariat {self.commissariat}")
        return ', '.join(parts)
    
    def clean(self):
        """Validation personnalisée."""
        super().clean()
        if self.latitude and (self.latitude < -90 or self.latitude > 90):
            raise ValidationError('La latitude doit être entre -90 et 90.')
        if self.longitude and (self.longitude < -180 or self.longitude > 180):
            raise ValidationError('La longitude doit être entre -180 et 180.')


# ============================================================================
# 3. OBJET
# ============================================================================
class Objet(models.Model):
    """
    Modèle principal pour les objets perdus et trouvés.
    Gère le cycle de vie complet d'un objet.
    """
    TYPE_OBJET_CHOICES = [
        ('TELEPHONE', 'Téléphone'),
        ('PORTEFEUILLE', 'Portefeuille'),
        ('CLES', 'Clés'),
        ('DOCUMENT', 'Document'),
        ('BIJOU', 'Bijou'),
        ('VETEMENT', 'Vêtement'),
        ('AUTRE', 'Autre'),
    ]
    
    ETAT_CHOICES = [
        ('CREE', 'Créé'),
        ('EN_VALIDATION', 'En validation'),
        ('VALIDE', 'Validé'),
        ('PUBLIE', 'Publié'),
        ('RECLAME', 'Réclamé'),
        ('EN_VERIFICATION', 'En vérification'),
        ('RESTITUE', 'Restitué'),
        ('REFUSE', 'Refusé'),
    ]
    
    # Informations de base
    typeObjet = models.CharField(
        max_length=20,
        choices=TYPE_OBJET_CHOICES,
        db_index=True,
        default='AUTRE'
    )
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    couleur = models.CharField(max_length=100, blank=True)
    marque = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to='objets/', blank=True, null=True)
    
    # Localisation et dates
    lieuPerte = models.ForeignKey(
        Localisation,
        on_delete=models.PROTECT,
        related_name='objets',
        null=True,
        blank=True
    )
    datePerte = models.DateTimeField(null=True, blank=True)
    dateDeclaration = models.DateTimeField(default=timezone.now)
    
    # Relations utilisateurs
    proprietaire = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='objets_proprietaire',
        help_text="Propriétaire de l'objet (null pour objets trouvés)"
    )
    agent_responsable = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='objets_geres',
        limit_choices_to={'role': 'agent'}
    )
    
    # État et type
    etat = models.CharField(
        max_length=20,
        choices=ETAT_CHOICES,
        default='CREE',
        db_index=True
    )
    est_perdu = models.BooleanField(
        default=True,
        help_text="True=perdu, False=trouvé"
    )
    
    class Meta:
        verbose_name = 'Objet'
        verbose_name_plural = 'Objets'
        ordering = ['-dateDeclaration']
        indexes = [
            models.Index(fields=['etat', 'est_perdu']),
            models.Index(fields=['typeObjet']),
            models.Index(fields=['-dateDeclaration']),
            models.Index(fields=['datePerte']),
        ]
        permissions = [
            ("can_validate_objet", "Peut valider un objet"),
            ("can_publish_objet", "Peut publier un objet"),
        ]
    
    def __str__(self):
        type_str = "Perdu" if self.est_perdu else "Trouvé"
        return f"{self.nom} ({type_str}) - {self.get_etat_display()}"
    
    def change_etat(self, nouvel_etat, agent=None):
        """
        Change l'état de l'objet avec validation.
        
        Args:
            nouvel_etat: Le nouvel état à appliquer
            agent: L'agent responsable du changement (optionnel)
        
        Returns:
            bool: True si le changement a réussi
        """
        etats_valides = dict(self.ETAT_CHOICES).keys()
        if nouvel_etat not in etats_valides:
            raise ValidationError(f"État invalide: {nouvel_etat}")
        
        # Règles de transition d'état
        transitions_autorisees = {
            'CREE': ['EN_VALIDATION', 'REFUSE'],
            'EN_VALIDATION': ['VALIDE', 'REFUSE'],
            'VALIDE': ['PUBLIE'],
            'PUBLIE': ['RECLAME'],
            'RECLAME': ['EN_VERIFICATION'],
            'EN_VERIFICATION': ['RESTITUE', 'REFUSE'],
        }
        
        if nouvel_etat not in transitions_autorisees.get(self.etat, []):
            raise ValidationError(
                f"Transition non autorisée de {self.etat} vers {nouvel_etat}"
            )
        
        self.etat = nouvel_etat
        if agent and agent.can_validate_objects():
            self.agent_responsable = agent
        self.save()
        return True
    
    def peut_etre_reclame(self):
        """Vérifie si l'objet peut être réclamé."""
        return self.etat == 'PUBLIE'
    
    def get_absolute_url(self):
        """Retourne l'URL de détail de l'objet."""
        return reverse('objet_detail', kwargs={'pk': self.pk})
    
    def clean(self):
        """Validation personnalisée."""
        super().clean()
        if self.datePerte and self.datePerte > timezone.now():
            raise ValidationError("La date de perte ne peut pas être dans le futur.")
        if not self.lieuPerte and not hasattr(self, '_skip_lieu_validation'):
            # Permet la validation pour les anciens objets sans lieuPerte
            pass


# ============================================================================
# 4. DECLARATION
# ============================================================================
class Declaration(models.Model):
    """
    Modèle pour gérer les déclarations d'objets perdus ou trouvés.
    """
    TYPE_DECLARATION_CHOICES = [
        ('PERDU', 'Perdu'),
        ('TROUVE', 'Trouvé'),
    ]
    
    STATUT_CHOICES = [
        ('SOUMIS', 'Soumis'),
        ('EN_COURS', 'En cours'),
        ('VALIDE', 'Validé'),
        ('REJETE', 'Rejeté'),
    ]
    
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='declarations'
    )
    objet = models.OneToOneField(
        Objet,
        on_delete=models.CASCADE,
        related_name='declaration'
    )
    type_declaration = models.CharField(
        max_length=10,
        choices=TYPE_DECLARATION_CHOICES
    )
    statut = models.CharField(
        max_length=10,
        choices=STATUT_CHOICES,
        default='SOUMIS',
        db_index=True
    )
    
    # Dates
    date_soumission = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    
    # Informations de validation
    commentaire_agent = models.TextField(blank=True)
    agent_validateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='declarations_validees',
        limit_choices_to={'role__in': ['agent', 'admin']}
    )
    
    class Meta:
        verbose_name = 'Déclaration'
        verbose_name_plural = 'Déclarations'
        ordering = ['-date_soumission']
        indexes = [
            models.Index(fields=['statut', '-date_soumission']),
            models.Index(fields=['type_declaration']),
        ]
    
    def __str__(self):
        return f"Déclaration {self.get_type_declaration_display()} - {self.objet.nom} par {self.utilisateur.username}"
    
    def clean(self):
        """Validation personnalisée."""
        super().clean()
        if self.statut in ['VALIDE', 'REJETE'] and not self.agent_validateur:
            raise ValidationError(
                "Un agent validateur est requis pour valider ou rejeter une déclaration."
            )


# ============================================================================
# 5. RECLAMATION
# ============================================================================
class Reclamation(models.Model):
    """
    Modèle pour gérer les réclamations d'objets trouvés.
    """
    STATUT_CHOICES = [
        ('EN_VERIFICATION', 'En vérification'),
        ('VALIDEE', 'Validée'),
        ('REFUSEE', 'Refusée'),
        ('RESTITUTION_PROGRAMMEE', 'Restitution programmée'),
    ]
    
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='reclamations'
    )
    objet = models.ForeignKey(
        Objet,
        on_delete=models.CASCADE,
        related_name='reclamations'
    )
    
    # Justification
    justificatif = models.FileField(
        upload_to='justificatifs/',
        help_text="Document justificatif (photo, facture, etc.)"
    )
    description_justificative = models.TextField(
        help_text="Description expliquant pourquoi l'objet vous appartient"
    )
    
    # Statut et dates
    statut = models.CharField(
        max_length=25,
        choices=STATUT_CHOICES,
        default='EN_VERIFICATION',
        db_index=True
    )
    date_reclamation = models.DateTimeField(auto_now_add=True)
    date_verification = models.DateTimeField(null=True, blank=True)
    
    # Vérification
    agent_verificateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reclamations_verifiees',
        limit_choices_to={'role__in': ['agent', 'admin']}
    )
    commentaire_verification = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Réclamation'
        verbose_name_plural = 'Réclamations'
        ordering = ['-date_reclamation']
        indexes = [
            models.Index(fields=['statut', '-date_reclamation']),
            models.Index(fields=['objet', 'statut']),
        ]
        permissions = [
            ("can_verify_reclamation", "Peut vérifier une réclamation"),
        ]
    
    def __str__(self):
        return f"Réclamation de {self.utilisateur.username} pour {self.objet.nom}"
    
    def peut_etre_validee(self):
        """
        Vérifie si la réclamation peut être validée.
        
        Returns:
            bool: True si la réclamation peut être validée
        """
        return (
            self.statut == 'EN_VERIFICATION' and
            self.objet.peut_etre_reclame() and
            self.justificatif and
            self.description_justificative
        )
    
    def clean(self):
        """Validation personnalisée."""
        super().clean()
        if not self.objet.peut_etre_reclame():
            raise ValidationError(
                "Cet objet ne peut pas être réclamé dans son état actuel."
            )


# ============================================================================
# 6. NOTIFICATION
# ============================================================================
class Notification(models.Model):
    """
    Modèle pour gérer les notifications envoyées aux utilisateurs.
    """
    TYPE_NOTIFICATION_CHOICES = [
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
        ('PUSH', 'Notification Push'),
        ('SYSTEME', 'Notification Système'),
    ]
    
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Contenu
    titre = models.CharField(max_length=200)
    message = models.TextField()
    
    # Type et statut
    type_notification = models.CharField(
        max_length=10,
        choices=TYPE_NOTIFICATION_CHOICES,
        default='SYSTEME'
    )
    lu = models.BooleanField(default=False, db_index=True)
    
    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_lecture = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['utilisateur', 'lu', '-date_creation']),
            models.Index(fields=['type_notification']),
        ]
    
    def __str__(self):
        return f"{self.titre} - {self.utilisateur.username} ({'Lu' if self.lu else 'Non lu'})"
    
    def marquer_comme_lu(self):
        """Marque la notification comme lue."""
        if not self.lu:
            self.lu = True
            self.date_lecture = timezone.now()
            self.save()


# ============================================================================
# MODÈLES DE COMPATIBILITÉ
# Ces modèles sont maintenus pour la compatibilité avec le code existant
# ============================================================================
class Signalement(models.Model):
    """
    Modèle de compatibilité pour les signalements existants.
    À terme, devrait être remplacé par le modèle Declaration.
    """
    TYPE_CHOICES = [
        ('perdu', 'Perdu'),
        ('trouve', 'Trouvé'),
        ('retourne', 'Retourné au propriétaire'),
    ]

    objet = models.ForeignKey(
        Objet,
        on_delete=models.CASCADE,
        related_name='signalements'
    )
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='signalements',
        null=True,
        blank=True
    )
    statut = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='perdu'
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    prefecture = models.ForeignKey(
        Prefecture,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    structure_locale = models.ForeignKey(
        StructureLocale,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    lieu = models.CharField(max_length=200, blank=True)
    commentaire = models.TextField(blank=True)
    photo = models.ImageField(upload_to='signalements/', blank=True, null=True)
    date_signalement = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Signalement (ancien)'
        verbose_name_plural = 'Signalements (anciens)'
        ordering = ['-date_signalement']

    def __str__(self):
        return f"{self.objet.nom} - {self.get_statut_display()}"


class ObjetPerdu(models.Model):
    """
    Modèle de compatibilité pour les anciens objets perdus.
    À terme, devrait être remplacé par le modèle Objet.
    """
    nom = models.CharField(max_length=100)
    lieu = models.CharField(max_length=100)
    date_perte = models.DateField()
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Objet perdu (ancien)'
        verbose_name_plural = 'Objets perdus (anciens)'

    def __str__(self):
        return f"{self.nom} - {self.lieu}"
