from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.db.models import Q, Count, Avg
from .models import Notification, ActionLog
import logging

logger = logging.getLogger(__name__)


def create_notification(destinataire, type_notification, titre, message, declaration=None, reclamation=None, importante=False, envoyer_email=False):
    """
    Créer une notification pour un utilisateur
    
    Args:
        destinataire: Utilisateur destinataire
        type_notification: Type de notification (voir Notification.TYPE_CHOICES)
        titre: Titre de la notification
        message: Message détaillé
        declaration: Déclaration liée (optionnel)
        reclamation: Réclamation liée (optionnel)
        importante: Si la notification est importante
        envoyer_email: Si un email doit être envoyé
    
    Returns:
        Notification créée
    """
    try:
        # Générer le lien d'action selon le contexte
        lien_action = ""
        if declaration:
            if type_notification == 'declaration_publiee':
                lien_action = reverse('declaration_detail', kwargs={'id': declaration.id})
            elif type_notification in ['declaration_validee', 'declaration_rejetee']:
                lien_action = reverse('utilisateur:mes_declarations')
        elif reclamation:
            if type_notification in ['reclamation_approuvee', 'reclamation_rejetee']:
                lien_action = reverse('utilisateur:mes_reclamations')
        
        # Créer la notification
        notification = Notification.objects.create(
            destinataire=destinataire,
            declaration=declaration,
            reclamation=reclamation,
            type_notification=type_notification,
            titre=titre,
            message=message,
            lien_action=lien_action,
            importante=importante
        )
        
        # Envoyer l'email si demandé
        if envoyer_email and destinataire.email:
            send_notification_email(notification)
        
        return notification
        
    except Exception as e:
        logger.error(f"Erreur lors de la création de notification : {str(e)}")
        return None


def send_notification_email(notification):
    """
    Envoyer un email pour une notification
    
    Args:
        notification: Instance de Notification
    """
    try:
        if not notification.destinataire.email:
            return False
        
        # Contexte pour le template email
        context = {
            'notification': notification,
            'user': notification.destinataire,
            'site_name': 'TogoRetrouve',
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        }
        
        # Rendu du template email
        html_content = render_to_string('emails/notification.html', context)
        text_content = render_to_string('emails/notification.txt', context)
        
        # Envoi de l'email
        sent = send_mail(
            subject=f"[TogoRetrouve] {notification.titre}",
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.destinataire.email],
            html_message=html_content,
            fail_silently=False
        )
        
        if sent:
            notification.envoyee_par_email = True
            notification.date_envoi_email = timezone.now()
            notification.save(update_fields=['envoyee_par_email', 'date_envoi_email'])
        
        return sent
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi d'email de notification : {str(e)}")
        return False


def log_action(user, action, description, declaration=None, reclamation=None, ip_address=None, user_agent=None, donnees_supplementaires=None):
    """
    Enregistrer une action dans les logs
    
    Args:
        user: Utilisateur qui effectue l'action (peut être None pour les actions système)
        action: Type d'action (voir ActionLog.ACTION_CHOICES)
        description: Description de l'action
        declaration: Déclaration liée (optionnel)
        reclamation: Réclamation liée (optionnel)
        ip_address: Adresse IP (optionnel)
        user_agent: User Agent (optionnel)
        donnees_supplementaires: Données supplémentaires au format dict (optionnel)
    
    Returns:
        ActionLog créée
    """
    try:
        log_entry = ActionLog.objects.create(
            utilisateur=user,
            declaration=declaration,
            reclamation=reclamation,
            action=action,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            donnees_supplementaires=donnees_supplementaires or {}
        )
        
        # Log dans le système de logging Python aussi
        logger.info(f"Action logged: {action} by {user.username if user else 'system'} - {description}")
        
        return log_entry
        
    except Exception as e:
        logger.error(f"Erreur lors du logging d'action : {str(e)}")
        return None


def get_user_ip(request):
    """
    Obtenir l'adresse IP de l'utilisateur depuis la requête
    
    Args:
        request: HttpRequest
        
    Returns:
        str: Adresse IP
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """
    Obtenir le User Agent de l'utilisateur depuis la requête
    
    Args:
        request: HttpRequest
        
    Returns:
        str: User Agent
    """
    return request.META.get('HTTP_USER_AGENT', '')


def create_notification_for_new_declaration(declaration):
    """
    Créer des notifications pour une nouvelle déclaration
    """
    # Notification pour les agents de la région
    from .models import Utilisateur
    
    agents = Utilisateur.objects.filter(
        role__in=['agent', 'admin', 'superadmin'],
        region=declaration.region,
        actif=True
    )
    
    for agent in agents:
        create_notification(
            destinataire=agent,
            type_notification='declaration_cree',
            titre=f"Nouvelle déclaration : {declaration.numero_declaration}",
            message=f"Une nouvelle déclaration '{declaration.nom_objet}' a été soumise et nécessite une validation.",
            declaration=declaration,
            importante=True
        )


def create_notification_for_new_reclamation(reclamation):
    """
    Créer des notifications pour une nouvelle réclamation
    """
    # Notification pour les agents de la région
    from .models import Utilisateur
    
    agents = Utilisateur.objects.filter(
        role__in=['agent', 'admin', 'superadmin'],
        region=reclamation.declaration.region,
        actif=True
    )
    
    for agent in agents:
        create_notification(
            destinataire=agent,
            type_notification='nouvelle_reclamation',
            titre=f"Nouvelle réclamation : {reclamation.numero_reclamation}",
            message=f"Une nouvelle réclamation a été soumise pour l'objet '{reclamation.declaration.nom_objet}'.",
            reclamation=reclamation,
            importante=True
        )


def update_region_statistics(region):
    """
    Mettre à jour les statistiques d'une région
    
    Args:
        region: Instance de Region
    """
    try:
        from django.db.models import Count, Avg
        from .models import Declaration, Reclamation, StatistiqueRegion
        
        # Obtenir ou créer les statistiques
        stats, created = StatistiqueRegion.objects.get_or_create(region=region)
        
        # Calculer les statistiques de déclarations
        declaration_stats = Declaration.objects.filter(region=region).aggregate(
            total=Count('id'),
            en_attente=Count('id', filter=Q(statut='cree')),
            publiees=Count('id', filter=Q(statut='publie')),
            restituees=Count('id', filter=Q(statut='restitue'))
        )
        
        # Calculer les statistiques de réclamations
        reclamation_stats = Reclamation.objects.filter(declaration__region=region).aggregate(
            total=Count('id'),
            en_cours=Count('id', filter=Q(statut__in=['soumise', 'en_cours'])),
            approuvees=Count('id', filter=Q(statut='approuvee')),
            rejetees=Count('id', filter=Q(statut='rejetee'))
        )
        
        # Mettre à jour les statistiques
        stats.total_declarations = declaration_stats['total'] or 0
        stats.declarations_en_attente = declaration_stats['en_attente'] or 0
        stats.declarations_publiees = declaration_stats['publiees'] or 0
        stats.objets_restitues = declaration_stats['restituees'] or 0
        
        stats.total_reclamations = reclamation_stats['total'] or 0
        stats.reclamations_en_cours = reclamation_stats['en_cours'] or 0
        stats.reclamations_approuvees = reclamation_stats['approuvees'] or 0
        stats.reclamations_rejetees = reclamation_stats['rejetees'] or 0
        
        # Calculer le taux de restitution
        if stats.declarations_publiees > 0:
            stats.taux_restitution = (stats.objets_restitues / stats.declarations_publiees) * 100
        else:
            stats.taux_restitution = 0.0
        
        stats.save()
        
        return stats
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des statistiques : {str(e)}")
        return None


def clean_old_notifications():
    """
    Nettoyer les anciennes notifications (plus de 6 mois)
    Cette fonction devrait être appelée périodiquement par une tâche cron
    """
    try:
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=180)  # 6 mois
        
        deleted_count = Notification.objects.filter(
            date_creation__lt=cutoff_date,
            lue=True
        ).delete()[0]
        
        logger.info(f"Nettoyage des notifications : {deleted_count} notifications supprimées")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des notifications : {str(e)}")
        return 0


def clean_old_action_logs():
    """
    Nettoyer les anciens logs d'action (plus de 1 an)
    Cette fonction devrait être appelée périodiquement par une tâche cron
    """
    try:
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=365)  # 1 an
        
        deleted_count = ActionLog.objects.filter(
            date_action__lt=cutoff_date
        ).exclude(
            action__in=['erreur', 'connexion']  # Garder certains logs plus longtemps
        ).delete()[0]
        
        logger.info(f"Nettoyage des logs : {deleted_count} logs supprimés")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des logs : {str(e)}")
        return 0


def validate_state_transition(declaration, new_status, user):
    """
    Valider une transition d'état pour une déclaration
    
    Args:
        declaration: Instance de Declaration
        new_status: Nouveau statut désiré
        user: Utilisateur qui tente la transition
        
    Returns:
        tuple: (is_valid, error_message)
    """
    current_status = declaration.statut
    
    # Règles de transition
    allowed_transitions = {
        'cree': ['valide', 'rejete'],
        'valide': ['publie', 'rejete'],
        'publie': ['reclame', 'archive'],
        'reclame': ['en_verification'],
        'en_verification': ['restitue', 'publie'],  # Retour en publication si réclamation rejetée
        'restitue': ['archive'],
        'rejete': [],  # Pas de transition depuis rejeté
        'archive': []  # Pas de transition depuis archivé
    }
    
    # Vérifier si la transition est autorisée
    if new_status not in allowed_transitions.get(current_status, []):
        return False, f"Transition de '{current_status}' vers '{new_status}' non autorisée"
    
    # Vérifier les permissions utilisateur
    if not user.is_agent_or_above():
        return False, "Permissions insuffisantes pour cette transition"
    
    if user.role == 'agent' and new_status in ['archive']:
        return False, "Seuls les admins peuvent archiver des déclarations"
    
    return True, "Transition autorisée"


def send_weekly_digest_to_agents():
    """
    Envoyer un digest hebdomadaire aux agents
    Cette fonction devrait être appelée chaque semaine par une tâche cron
    """
    try:
        from datetime import timedelta
        from django.db.models import Q
        from .models import Utilisateur, Declaration, Reclamation
        
        # Période : dernière semaine
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)
        
        agents = Utilisateur.objects.filter(
            role__in=['agent', 'admin'],
            actif=True,
            email__isnull=False
        ).exclude(email='')
        
        for agent in agents:
            # Statistiques de la semaine pour l'agent
            region_filter = Q()
            if agent.region:
                region_filter = Q(region=agent.region)
            elif agent.prefecture:
                region_filter = Q(prefecture=agent.prefecture)
            
            stats = {
                'nouvelles_declarations': Declaration.objects.filter(
                    region_filter & Q(date_declaration__range=[start_date, end_date])
                ).count(),
                'declarations_validees': Declaration.objects.filter(
                    region_filter & Q(
                        agent_validateur=agent,
                        date_publication__range=[start_date, end_date]
                    )
                ).count(),
                'nouvelles_reclamations': Reclamation.objects.filter(
                    declaration__region=agent.region if agent.region else None,
                    date_reclamation__range=[start_date, end_date]
                ).count(),
                'reclamations_traitees': Reclamation.objects.filter(
                    agent_traitant=agent,
                    date_traitement__range=[start_date, end_date]
                ).count(),
            }
            
            # Envoyer l'email de digest si il y a de l'activité
            if any(stats.values()):
                context = {
                    'agent': agent,
                    'stats': stats,
                    'periode': f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
                    'site_name': 'TogoRetrouve',
                    'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
                }
                
                html_content = render_to_string('emails/weekly_digest.html', context)
                text_content = render_to_string('emails/weekly_digest.txt', context)
                
                send_mail(
                    subject=f"[TogoRetrouve] Rapport hebdomadaire - {agent.region.nom if agent.region else 'Global'}",
                    message=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[agent.email],
                    html_message=html_content,
                    fail_silently=True
                )
        
        logger.info("Digest hebdomadaire envoyé aux agents")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du digest hebdomadaire : {str(e)}")