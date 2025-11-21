from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Utilisateur, Region, Prefecture, StructureLocale,
    Localisation, Objet, Declaration, Reclamation, Notification,
    Signalement, ObjetPerdu
)


# ============================================================================
# Admin pour Utilisateur (Custom User)
# ============================================================================
@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    """Administration personnalisée pour le modèle Utilisateur."""
    list_display = ('username', 'email', 'nom', 'prenom', 'role', 'region', 'is_active')
    list_filter = ('role', 'region', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'nom', 'prenom', 'telephone')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Informations personnelles', {
            'fields': ('nom', 'prenom', 'telephone', 'adresse')
        }),
        ('Localisation', {
            'fields': ('region', 'prefecture')
        }),
        ('Rôle et permissions', {
            'fields': ('role',)
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('nom', 'prenom', 'email', 'telephone', 'role', 'region', 'prefecture')
        }),
    )


# ============================================================================
# Admin pour les modèles de localisation
# ============================================================================
@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    """Administration pour les régions."""
    list_display = ('nom',)
    search_fields = ('nom',)


@admin.register(Prefecture)
class PrefectureAdmin(admin.ModelAdmin):
    """Administration pour les préfectures."""
    list_display = ('nom', 'region')
    list_filter = ('region',)
    search_fields = ('nom', 'region__nom')


@admin.register(StructureLocale)
class StructureLocaleAdmin(admin.ModelAdmin):
    """Administration pour les structures locales."""
    list_display = ('nom', 'type_structure', 'prefecture')
    list_filter = ('type_structure', 'prefecture__region')
    search_fields = ('nom', 'prefecture__nom')


@admin.register(Localisation)
class LocalisationAdmin(admin.ModelAdmin):
    """Administration pour les localisations."""
    list_display = ('quartier', 'prefecture', 'region', 'commissariat', 'latitude', 'longitude')
    list_filter = ('region', 'prefecture')
    search_fields = ('region', 'prefecture', 'quartier', 'commissariat')
    
    fieldsets = (
        ('Localisation administrative', {
            'fields': ('region', 'prefecture', 'quartier', 'commissariat')
        }),
        ('Coordonnées GPS', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
    )


# ============================================================================
# Admin pour Objet
# ============================================================================
@admin.register(Objet)
class ObjetAdmin(admin.ModelAdmin):
    """Administration pour les objets perdus/trouvés."""
    list_display = ('nom', 'typeObjet', 'etat', 'est_perdu', 'proprietaire', 'agent_responsable', 'dateDeclaration')
    list_filter = ('etat', 'est_perdu', 'typeObjet', 'dateDeclaration')
    search_fields = ('nom', 'description', 'couleur', 'marque')
    date_hierarchy = 'dateDeclaration'
    readonly_fields = ('dateDeclaration',)
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('typeObjet', 'nom', 'description', 'couleur', 'marque', 'photo')
        }),
        ('Localisation et dates', {
            'fields': ('lieuPerte', 'datePerte', 'dateDeclaration')
        }),
        ('Personnes impliquées', {
            'fields': ('proprietaire', 'agent_responsable')
        }),
        ('État et type', {
            'fields': ('etat', 'est_perdu')
        }),
    )
    
    actions = ['marquer_en_validation', 'marquer_valide', 'marquer_publie']
    
    def marquer_en_validation(self, request, queryset):
        for objet in queryset:
            try:
                objet.change_etat('EN_VALIDATION', request.user)
                self.message_user(request, f"{objet.nom} marqué en validation.")
            except ValidationError as e:
                self.message_user(request, f"Erreur pour {objet.nom}: {e}", level='error')
    marquer_en_validation.short_description = "Marquer en validation"
    
    def marquer_valide(self, request, queryset):
        for objet in queryset:
            try:
                objet.change_etat('VALIDE', request.user)
                self.message_user(request, f"{objet.nom} marqué validé.")
            except ValidationError as e:
                self.message_user(request, f"Erreur pour {objet.nom}: {e}", level='error')
    marquer_valide.short_description = "Marquer validé"
    
    def marquer_publie(self, request, queryset):
        for objet in queryset:
            try:
                objet.change_etat('PUBLIE', request.user)
                self.message_user(request, f"{objet.nom} marqué publié.")
            except ValidationError as e:
                self.message_user(request, f"Erreur pour {objet.nom}: {e}", level='error')
    marquer_publie.short_description = "Marquer publié"


# ============================================================================
# Admin pour Declaration
# ============================================================================
@admin.register(Declaration)
class DeclarationAdmin(admin.ModelAdmin):
    """Administration pour les déclarations."""
    list_display = ('objet', 'utilisateur', 'type_declaration', 'statut', 'date_soumission', 'agent_validateur')
    list_filter = ('statut', 'type_declaration', 'date_soumission')
    search_fields = ('objet__nom', 'utilisateur__username', 'commentaire_agent')
    date_hierarchy = 'date_soumission'
    readonly_fields = ('date_soumission',)
    
    fieldsets = (
        ('Déclaration', {
            'fields': ('utilisateur', 'objet', 'type_declaration', 'statut')
        }),
        ('Dates', {
            'fields': ('date_soumission', 'date_validation')
        }),
        ('Validation agent', {
            'fields': ('agent_validateur', 'commentaire_agent')
        }),
    )


# ============================================================================
# Admin pour Reclamation
# ============================================================================
@admin.register(Reclamation)
class ReclamationAdmin(admin.ModelAdmin):
    """Administration pour les réclamations."""
    list_display = ('objet', 'utilisateur', 'statut', 'date_reclamation', 'agent_verificateur')
    list_filter = ('statut', 'date_reclamation')
    search_fields = ('objet__nom', 'utilisateur__username', 'description_justificative')
    date_hierarchy = 'date_reclamation'
    readonly_fields = ('date_reclamation',)
    
    fieldsets = (
        ('Réclamation', {
            'fields': ('utilisateur', 'objet', 'statut')
        }),
        ('Justification', {
            'fields': ('justificatif', 'description_justificative')
        }),
        ('Dates', {
            'fields': ('date_reclamation', 'date_verification')
        }),
        ('Vérification agent', {
            'fields': ('agent_verificateur', 'commentaire_verification')
        }),
    )
    
    actions = ['valider_reclamation', 'refuser_reclamation']
    
    def valider_reclamation(self, request, queryset):
        count = queryset.filter(statut='EN_VERIFICATION').update(
            statut='VALIDEE',
            agent_verificateur=request.user,
            date_verification=timezone.now()
        )
        self.message_user(request, f"{count} réclamation(s) validée(s).")
    valider_reclamation.short_description = "Valider la réclamation"
    
    def refuser_reclamation(self, request, queryset):
        count = queryset.filter(statut='EN_VERIFICATION').update(
            statut='REFUSEE',
            agent_verificateur=request.user,
            date_verification=timezone.now()
        )
        self.message_user(request, f"{count} réclamation(s) refusée(s).")
    refuser_reclamation.short_description = "Refuser la réclamation"


# ============================================================================
# Admin pour Notification
# ============================================================================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Administration pour les notifications."""
    list_display = ('titre', 'utilisateur', 'type_notification', 'lu', 'date_creation')
    list_filter = ('type_notification', 'lu', 'date_creation')
    search_fields = ('titre', 'message', 'utilisateur__username')
    date_hierarchy = 'date_creation'
    readonly_fields = ('date_creation', 'date_lecture')
    
    fieldsets = (
        ('Notification', {
            'fields': ('utilisateur', 'titre', 'message', 'type_notification')
        }),
        ('État', {
            'fields': ('lu', 'date_creation', 'date_lecture')
        }),
    )
    
    actions = ['marquer_comme_lu']
    
    def marquer_comme_lu(self, request, queryset):
        for notif in queryset:
            notif.marquer_comme_lu()
        self.message_user(request, f"{queryset.count()} notification(s) marquée(s) comme lue(s).")
    marquer_comme_lu.short_description = "Marquer comme lu"


# ============================================================================
# Admin pour les modèles de compatibilité
# ============================================================================
@admin.register(Signalement)
class SignalementAdmin(admin.ModelAdmin):
    """Administration pour les signalements (ancien modèle)."""
    list_display = ('objet', 'utilisateur', 'statut', 'date_signalement')
    list_filter = ('statut', 'date_signalement')
    search_fields = ('objet__nom', 'utilisateur__username', 'lieu')


@admin.register(ObjetPerdu)
class ObjetPerduAdmin(admin.ModelAdmin):
    """Administration pour les objets perdus (ancien modèle)."""
    list_display = ('nom', 'lieu', 'date_perte')
    list_filter = ('date_perte',)
    search_fields = ('nom', 'lieu', 'description')
