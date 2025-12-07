from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid


class Region(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Prefecture(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='prefectures')
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        unique_together = ('region', 'nom')
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} ({self.region.nom})"


class StructureLocale(models.Model):
    TYPE_CHOICES = [
        ('commissariat', 'Commissariat'),
        ('mairie', 'Mairie'),
        ('gendarmerie', 'Gendarmerie'),
        ('poste', 'Bureau de poste'),
        ('autre', 'Autre structure locale'),
    ]
    nom = models.CharField(max_length=150)
    type_structure = models.CharField(max_length=20, choices=TYPE_CHOICES)
    prefecture = models.ForeignKey(Prefecture, on_delete=models.CASCADE, related_name='structures_locales')
    adresse = models.TextField(blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} - {self.prefecture.nom}"


class Utilisateur(AbstractUser):
    """Utilisateur avec rôles et permissions étendues"""
    telephone = models.CharField(max_length=20, blank=True, null=True)
    
    ROLE_CHOICES = [
        ('citoyen', 'Citoyen'),
        ('agent', 'Agent'),
        ('admin', 'Administrateur'),
    ]
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default='citoyen')
    
    # Assignation géographique pour agents et admins
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, blank=True, null=True)
    prefecture = models.ForeignKey(Prefecture, on_delete=models.SET_NULL, blank=True, null=True)
    structure_locale = models.ForeignKey(StructureLocale, on_delete=models.SET_NULL, blank=True, null=True)
    
    # Métadonnées utilisateur
    date_derniere_connexion = models.DateTimeField(null=True, blank=True)
    actif = models.BooleanField(default=True)
    verifie = models.BooleanField(default=False, help_text="Compte vérifié par un admin")
    date_verification = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        permissions = [
            ("can_manage_declarations", "Peut gérer les déclarations"),
            ("can_validate_claims", "Peut valider les réclamations"),
            ("can_manage_users", "Peut gérer les utilisateurs"),
            ("can_view_analytics", "Peut voir les analytics"),
            ("can_manage_regions", "Peut gérer les régions"),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_agent_or_above(self):
        return self.role in ['agent', 'admin', 'superadmin']
    
    def is_admin_or_above(self):
        return self.role in ['admin', 'superadmin']


class CategorieObjet(models.Model):
    """Catégories d'objets pour classification"""
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icone = models.CharField(max_length=50, blank=True, help_text="Classe CSS FontAwesome")
    couleur = models.CharField(max_length=7, default="#3B82F6", help_text="Code couleur hexadécimal")
    actif = models.BooleanField(default=True)
    ordre = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['ordre', 'nom']
        verbose_name = "Catégorie d'objet"
        verbose_name_plural = "Catégories d'objets"
    
    def __str__(self):
        return self.nom


class Declaration(models.Model):
    """Déclaration d'objet perdu ou trouvé avec machine à états"""
    
    # États de la machine à états
    STATUT_CHOICES = [
        ('cree', 'Créé'),
        ('en_validation', 'En validation'),
        ('valide', 'Validé'),
        ('publie', 'Publié'),
        ('reclame', 'Réclamé'),
        ('en_verification', 'En vérification'),
        ('restitue', 'Restitué'),
        ('rejete', 'Rejeté'),
        ('archive', 'Archivé'),
    ]
    
    TYPE_CHOICES = [
        ('perdu', 'Objet perdu'),
        ('trouve', 'Objet trouvé'),
    ]
    
    # Identifiants
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    numero_declaration = models.CharField(max_length=20, unique=True, blank=True)
    
    # Informations de base
    type_declaration = models.CharField(max_length=10, choices=TYPE_CHOICES)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='cree')
    
    # Objet déclaré
    nom_objet = models.CharField(max_length=200)
    description = models.TextField()
    categorie = models.ForeignKey(CategorieObjet, on_delete=models.SET_NULL, null=True, blank=True)
    photo_principale = models.ImageField(upload_to='declarations/', blank=True, null=True)
    
    # Localisation
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    prefecture = models.ForeignKey(Prefecture, on_delete=models.SET_NULL, null=True, blank=True)
    structure_locale = models.ForeignKey(StructureLocale, on_delete=models.SET_NULL, null=True, blank=True)
    lieu_precis = models.CharField(max_length=300, help_text="Lieu précis de perte/découverte")
    
    # Dates
    date_incident = models.DateField(help_text="Date de perte ou de découverte")
    date_declaration = models.DateTimeField(auto_now_add=True)
    date_publication = models.DateTimeField(null=True, blank=True)
    date_restitution = models.DateTimeField(null=True, blank=True)
    
    # Relations utilisateurs
    declarant = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='mes_declarations')
    agent_validateur = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True, 
                                       related_name='declarations_validees', 
                                       limit_choices_to={'role__in': ['agent', 'admin', 'superadmin']})
    
    # Métadonnées
    commentaire_declarant = models.TextField(blank=True)
    commentaire_agent = models.TextField(blank=True, help_text="Commentaire interne de l'agent")
    priorite = models.IntegerField(default=1, choices=[(1, 'Normale'), (2, 'Haute'), (3, 'Urgente')])
    visible_publiquement = models.BooleanField(default=True)
    
    # Tracking
    nombre_vues = models.PositiveIntegerField(default=0)
    derniere_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_declaration']
        permissions = [
            ("can_validate_declaration", "Peut valider une déclaration"),
            ("can_publish_declaration", "Peut publier une déclaration"),
            ("can_archive_declaration", "Peut archiver une déclaration"),
        ]
    
    def save(self, *args, **kwargs):
        # Générer le numéro de déclaration automatiquement
        if not self.numero_declaration:
            from django.db import transaction
            import random
            import string
            
            with transaction.atomic():
                prefix = 'TGR' + str(timezone.now().year)[-2:]
                
                # Générer un numéro unique avec retry en cas de collision
                max_attempts = 10
                for attempt in range(max_attempts):
                    # Utiliser une approche plus robuste avec timestamp et random
                    timestamp_part = str(int(timezone.now().timestamp()))[-6:]
                    random_part = ''.join(random.choices(string.digits, k=2))
                    numero = f"{prefix}{timestamp_part}{random_part}"
                    
                    # Vérifier l'unicité
                    if not Declaration.objects.filter(numero_declaration=numero).exists():
                        self.numero_declaration = numero
                        break
                else:
                    # Si aucun numéro unique trouvé après max_attempts, utiliser UUID
                    import uuid
                    self.numero_declaration = f"{prefix}{str(uuid.uuid4())[:8].upper()}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.numero_declaration} - {self.nom_objet}"
    
    def peut_etre_valide(self):
        """Vérifie si la déclaration peut être validée"""
        return self.statut == 'cree'
    
    def peut_etre_publiee(self):
        """Vérifie si la déclaration peut être publiée"""
        return self.statut == 'valide'
    
    def peut_etre_reclamee(self):
        """Vérifie si la déclaration peut être réclamée"""
        return self.statut == 'publie'


class PhotoDeclaration(models.Model):
    """Photos supplémentaires pour une déclaration"""
    declaration = models.ForeignKey(Declaration, on_delete=models.CASCADE, related_name='photos_supplementaires')
    photo = models.ImageField(upload_to='declarations/photos/')
    legende = models.CharField(max_length=200, blank=True)
    ordre = models.PositiveIntegerField(default=0)
    date_ajout = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['ordre', 'date_ajout']
    
    def __str__(self):
        return f"Photo pour {self.declaration.numero_declaration}"


class Reclamation(models.Model):
    """Réclamations d'objets par des utilisateurs"""
    
    STATUT_CHOICES = [
        ('soumise', 'Soumise'),
        ('en_cours', 'En cours de vérification'),
        ('approuvee', 'Approuvée'),
        ('rejetee', 'Rejetée'),
        ('retiree', 'Retirée par le réclamant'),
    ]
    
    # Identifiants
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    numero_reclamation = models.CharField(max_length=20, unique=True, blank=True)
    
    # Relations
    declaration = models.ForeignKey(Declaration, on_delete=models.CASCADE, related_name='reclamations')
    reclamant = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='mes_reclamations')
    agent_traitant = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='reclamations_traitees',
                                     limit_choices_to={'role__in': ['agent', 'admin', 'superadmin']})
    
    # Informations de réclamation
    statut = models.CharField(max_length=15, choices=STATUT_CHOICES, default='soumise')
    justification = models.TextField(help_text="Pourquoi cet objet vous appartient-il ?")
    
    # Informations de contact
    telephone_contact = models.CharField(max_length=20, blank=True)
    email_contact = models.EmailField(blank=True)
    
    # Dates
    date_reclamation = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    date_retrait_prevue = models.DateTimeField(null=True, blank=True)
    
    # Commentaires et notes
    commentaire_reclamant = models.TextField(blank=True)
    commentaire_agent = models.TextField(blank=True, help_text="Commentaire interne de l'agent")
    motif_rejet = models.TextField(blank=True)
    
    # Métadonnées
    priorite = models.IntegerField(default=1, choices=[(1, 'Normale'), (2, 'Haute'), (3, 'Urgente')])
    derniere_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_reclamation']
        unique_together = ('declaration', 'reclamant')
    
    def save(self, *args, **kwargs):
        if not self.numero_reclamation:
            prefix = 'REC' + str(timezone.now().year)[-2:]
            last_num = Reclamation.objects.filter(
                numero_reclamation__startswith=prefix
            ).count() + 1
            self.numero_reclamation = f"{prefix}{last_num:06d}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.numero_reclamation} - {self.declaration.nom_objet}"


class PieceJustificative(models.Model):
    """Pièces justificatives pour les réclamations"""
    
    TYPE_CHOICES = [
        ('photo', 'Photo de l\'objet'),
        ('facture', 'Facture d\'achat'),
        ('garantie', 'Certificat de garantie'),
        ('identite', 'Pièce d\'identité'),
        ('autre', 'Autre document'),
    ]
    
    reclamation = models.ForeignKey(Reclamation, on_delete=models.CASCADE, related_name='pieces_justificatives')
    type_piece = models.CharField(max_length=10, choices=TYPE_CHOICES)
    fichier = models.FileField(upload_to='justificatifs/')
    nom_fichier = models.CharField(max_length=255)
    description = models.CharField(max_length=300, blank=True)
    taille_fichier = models.PositiveIntegerField(help_text="Taille en octets")
    date_ajout = models.DateTimeField(auto_now_add=True)
    verifie = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['type_piece', 'date_ajout']
    
    def __str__(self):
        return f"{self.get_type_piece_display()} - {self.reclamation.numero_reclamation}"


class Notification(models.Model):
    """Système de notifications pour les utilisateurs"""
    
    TYPE_CHOICES = [
        ('declaration_cree', 'Déclaration créée'),
        ('declaration_validee', 'Déclaration validée'),
        ('declaration_rejetee', 'Déclaration rejetée'),
        ('declaration_publiee', 'Déclaration publiée'),
        ('nouvelle_reclamation', 'Nouvelle réclamation'),
        ('reclamation_approuvee', 'Réclamation approuvée'),
        ('reclamation_rejetee', 'Réclamation rejetée'),
        ('objet_restitue', 'Objet restitué'),
        ('nouveau_message', 'Nouveau message'),
        ('rappel', 'Rappel'),
        ('systeme', 'Notification système'),
    ]
    
    # Relations
    destinataire = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='notifications')
    declaration = models.ForeignKey(Declaration, on_delete=models.CASCADE, null=True, blank=True)
    reclamation = models.ForeignKey(Reclamation, on_delete=models.CASCADE, null=True, blank=True)
    
    # Contenu
    type_notification = models.CharField(max_length=25, choices=TYPE_CHOICES)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    lien_action = models.URLField(blank=True, help_text="Lien vers l'action à effectuer")
    
    # Statut
    lue = models.BooleanField(default=False)
    importante = models.BooleanField(default=False)
    envoyee_par_email = models.BooleanField(default=False)
    date_envoi_email = models.DateTimeField(null=True, blank=True)
    
    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_lecture = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['destinataire', '-date_creation']),
            models.Index(fields=['lue', 'destinataire']),
        ]
    
    def __str__(self):
        return f"{self.titre} - {self.destinataire.username}"
    
    def marquer_comme_lue(self):
        if not self.lue:
            self.lue = True
            self.date_lecture = timezone.now()
            self.save(update_fields=['lue', 'date_lecture'])


class ActionLog(models.Model):
    """Log des actions pour audit et suivi"""
    
    ACTION_CHOICES = [
        # Actions sur déclarations
        ('declaration_creee', 'Déclaration créée'),
        ('declaration_validee', 'Déclaration validée'),
        ('declaration_rejetee', 'Déclaration rejetée'),
        ('declaration_publiee', 'Déclaration publiée'),
        ('declaration_archivee', 'Déclaration archivée'),
        
        # Actions sur réclamations
        ('reclamation_soumise', 'Réclamation soumise'),
        ('reclamation_approuvee', 'Réclamation approuvée'),
        ('reclamation_rejetee', 'Réclamation rejetée'),
        ('objet_restitue', 'Objet restitué'),
        
        # Actions administratives
        ('utilisateur_cree', 'Utilisateur créé'),
        ('utilisateur_modifie', 'Utilisateur modifié'),
        ('role_modifie', 'Rôle utilisateur modifié'),
        ('region_assignee', 'Région assignée'),
        
        # Actions système
        ('connexion', 'Connexion'),
        ('deconnexion', 'Déconnexion'),
        ('erreur', 'Erreur système'),
    ]
    
    # Relations
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True)
    declaration = models.ForeignKey(Declaration, on_delete=models.CASCADE, null=True, blank=True)
    reclamation = models.ForeignKey(Reclamation, on_delete=models.CASCADE, null=True, blank=True)
    
    # Informations de l'action
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Métadonnées
    donnees_supplementaires = models.JSONField(default=dict, blank=True)
    date_action = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_action']
        indexes = [
            models.Index(fields=['utilisateur', '-date_action']),
            models.Index(fields=['action', '-date_action']),
            models.Index(fields=['declaration', '-date_action']),
        ]
    
    def __str__(self):
        user_info = f"par {self.utilisateur.username}" if self.utilisateur else "par système"
        return f"{self.get_action_display()} {user_info} - {self.date_action.strftime('%d/%m/%Y %H:%M')}"


class StatistiqueRegion(models.Model):
    """Statistiques pré-calculées par région pour optimiser les dashboards"""
    region = models.OneToOneField(Region, on_delete=models.CASCADE, related_name='statistiques')
    
    # Compteurs de déclarations
    total_declarations = models.PositiveIntegerField(default=0)
    declarations_en_attente = models.PositiveIntegerField(default=0)
    declarations_publiees = models.PositiveIntegerField(default=0)
    objets_restitues = models.PositiveIntegerField(default=0)
    
    # Compteurs de réclamations
    total_reclamations = models.PositiveIntegerField(default=0)
    reclamations_en_cours = models.PositiveIntegerField(default=0)
    reclamations_approuvees = models.PositiveIntegerField(default=0)
    reclamations_rejetees = models.PositiveIntegerField(default=0)
    
    # Métriques de performance
    temps_moyen_traitement_heures = models.FloatField(default=0.0)
    taux_restitution = models.FloatField(default=0.0)
    
    # Dates de mise à jour
    derniere_mise_a_jour = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Statistique région"
        verbose_name_plural = "Statistiques régions"
    
    def __str__(self):
        return f"Stats {self.region.nom}"
    
    def calculer_taux_restitution(self):
        """Calcule le taux de restitution en pourcentage"""
        if self.declarations_publiees > 0:
            return (self.objets_restitues / self.declarations_publiees) * 100
        return 0.0


# ============ MODÈLES DE COMPATIBILITÉ ============
# Ces modèles restent pour la compatibilité avec les vues existantes

class Objet(models.Model):
    """Modèle de compatibilité - redirige vers Declaration"""
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    categorie = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to='objets/', blank=True, null=True)
    lieu_trouve = models.CharField(max_length=200, blank=True)
    date_trouve = models.DateField(blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom


class ObjetPerdu(models.Model):
    """Modèle de compatibilité"""
    nom = models.CharField(max_length=100)
    lieu = models.CharField(max_length=100)
    date_perte = models.DateField()
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nom} - {self.lieu}"


class Signalement(models.Model):
    """Modèle de compatibilité - redirige vers Declaration"""
    TYPE_CHOICES = [
        ('perdu', 'Perdu'),
        ('trouve', 'Trouvé'),
        ('retourne', 'Retourné au propriétaire'),
    ]

    objet = models.ForeignKey(Objet, on_delete=models.CASCADE, related_name='signalements', null=True, blank=True)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='signalements', null=True, blank=True)
    statut = models.CharField(max_length=20, choices=TYPE_CHOICES, default='perdu')
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    prefecture = models.ForeignKey(Prefecture, on_delete=models.SET_NULL, null=True, blank=True)
    structure_locale = models.ForeignKey(StructureLocale, on_delete=models.SET_NULL, null=True, blank=True)
    lieu = models.CharField(max_length=200, blank=True)
    commentaire = models.TextField(blank=True)
    photo = models.ImageField(upload_to='signalements/', blank=True, null=True)
    date_signalement = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.objet.nom if self.objet else 'Objet inconnu'} - {self.get_statut_display()}"


class CommentaireAnonyme(models.Model):
    """Commentaires anonymes sur les signalements et déclarations"""
    signalement = models.ForeignKey(Signalement, on_delete=models.CASCADE, related_name='commentaires_anonymes', null=True, blank=True)
    declaration = models.ForeignKey(Declaration, on_delete=models.CASCADE, related_name='commentaires_anonymes', null=True, blank=True)
    contenu = models.TextField(max_length=1000, help_text="Votre commentaire (max 1000 caractères)")
    pseudo = models.CharField(max_length=50, blank=True, help_text="Pseudo optionnel (ou laissez vide pour 'Anonyme')")
    email = models.EmailField(blank=True, help_text="Email optionnel (ne sera pas affiché publiquement)")
    date_creation = models.DateTimeField(auto_now_add=True)
    est_approuve = models.BooleanField(default=True, help_text="Commentaire approuvé pour affichage")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Commentaire anonyme"
        verbose_name_plural = "Commentaires anonymes"
    
    def __str__(self):
        pseudo = self.pseudo or "Anonyme"
        objet = "déclaration"
        if self.signalement and self.signalement.objet:
            objet = self.signalement.objet.nom
        elif self.declaration:
            objet = self.declaration.nom_objet
        return f"Commentaire de {pseudo} sur {objet}"
    
    def get_display_name(self):
        """Retourne le nom d'affichage (pseudo ou 'Anonyme')"""
        return self.pseudo or "Anonyme"


# ===== MODÈLES DE MESSAGERIE TEMPS RÉEL =====

class Conversation(models.Model):
    """
    Conversation privée entre un agent et un déclarant pour un signalement spécifique
    """
    signalement = models.ForeignKey(
        Declaration, 
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='conversations',
        help_text="Signalement concerné par cette conversation"
    )
    agent = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        limit_choices_to={'role__in': ['agent', 'admin']},
        related_name='conversations_agent',
        help_text="Agent participant à la conversation"
    )
    declarant = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        limit_choices_to={'role': 'citoyen'},
        related_name='conversations_declarant',
        help_text="Déclarant participant à la conversation"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'core_conversation_chat'
        unique_together = ['signalement', 'agent', 'declarant']
        ordering = ['-updated_at']
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
    
    def __str__(self):
        return f"Conversation {self.agent.get_full_name()} ↔ {self.declarant.get_full_name()} - {self.signalement.numero_declaration}"
    
    @property
    def unread_count_for_agent(self):
        """Nombre de messages non lus par l'agent"""
        return self.messages.filter(sender=self.declarant, is_read=False).count()
    
    @property
    def unread_count_for_declarant(self):
        """Nombre de messages non lus par le déclarant"""
        return self.messages.filter(sender=self.agent, is_read=False).count()
    
    @property
    def dernier_message(self):
        """Retourne le dernier message de la conversation"""
        return self.messages.order_by('-created_at').first()
        return self.messages.filter(sender=self.agent, is_read=False).count()
    
    def get_last_message(self):
        """Retourne le dernier message de la conversation"""
        return self.messages.order_by('-created_at').first()


class Message(models.Model):
    """
    Message dans une conversation entre agent et déclarant
    """
    TYPE_CHOICES = [
        ('texte', 'Message texte'),
        ('fichier', 'Fichier joint'),
        ('systeme', 'Message système'),
    ]
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text="Conversation à laquelle appartient ce message"
    )
    sender = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='messages_sent',
        help_text="Expéditeur du message"
    )
    receiver = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='messages_received',
        help_text="Destinataire du message"
    )
    contenu = models.TextField(
        max_length=2000,
        blank=True,
        help_text="Contenu du message (max 2000 caractères)"
    )
    fichier = models.FileField(
        upload_to='chat_files/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Fichier joint (image, PDF, etc.)"
    )
    type_message = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default='texte',
        help_text="Type de message"
    )
    is_read = models.BooleanField(
        default=False,
        help_text="Message lu par le destinataire"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date de lecture du message"
    )
    
    class Meta:
        db_table = 'core_message_chat'
        ordering = ['created_at']
        verbose_name = "Message"
        verbose_name_plural = "Messages"
    
    def __str__(self):
        if self.type_message == 'fichier':
            return f"📎 Fichier de {self.sender.get_full_name()} à {self.receiver.get_full_name()}"
        elif self.type_message == 'systeme':
            return f"🤖 Message système: {self.contenu[:50]}..."
        else:
            return f"💬 {self.sender.get_full_name()} → {self.receiver.get_full_name()}: {self.contenu[:50]}..."
    
    def mark_as_read(self):
        """Marque le message comme lu"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    @property
    def file_name(self):
        """Retourne le nom du fichier si présent"""
        if self.fichier:
            return self.fichier.name.split('/')[-1]
        return None
    
    @property
    def file_size(self):
        """Retourne la taille du fichier en bytes"""
        if self.fichier:
            try:
                return self.fichier.size
            except:
                return 0
        return 0
    
    @property
    def is_image(self):
        """Vérifie si le fichier est une image"""
        if self.fichier:
            try:
                name = self.fichier.name.lower()
                return name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'))
            except:
                return False
        return False