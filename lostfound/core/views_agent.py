from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Max
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
import json
from datetime import datetime, timedelta

from .models import (
    Declaration, Reclamation, Conversation, Message, PieceJustificative, 
    Notification, ActionLog, CommentaireAnonyme, Utilisateur
)
from .decorators import role_required
# Les formulaires spécifiques aux agents seront ajoutés plus tard si nécessaire


@login_required
@role_required(['agent'])
def agent_dashboard(request):
    """
    Dashboard principal de l'agent
    Affiche les statistiques et données filtrées par sa zone de compétence
    """
    user = request.user
    
    # Filtrage strict par structure locale uniquement
    if not user.structure_locale:
        messages.error(request, "Aucune structure locale assignée. Contactez votre administrateur.")
        return redirect('logout')
    
    base_filter = {'structure_locale': user.structure_locale}
    
    # Statistiques principales
    stats = {
        'total_signalements': Declaration.objects.filter(**base_filter).count(),
        'objets_retrouves': Declaration.objects.filter(
            **base_filter, 
            type_declaration='trouve', 
            agent_validateur=user
        ).count(),
        'objets_restitues': Declaration.objects.filter(
            **base_filter, 
            statut='restitue'
        ).count(),
        'demandes_attente': Reclamation.objects.filter(
            declaration__in=Declaration.objects.filter(**base_filter),
            statut='soumise'
        ).count(),
    }
    
    # Signalements récents nécessitant une action
    signalements_en_attente = Declaration.objects.filter(
        **base_filter,
        statut__in=['cree', 'en_validation']
    ).order_by('-date_declaration')[:5]
    
    # Réclamations en attente de vérification
    reclamations_en_attente = Reclamation.objects.filter(
        declaration__in=Declaration.objects.filter(**base_filter),
        statut='soumise'
    ).select_related('declaration', 'reclamant').order_by('-date_reclamation')[:5]
    
    # Messages non lus
    conversations_actives = Conversation.objects.filter(
        agent=user
    ).annotate(
        messages_non_lus=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=user))
    ).order_by('-updated_at')[:5]
    
    # Activité récente
    activites_recentes = ActionLog.objects.filter(
        utilisateur=user
    ).select_related('declaration', 'reclamation').order_by('-date_action')[:10]
    
    context = {
        'stats': stats,
        'signalements_en_attente': signalements_en_attente,
        'reclamations_en_attente': reclamations_en_attente,
        'conversations_actives': conversations_actives,
        'activites_recentes': activites_recentes,
        'agent': user,
    }
    
    return render(request, 'agent/dashboard.html', context)


@login_required
@role_required(['agent'])
def agent_chat_dashboard(request):
    """
    Dashboard agent avec focus sur le chat intégré
    Identique au dashboard principal mais optimisé pour le chat
    """
    user = request.user
    
    # Paramètres pour ouvrir une conversation spécifique
    conversation_id = request.GET.get('conversation_id')
    reclamation_id = request.GET.get('reclamation_id')
    signalement_id = request.GET.get('signalement_id')
    declarant_id = request.GET.get('declarant_id')
    
    # Filtrage strict par structure locale uniquement
    if not user.structure_locale:
        messages.error(request, "Aucune structure locale assignée. Contactez votre administrateur.")
        return redirect('togo_agent:dashboard')

    base_filter = {'structure_locale': user.structure_locale}
    
    # Statistiques de base
    stats = {
        'total_signalements': Declaration.objects.filter(**base_filter).count(),
        'signalements_en_attente': Declaration.objects.filter(**base_filter, statut='cree').count(),
        'signalements_valides': Declaration.objects.filter(**base_filter, statut='valide').count(),
        'objets_restitues': Declaration.objects.filter(**base_filter, statut='restitue').count(),
    }
    
    # Signalements récents pour contexte
    signalements_en_attente = Declaration.objects.filter(
        **base_filter, statut='cree'
    ).select_related('declarant', 'categorie').order_by('-date_declaration')[:5]
    
    # Réclamations en attente
    reclamations_en_attente = Reclamation.objects.filter(
        declaration__structure_locale=user.structure_locale,
        statut='en_attente'
    ).select_related('declaration', 'reclamant').order_by('-date_reclamation')[:5]
    
    # Conversations de chat
    conversations_actives = Conversation.objects.filter(
        agent=user
    ).annotate(
        messages_non_lus=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=user))
    ).order_by('-updated_at')[:5]
    
    # Conversation sélectionnée
    selected_conversation = None
    if conversation_id:
        try:
            selected_conversation = Conversation.objects.get(
                id=conversation_id,
                agent=user
            )
        except Conversation.DoesNotExist:
            messages.error(request, 'Conversation introuvable')
    elif reclamation_id:
        try:
            reclamation = Reclamation.objects.get(
                id=reclamation_id,
                declaration__structure_locale=user.structure_locale
            )
            # Chercher ou créer une conversation pour cette réclamation
            selected_conversation = Conversation.objects.filter(
                signalement=reclamation.declaration,
                agent=user,
                declarant=reclamation.reclamant
            ).first()
            if not selected_conversation:
                selected_conversation = Conversation.objects.create(
                    signalement=reclamation.declaration,
                    agent=user,
                    declarant=reclamation.reclamant
                )
        except Reclamation.DoesNotExist:
            messages.error(request, 'Réclamation introuvable')
    elif signalement_id and declarant_id:
        try:
            from .models import Declaration, Utilisateur
            signalement = Declaration.objects.get(id=signalement_id)
            declarant = Utilisateur.objects.get(id=declarant_id)
            selected_conversation = Conversation.objects.filter(
                signalement=signalement,
                agent=user,
                declarant=declarant
            ).first()
            if not selected_conversation:
                selected_conversation = Conversation.objects.create(
                    signalement=signalement,
                    agent=user,
                    declarant=declarant
                )
                messages.success(request, "Une nouvelle conversation a été créée avec le déclarant.")
        except (Declaration.DoesNotExist, Utilisateur.DoesNotExist):
            messages.error(request, 'Signalement ou déclarant introuvable')
    
    # Activité récente
    activites_recentes = ActionLog.objects.filter(
        utilisateur=user
    ).select_related('declaration', 'reclamation').order_by('-date_action')[:10]

    context = {
        'stats': stats,
        'signalements_en_attente': signalements_en_attente,
        'reclamations_en_attente': reclamations_en_attente,
        'conversations_actives': conversations_actives,
        'activites_recentes': activites_recentes,
        'agent': user,
        'chat_focused': True,  # Indique que cette page est centrée sur le chat
        'selected_conversation': selected_conversation,  # Conversation à ouvrir automatiquement
    }
    
    return render(request, 'agent/chat_dashboard.html', context)


@login_required
@role_required(['agent'])
def mes_signalements(request):
    """
    Liste des signalements dans la structure locale de l'agent
    """
    user = request.user
    
    # Filtrage strict par structure locale uniquement
    if not user.structure_locale:
        messages.error(request, "Aucune structure locale assignée. Contactez votre administrateur.")
        return redirect('togo_agent:dashboard')
    
    base_filter = {'structure_locale': user.structure_locale}
    
    # Filtres supplémentaires
    statut_filter = request.GET.get('statut', '')
    type_filter = request.GET.get('type', '')
    search_query = request.GET.get('q', '')
    
    signalements = Declaration.objects.filter(**base_filter)
    
    if statut_filter:
        signalements = signalements.filter(statut=statut_filter)
    
    if type_filter:
        signalements = signalements.filter(type_declaration=type_filter)
    
    if search_query:
        signalements = signalements.filter(
            Q(nom_objet__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(numero_declaration__icontains=search_query)
        )
    
    signalements = signalements.select_related(
        'declarant', 'categorie', 'region', 'prefecture', 'structure_locale'
    ).order_by('-date_declaration')
    
    # Pagination
    paginator = Paginator(signalements, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'statut_filter': statut_filter,
        'type_filter': type_filter,
        'search_query': search_query,
        'statuts_choices': Declaration.STATUT_CHOICES,
        'types_choices': Declaration.TYPE_CHOICES,
    }
    
    return render(request, 'agent/mes_signalements.html', context)


@login_required
@role_required(['agent'])
def signalement_detail(request, signalement_id):
    """
    Détail d'un signalement avec actions possibles
    """
    user = request.user
    signalement = get_object_or_404(Declaration, id=signalement_id)
    
    # Vérification des droits d'accès (même zone)
    if not _agent_peut_acceder_signalement(user, signalement):
        messages.error(request, "Vous n'avez pas accès à ce signalement.")
        return redirect('togo_agent:mes_signalements')
    
    # Réclamations liées
    reclamations = signalement.reclamations.all().select_related('reclamant').order_by('-date_reclamation')
    
    # Commentaires
    commentaires = signalement.commentaires_anonymes.filter(est_approuve=True).order_by('date_creation')
    
    # Conversations
    conversations = Conversation.objects.filter(
        signalement=signalement,
        agent=user
    ).order_by('-created_at')
    
    # Historique des actions
    historique = ActionLog.objects.filter(
        declaration=signalement
    ).select_related('utilisateur').order_by('-date_action')
    
    context = {
        'signalement': signalement,
        'reclamations': reclamations,
        'commentaires': commentaires,
        'conversations': conversations,
        'historique': historique,
        'peut_valider': signalement.peut_etre_valide(),
        'peut_marquer_retrouve': (
            signalement.type_declaration == 'perdu' and 
            signalement.statut == 'valide'
        ),
        'peut_marquer_restitue': (
            (signalement.type_declaration == 'perdu' and signalement.statut == 'publie') or
            (signalement.type_declaration == 'trouve' and signalement.statut == 'valide')
        ),
        'peut_publier': signalement.peut_etre_publiee(),
    }
    
    return render(request, 'agent/signalement_detail.html', context)


@login_required
@role_required(['agent'])
@login_required
@role_required(['agent'])
def commentaires_echanges(request):
    """
    Module de gestion des commentaires et échanges
    """
    user = request.user
    
    # Filtrage strict par structure locale uniquement
    if not user.structure_locale:
        messages.error(request, "Aucune structure locale assignée.")
        return redirect('togo_agent:dashboard')
    
    base_filter = {'declaration__structure_locale': user.structure_locale}
    
    # Commentaires récents sur les signalements de la zone
    try:
        # Récupérer tous les commentaires de la zone
        commentaires = CommentaireAnonyme.objects.filter(
            declaration__structure_locale=user.structure_locale
        ).select_related('declaration').order_by('-date_creation')
        
        # Filtres
        statut_filter = request.GET.get('statut', 'tous')
        if statut_filter == 'approuves':
            commentaires = commentaires.filter(est_approuve=True)
        elif statut_filter == 'en_attente':
            commentaires = commentaires.filter(est_approuve=False)
        
        # Grouper les commentaires par signalement
        from collections import defaultdict
        signalements_avec_commentaires = defaultdict(list)
        
        for commentaire in commentaires:
            if commentaire.declaration:
                signalements_avec_commentaires[commentaire.declaration].append(commentaire)
        
        # Trier les signalements par date du commentaire le plus récent
        signalements_groupes = []
        for signalement, commentaires_list in signalements_avec_commentaires.items():
            # Trier les commentaires de ce signalement par date
            commentaires_list.sort(key=lambda c: c.date_creation)
            signalements_groupes.append({
                'signalement': signalement,
                'commentaires': commentaires_list,
                'dernier_commentaire_date': commentaires_list[-1].date_creation if commentaires_list else None,
                'nombre_commentaires': len(commentaires_list)
            })
        
        # Trier par date du dernier commentaire (plus récent en premier)
        signalements_groupes.sort(key=lambda x: x['dernier_commentaire_date'] or timezone.now(), reverse=True)
        
        # Statistiques
        stats = {
            'total_commentaires': commentaires.count(),
            'commentaires_approuves': commentaires.filter(est_approuve=True).count(),
            'commentaires_en_attente': commentaires.filter(est_approuve=False).count(),
            'signalements_avec_commentaires': len(signalements_groupes),
        }
        
    except Exception as e:
        print(f"❌ Erreur commentaires: {e}")
        signalements_groupes = []
        stats = {
            'total_commentaires': 0,
            'commentaires_approuves': 0,
            'commentaires_en_attente': 0,
            'signalements_avec_commentaires': 0,
        }
    
    # Pagination des signalements groupés
    from django.core.paginator import Paginator
    paginator = Paginator(signalements_groupes, 10)  # 10 signalements par page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'signalements_groupes': page_obj,
        'stats': stats,
        'statut_filter': statut_filter,
        'agent': user,
    }
    
    return render(request, 'agent/commentaires_echanges.html', context)

@login_required
@role_required(['agent'])
def repondre_commentaire(request, commentaire_id):
    """Répondre à un commentaire anonyme"""
    if request.method == 'POST':
        from django.http import JsonResponse
        from django.shortcuts import redirect
        from django.contrib import messages
        
        try:
            contenu = request.POST.get('contenu')
            
            if not contenu:
                messages.error(request, 'Le contenu de la réponse est requis')
                return redirect('togo_agent:commentaires_echanges')
            
            commentaire = CommentaireAnonyme.objects.get(id=commentaire_id)
            
            # TODO: Implémenter la logique de réponse selon vos besoins
            # Par exemple, envoyer un email au déclarant ou créer un nouveau commentaire
            
            messages.success(request, f'Réponse envoyée pour le commentaire de {commentaire.get_display_name()}')
            return redirect('togo_agent:commentaires_echanges')
            
        except CommentaireAnonyme.DoesNotExist:
            messages.error(request, 'Commentaire introuvable')
            return redirect('togo_agent:commentaires_echanges')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
            return redirect('togo_agent:commentaires_echanges')
    
    return redirect('togo_agent:commentaires_echanges')


@login_required
@role_required(['agent'])
def approuver_commentaire(request, commentaire_id):
    """Approuver un commentaire en attente"""
    if request.method == 'POST':
        try:
            commentaire = CommentaireAnonyme.objects.get(
                id=commentaire_id,
                declaration__structure_locale=request.user.structure_locale
            )
            commentaire.est_approuve = True
            commentaire.save()
            
            messages.success(request, f'Commentaire de {commentaire.get_display_name()} approuvé avec succès.')
            
        except CommentaireAnonyme.DoesNotExist:
            messages.error(request, 'Commentaire introuvable ou non autorisé.')
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'approbation: {str(e)}')
    
    return redirect('togo_agent:commentaires_echanges')


@login_required
@role_required(['agent'])
def rejeter_commentaire(request, commentaire_id):
    """Rejeter/supprimer un commentaire en attente"""
    if request.method == 'POST':
        try:
            commentaire = CommentaireAnonyme.objects.get(
                id=commentaire_id,
                declaration__structure_locale=request.user.structure_locale
            )
            pseudo = commentaire.get_display_name()
            commentaire.delete()
            
            messages.success(request, f'Commentaire de {pseudo} rejeté et supprimé.')
            
        except CommentaireAnonyme.DoesNotExist:
            messages.error(request, 'Commentaire introuvable ou non autorisé.')
        except Exception as e:
            messages.error(request, f'Erreur lors du rejet: {str(e)}')
    
    return redirect('togo_agent:commentaires_echanges')


@login_required
@role_required(['agent'])
def repondre_signalement(request, signalement_id):
    """Ajouter une réponse/commentaire à un signalement"""
    if request.method == 'POST':
        try:
            signalement = Declaration.objects.get(
                id=signalement_id,
                structure_locale=request.user.structure_locale
            )
            
            contenu = request.POST.get('contenu', '').strip()
            if not contenu:
                messages.error(request, 'Le contenu du commentaire est requis.')
                return redirect('togo_agent:commentaires_echanges')
            
            # Créer un nouveau commentaire de la part de l'agent
            CommentaireAnonyme.objects.create(
                declaration=signalement,
                contenu=contenu,
                pseudo=f"Agent {request.user.get_full_name() or request.user.username}",
                est_approuve=True,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Votre réponse a été ajoutée au signalement "{signalement.nom_objet}".')
            
        except Declaration.DoesNotExist:
            messages.error(request, 'Signalement introuvable ou non autorisé.')
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'ajout de la réponse: {str(e)}')
    
    return redirect('togo_agent:commentaires_echanges')


@login_required
@role_required(['agent'])
def marquer_retrouve(request, signalement_id):
    """
    Marquer un signalement d'objet perdu comme retrouvé
    """
    user = request.user
    signalement = get_object_or_404(Declaration, id=signalement_id)
    
    # Vérification des droits
    if not _agent_peut_acceder_signalement(user, signalement):
        messages.error(request, "Vous n'avez pas accès à ce signalement.")
        return redirect('togo_agent:mes_signalements')
    
    if request.method == 'POST':
        # Vérifier que c'est un objet perdu validé
        if signalement.type_declaration == 'perdu' and signalement.statut == 'valide':
            commentaire_agent = request.POST.get('commentaire_agent', '')
            
            # Mise à jour du signalement
            signalement.statut = 'publie'  # On utilise 'publie' pour "retrouvé"
            signalement.commentaire_agent = commentaire_agent
            signalement.save()
            
            # Log de l'action
            ActionLog.objects.create(
                declaration=signalement,
                utilisateur=user,
                action='objet_retrouve',
                description=f"Objet {signalement.nom_objet} marqué comme retrouvé par {user.get_full_name()}"
            )
            
            messages.success(request, f'L\'objet "{signalement.nom_objet}" a été marqué comme retrouvé.')
        else:
            messages.error(request, "Ce signalement ne peut pas être marqué comme retrouvé.")
    
    return redirect('togo_agent:signalement_detail', signalement_id=signalement_id)


@login_required
@role_required(['agent'])
def marquer_restitue(request, signalement_id):
    """
    Marquer un signalement comme restitué au propriétaire
    """
    user = request.user
    signalement = get_object_or_404(Declaration, id=signalement_id)
    
    # Vérification des droits
    if not _agent_peut_acceder_signalement(user, signalement):
        messages.error(request, "Vous n'avez pas accès à ce signalement.")
        return redirect('togo_agent:mes_signalements')
    
    if request.method == 'POST':
        # Vérifier les conditions pour la restitution
        conditions_ok = (
            (signalement.type_declaration == 'perdu' and signalement.statut == 'publie') or  # Objet perdu retrouvé
            (signalement.type_declaration == 'trouve' and signalement.statut == 'valide')     # Objet trouvé validé
        )
        
        if conditions_ok:
            commentaire_agent = request.POST.get('commentaire_agent', '')
            
            # Mise à jour du signalement
            signalement.statut = 'restitue'
            signalement.commentaire_agent = commentaire_agent
            signalement.save()
            
            # Log de l'action
            ActionLog.objects.create(
                declaration=signalement,
                utilisateur=user,
                action='objet_restitue',
                description=f"Objet {signalement.nom_objet} restitué au propriétaire par {user.get_full_name()}"
            )
            
            messages.success(request, f'L\'objet "{signalement.nom_objet}" a été marqué comme restitué au propriétaire.')
        else:
            messages.error(request, "Ce signalement ne peut pas être marqué comme restitué.")
    
    return redirect('togo_agent:signalement_detail', signalement_id=signalement_id)


@login_required
@role_required(['agent'])
def valider_signalement(request, signalement_id):
    """
    Valider un signalement (passage de 'cree' à 'valide')
    """
    user = request.user
    signalement = get_object_or_404(Declaration, id=signalement_id)
    
    # Vérification des droits
    if not _agent_peut_acceder_signalement(user, signalement):
        messages.error(request, "Vous n'avez pas accès à ce signalement.")
        return redirect('togo_agent:mes_signalements')
    
    if request.method == 'POST':
        if signalement.peut_etre_valide():
            commentaire_agent = request.POST.get('commentaire_agent', '')
            
            # Mise à jour du signalement
            signalement.statut = 'valide'
            signalement.agent_validateur = user
            signalement.commentaire_agent = commentaire_agent
            signalement.save()
            
            # Log de l'action
            ActionLog.objects.create(
                declaration=signalement,
                utilisateur=user,
                action='declaration_validee',
                description=f'Signalement validé par {user.get_full_name()}'
            )
            
            # Notification au déclarant
            if signalement.declarant:
                from core.models import Notification
                Notification.objects.create(
                    destinataire=signalement.declarant,
                    declaration=signalement,
                    type_notification='declaration_validee',
                    titre=f'Déclaration {signalement.numero_declaration} validée',
                    message=f'Bonjour {signalement.declarant.get_full_name()},\n\nVotre déclaration concernant "{signalement.nom_objet}" a été validée par nos services.\n\nCommentaire: {commentaire_agent}\n\nCordialement,\nL\'\u00e9quipe TogoRetrouve'
                )
            
            messages.success(request, f"✅ Signalement {signalement.numero_declaration} validé avec succès !")
        else:
            messages.error(request, "❌ Ce signalement ne peut pas être validé dans son état actuel.")
    
    return redirect('togo_agent:signalement_detail', signalement_id=signalement_id)


@login_required
@role_required(['agent'])
def contacter_declarant(request, signalement_id):
    """
    Interface de contact avec le déclarant (simplifiée)
    """
    user = request.user
    signalement = get_object_or_404(Declaration, id=signalement_id)
    
    # Vérification des droits
    if not _agent_peut_acceder_signalement(user, signalement):
        messages.error(request, "Vous n'avez pas accès à ce signalement.")
        return redirect('togo_agent:mes_signalements')
    
    from core.models import Conversation, Message
    # Récupérer ou créer la conversation unique pour ce signalement/agent/déclarant
    conversation, _ = Conversation.objects.get_or_create(
        signalement=signalement,
        agent=user,
        declarant=signalement.declarant
    )

    if request.method == 'POST':
        contenu = request.POST.get('contenu', '').strip()
        if contenu:
            destinataire = signalement.declarant
            Message.objects.create(
                conversation=conversation,
                sender=user,
                receiver=destinataire,
                contenu=contenu
            )
            messages.success(request, "✅ Message envoyé au déclarant !")
            return redirect('togo_agent:contacter_declarant', signalement_id=signalement_id)
        else:
            messages.error(request, "❌ Le message ne peut pas être vide.")

    # Récupérer les messages de la conversation (ordre chronologique)
    messages_conv = conversation.messages.select_related('sender').order_by('created_at')

    context = {
        'signalement': signalement,
        'declarant': signalement.declarant,
        'conversation': conversation,
        'messages_conv': messages_conv,
        'user': user,
    }
    return render(request, 'agent/contacter_declarant.html', context)


@login_required
@role_required(['agent'])
def generer_rapport(request, signalement_id):
    """
    Génération de rapport PDF moderne pour un signalement
    """
    user = request.user
    signalement = get_object_or_404(Declaration, id=signalement_id)
    
    # Vérification des droits
    if not _agent_peut_acceder_signalement(user, signalement):
        messages.error(request, "Vous n'avez pas accès à ce signalement.")
        return redirect('togo_agent:mes_signalements')
    
    from django.http import HttpResponse
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.colors import Color, HexColor
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.platypus import Image as RLImage
    from reportlab.lib import colors
    import io
    from datetime import datetime
    import textwrap
    
    # Créer le buffer PDF
    buffer = io.BytesIO()
    
    # Configuration du document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2*cm,
        bottomMargin=2*cm,
        leftMargin=2*cm,
        rightMargin=2*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Style personnalisé pour le titre principal
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=18,
        textColor=HexColor('#2563eb'),
        spaceAfter=30,
        alignment=1,  # Centré
        fontName='Helvetica-Bold'
    )
    
    # Style pour les en-têtes de section
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=HexColor('#1f2937'),
        spaceBefore=20,
        spaceAfter=12,
        fontName='Helvetica-Bold',
        borderWidth=2,
        borderColor=HexColor('#3b82f6'),
        borderPadding=8,
        backColor=HexColor('#eff6ff')
    )
    
    # Style pour le contenu
    content_style = ParagraphStyle(
        'Content',
        parent=styles['Normal'],
        fontSize=11,
        textColor=HexColor('#374151'),
        spaceAfter=8,
        fontName='Helvetica'
    )
    
    # Style pour les informations importantes
    highlight_style = ParagraphStyle(
        'Highlight',
        parent=styles['Normal'],
        fontSize=12,
        textColor=HexColor('#1f2937'),
        fontName='Helvetica-Bold',
        spaceAfter=6
    )
    
    # Contenu du rapport
    story = []
    
    # En-tête officiel
    header_table = Table([
        ['RÉPUBLIQUE TOGOLAISE', ''],
        ['Ministère de l\'Intérieur et de la Sécurité', ''],
        ['Plateforme TogoRetrouve', f'Rapport N°: {signalement.numero_declaration}'],
        ['', f'Date: {datetime.now().strftime("%d/%m/%Y à %H:%M")}']
    ], colWidths=[12*cm, 6*cm])
    
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, 0), 14),
        ('FONTSIZE', (0, 1), (0, 2), 12),
        ('TEXTCOLOR', (0, 0), (1, 2), colors.darkblue),
        ('ALIGN', (1, 0), (1, 3), 'RIGHT'),
        ('FONTNAME', (1, 2), (1, 3), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 2), (1, 3), 10),
        ('VALIGN', (0, 0), (1, 3), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (1, 3), 8),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 30))
    
    # Titre principal
    story.append(Paragraph("RAPPORT DE SIGNALEMENT D'OBJET", title_style))
    
    # Informations du signalement
    story.append(Paragraph("INFORMATIONS GÉNÉRALES", section_style))
    
    info_data = [
        ['Numéro de déclaration:', signalement.numero_declaration],
        ['Type de déclaration:', signalement.get_type_declaration_display()],
        ['Statut actuel:', signalement.get_statut_display()],
        ['Date de l\'incident:', signalement.date_incident.strftime('%d/%m/%Y') if signalement.date_incident else 'Non spécifiée'],
        ['Date de déclaration:', signalement.date_declaration.strftime('%d/%m/%Y à %H:%M')],
        ['Agent validateur:', user.get_full_name() or user.username],
        ['Structure:', str(user.structure_locale)]
    ]
    
    info_table = Table(info_data, colWidths=[5*cm, 11*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (1, -1), 11),
        ('GRID', (0, 0), (1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#f3f4f6')),
        ('PADDING', (0, 0), (1, -1), 8),
        ('VALIGN', (0, 0), (1, -1), 'TOP'),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # Détails de l'objet
    story.append(Paragraph("DÉTAILS DE L'OBJET", section_style))
    
    objet_data = [
        ['Nom de l\'objet:', signalement.nom_objet or '']
    ]
    
    objet_table = Table(objet_data, colWidths=[5*cm, 11*cm])
    objet_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (1, -1), 11),
        ('GRID', (0, 0), (1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#f3f4f6')),
        ('PADDING', (0, 0), (1, -1), 8),
        ('VALIGN', (0, 0), (1, -1), 'TOP'),
    ]))
    
    story.append(objet_table)
    story.append(Spacer(1, 20))
    
    # Photo de l'objet (si disponible)
    if signalement.photo_principale:
        try:
            story.append(Paragraph("PHOTO DE L'OBJET", section_style))
            
            # Redimensionner l'image pour qu'elle s'adapte au PDF
            max_width = 8*cm
            max_height = 6*cm
            
            img = RLImage(signalement.photo_principale.path, 
                         width=max_width, height=max_height)
            
            # Centrer l'image
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Spacer(1, 20))
            
        except Exception as e:
            # Si l'image ne peut pas être chargée, afficher un message
            story.append(Paragraph("PHOTO DE L'OBJET", section_style))
            story.append(Paragraph("Photo non disponible ou corrompue", content_style))
            story.append(Spacer(1, 20))
    
    # Localisation
    story.append(Paragraph("LOCALISATION", section_style))
    
    localisation_data = [
        ['Préfecture:', str(signalement.prefecture) if signalement.prefecture else 'Non spécifiée'],
        ['Structure locale:', str(signalement.structure_locale) if signalement.structure_locale else 'Non spécifiée'],
        ['Lieu précis:', signalement.lieu_precis or 'Non spécifié']
    ]
    
    localisation_table = Table(localisation_data, colWidths=[5*cm, 11*cm])
    localisation_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (1, -1), 11),
        ('GRID', (0, 0), (1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#f3f4f6')),
        ('PADDING', (0, 0), (1, -1), 8),
        ('VALIGN', (0, 0), (1, -1), 'TOP'),
    ]))
    
    story.append(localisation_table)
    story.append(Spacer(1, 20))
    
    # Informations du déclarant
    story.append(Paragraph("INFORMATIONS DU DÉCLARANT", section_style))
    
    declarant = signalement.declarant
    declarant_data = [
        ['Nom complet:', declarant.get_full_name() or ''],
        ['Nom d\'utilisateur:', declarant.username],
        ['Email:', declarant.email or ''],
        ['Téléphone:', declarant.telephone or ''],
        ['Adresse:', getattr(declarant, 'adresse', '')],
        ['Date d\'inscription:', declarant.date_joined.strftime('%d/%m/%Y') if declarant.date_joined else '']
    ]
    
    declarant_table = Table(declarant_data, colWidths=[5*cm, 11*cm])
    declarant_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (1, -1), 11),
        ('GRID', (0, 0), (1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#f3f4f6')),
        ('PADDING', (0, 0), (1, -1), 8),
        ('VALIGN', (0, 0), (1, -1), 'TOP'),
    ]))
    
    story.append(declarant_table)
    story.append(Spacer(1, 20))
    
    # Réclamations liées (si existantes)
    reclamations = signalement.reclamations.all()
    if reclamations.exists():
        story.append(Paragraph("RÉCLAMATIONS ASSOCIÉES", section_style))
        
        for idx, reclamation in enumerate(reclamations[:3], 1):  # Limiter à 3 réclamations
            story.append(Paragraph(f"<b>Réclamation #{idx}:</b>", highlight_style))
            
            reclamation_data = [
                ['Réclamant:', reclamation.reclamant.get_full_name() or ''],
                ['Email:', reclamation.reclamant.email or ''],
                ['Téléphone:', reclamation.telephone_contact or ''],
                ['Date de réclamation:', reclamation.date_reclamation.strftime('%d/%m/%Y à %H:%M')],
                ['Statut:', reclamation.get_statut_display()],
                ['Agent traitant:', reclamation.agent_traitant.get_full_name() if reclamation.agent_traitant else '']
            ]
            
            reclamation_table = Table(reclamation_data, colWidths=[4*cm, 12*cm])
            reclamation_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (1, -1), 10),
                ('GRID', (0, 0), (1, -1), 0.5, colors.lightgrey),
                ('BACKGROUND', (0, 0), (0, -1), HexColor('#fafafa')),
                ('PADDING', (0, 0), (1, -1), 6),
            ]))
            
            story.append(reclamation_table)
            story.append(Spacer(1, 10))
    

    
    story.append(Spacer(1, 30))
    
    # Pied de page avec signature
    footer_data = [
        ['Agent responsable:', ''],
        [f'{user.get_full_name() or user.username}', ''],
        [f'{user.structure_locale}', ''],
        ['', ''],
        ['Signature:', '_' * 30]
    ]
    
    footer_table = Table(footer_data, colWidths=[8*cm, 8*cm])
    footer_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (1, -1), 11),
        ('PADDING', (0, 0), (1, -1), 6),
        ('ALIGN', (1, 4), (1, 4), 'CENTER'),
    ]))
    
    story.append(footer_table)
    
    # Mention légale
    story.append(Spacer(1, 20))
    legal_text = f"""
    <i>Ce rapport est généré automatiquement par le système TogoRetrouve le {datetime.now().strftime('%d/%m/%Y à %H:%M')}.<br/>
    Il constitue un document officiel dans le cadre de la procédure de récupération d'objets perdus.<br/>
    Toute falsification de ce document est passible de sanctions selon la loi togolaise.</i>
    """
    story.append(Paragraph(legal_text, ParagraphStyle(
        'Legal',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=1,  # Centré
        fontName='Helvetica-Oblique'
    )))
    
    # Construire le PDF
    doc.build(story)
    
    # Log de l'action
    ActionLog.objects.create(
        declaration=signalement,
        utilisateur=user,
        action='rapport_genere',
        description=f'Rapport PDF moderne généré par {user.get_full_name() or user.username}'
    )
    
    # Retourner le PDF
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_moderne_{signalement.numero_declaration}_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf"'
    
    return response


@login_required
@role_required(['agent'])
def verification_identite(request):
    """
    Module de vérification d'identité des réclamants et fichiers de conversations
    """
    user = request.user
    
    # Filtrage strict par structure locale uniquement
    if not user.structure_locale:
        messages.error(request, "Aucune structure locale assignée.")
        return redirect('togo_agent:dashboard')
    
    base_filter = {'declaration__structure_locale': user.structure_locale}
    
    # Réclamations en attente avec pièces justificatives
    reclamations_a_verifier = Reclamation.objects.filter(
        **base_filter,
        statut='soumise'
    ).prefetch_related(
        'pieces_justificatives'
    ).select_related('declaration', 'reclamant').order_by('-date_reclamation')
    
    # Fichiers envoyés dans les conversations (messagerie)
    # Récupérer les conversations de l'agent où des fichiers ont été envoyés
    conversations_agent = Conversation.objects.filter(
        signalement__structure_locale=user.structure_locale
    ).prefetch_related('messages').select_related('signalement', 'declarant')
    
    # Extraire les messages avec fichiers
    fichiers_conversations = []
    for conversation in conversations_agent:
        messages_avec_fichiers = conversation.messages.filter(
            fichier__isnull=False
        ).exclude(fichier='').select_related('sender').order_by('-created_at')
        
        for msg in messages_avec_fichiers:
            fichiers_conversations.append({
                'message': msg,
                'conversation': conversation,
                'signalement': conversation.signalement,
                'declarant': conversation.declarant,
            })
    
    # Statistiques
    stats = {
        'en_attente': Reclamation.objects.filter(**base_filter, statut='soumise').count(),
        'en_cours': Reclamation.objects.filter(**base_filter, statut='en_cours').count(),
        'valides': Reclamation.objects.filter(**base_filter, statut='approuvee').count(),
        'rejetes': Reclamation.objects.filter(**base_filter, statut='rejetee').count(),
        'fichiers_messagerie': len(fichiers_conversations),
    }
    
    context = {
        'reclamations_a_verifier': reclamations_a_verifier,
        'fichiers_conversations': fichiers_conversations,
        'stats': stats,
    }
    
    return render(request, 'agent/verification_identite.html', context)


@login_required
@role_required(['agent'])
def verifier_reclamation(request, reclamation_id):
    """
    Page de vérification détaillée d'une réclamation
    """
    user = request.user
    reclamation = get_object_or_404(Reclamation, id=reclamation_id)
    
    # Vérification des droits d'accès
    if not _agent_peut_acceder_signalement(user, reclamation.declaration):
        messages.error(request, "Vous n'avez pas accès à cette réclamation.")
        return redirect('togo_agent:verification_identite')
    
    pieces_justificatives = reclamation.pieces_justificatives.all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        commentaire = request.POST.get('commentaire', '')
        
        if action == 'approuver':
            reclamation.statut = 'approuvee'
            reclamation.agent_traitant = user
            reclamation.date_traitement = timezone.now()
            reclamation.commentaire_agent = commentaire
            reclamation.save()
            
            # Log de l'action
            ActionLog.objects.create(
                utilisateur=user,
                reclamation=reclamation,
                action='reclamation_approuvee',
                description=f"Réclamation {reclamation.numero_reclamation} approuvée"
            )
            
            # Notification au réclamant
            Notification.objects.create(
                destinataire=reclamation.reclamant,
                reclamation=reclamation,
                type_notification='reclamation_approuvee',
                titre='Réclamation approuvée',
                message=f'Votre réclamation {reclamation.numero_reclamation} a été approuvée. Vous pouvez venir récupérer votre objet.',
            )
            
            messages.success(request, f'Réclamation {reclamation.numero_reclamation} approuvée.')
            
        elif action == 'rejeter':
            reclamation.statut = 'rejetee'
            reclamation.agent_traitant = user
            reclamation.date_traitement = timezone.now()
            reclamation.motif_rejet = commentaire
            reclamation.save()
            
            # Log de l'action
            ActionLog.objects.create(
                utilisateur=user,
                reclamation=reclamation,
                action='reclamation_rejetee',
                description=f"Réclamation {reclamation.numero_reclamation} rejetée"
            )
            
            # Notification au réclamant
            Notification.objects.create(
                destinataire=reclamation.reclamant,
                reclamation=reclamation,
                type_notification='reclamation_rejetee',
                titre='Réclamation rejetée',
                message=f'Votre réclamation {reclamation.numero_reclamation} a été rejetée. Motif: {commentaire}',
            )
            
            messages.warning(request, f'Réclamation {reclamation.numero_reclamation} rejetée.')
        
        return redirect('togo_agent:verification_identite')
    
    context = {
        'reclamation': reclamation,
        'pieces_justificatives': pieces_justificatives,
    }
    
    return render(request, 'agent/verifier_reclamation.html', context)


@login_required
@role_required(['agent'])
def messagerie(request):
    """
    Interface de messagerie pour l'agent avec liste des conversations
    """
    user = request.user
    
    # Filtrage strict par structure locale uniquement
    if not user.structure_locale:
        messages.error(request, "Aucune structure locale assignée. Contactez votre administrateur.")
        return redirect('togo_agent:dashboard')
    
    # Récupérer toutes les conversations de l'agent
    conversations = Conversation.objects.filter(
        agent=user
    ).select_related('signalement', 'declarant', 'agent').annotate(
        messages_non_lus=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=user)),
        dernier_message_date=Max('messages__created_at')
    ).order_by('-updated_at')
    
    # Conversation sélectionnée (première par défaut ou spécifiée)
    conversation_id = request.GET.get('conversation_id')
    selected_conversation = None
    messages_conv = []
    
    if conversation_id:
        try:
            selected_conversation = conversations.get(id=conversation_id)
        except Conversation.DoesNotExist:
            pass
    elif conversations.exists():
        selected_conversation = conversations.first()
    
    if selected_conversation:
        # Messages de la conversation sélectionnée
        messages_conv = selected_conversation.messages.select_related('sender').order_by('created_at')
        
        # Marquer les messages comme lus
        messages_conv.filter(is_read=False).exclude(sender=user).update(
            is_read=True
        )
    
    context = {
        'conversations': conversations,
        'selected_conversation': selected_conversation,
        'messages_conv': messages_conv,
        'agent': user,
    }
    
    return render(request, 'agent/messagerie.html', context)


@login_required
@role_required(['agent'])
@require_POST
def send_message(request, conversation_id):
    """
    Envoi d'un message dans une conversation via AJAX
    """
    try:
        user = request.user
        conversation = get_object_or_404(Conversation, id=conversation_id, agent=user)
        
        # Parser le contenu depuis POST ou JSON
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            contenu = data.get('content', '').strip()
        else:
            contenu = request.POST.get('content', '').strip()
        
        # Récupérer le fichier s'il existe
        fichier = request.FILES.get('fichier')
        
        # Vérifier qu'il y a au moins un contenu ou un fichier
        if not contenu and not fichier:
            return JsonResponse({'success': False, 'error': 'Message vide'})
        
        # Déterminer le type de message
        type_message = 'fichier' if fichier else 'texte'
        
        # Créer le message
        message = Message.objects.create(
            conversation=conversation,
            sender=user,
            receiver=conversation.declarant,
            contenu=contenu,
            fichier=fichier,
            type_message=type_message
        )
        
        # Mettre à jour la conversation
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['updated_at'])
        
        # Créer une notification pour le déclarant
        Notification.objects.create(
            destinataire=conversation.declarant,
            type_notification='nouveau_message',
            titre='Nouveau message',
            message=f'Vous avez reçu un nouveau message de {user.get_full_name() or user.username}',
        )
        
        # Retourner les données du message pour l'interface
        message_data = {
            'id': message.id,
            'contenu': message.contenu,
            'content': message.contenu,
            'created_at': message.created_at.strftime('%H:%M'),
            'sender_name': user.get_full_name() or user.username,
            'is_from_agent': True
        }
        
        # Ajouter les infos du fichier si présent
        if message.fichier:
            try:
                message_data['fichier_url'] = message.fichier.url
                message_data['file_name'] = message.file_name
                message_data['is_image'] = message.is_image
                message_data['file_size'] = message.file_size
            except Exception as file_error:
                # Si erreur d'accès au fichier, on continue sans bloquer
                print(f"Erreur fichier: {file_error}")
                message_data['fichier_url'] = None
        
        return JsonResponse({
            'success': True,
            'message': message_data
        })
        
    except json.JSONDecodeError as e:
        print(f"Erreur JSON: {e}")
        return JsonResponse({'success': False, 'error': 'Format JSON invalide'})
    except Exception as e:
        print(f"Erreur générale: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@role_required(['agent'])
def conversation_detail(request, conversation_id):
    """
    Redirection vers la messagerie avec la conversation sélectionnée
    """
    user = request.user
    # Vérifier que la conversation existe et appartient à l'agent
    conversation = get_object_or_404(Conversation, id=conversation_id, agent=user)
    
    # Rediriger vers la messagerie avec cette conversation
    return redirect(f'{reverse("togo_agent:messagerie")}?conversation_id={conversation_id}')


@login_required
@role_required(['agent'])
def get_conversation_messages(request, conversation_id):
    """
    API pour récupérer les messages d'une conversation (pour le polling)
    """
    try:
        user = request.user
        conversation = get_object_or_404(Conversation, id=conversation_id, agent=user)
        
        # Récupérer les messages
        messages_list = []
        for msg in conversation.messages.all().select_related('sender').order_by('created_at'):
            message_data = {
                'id': msg.id,
                'contenu': msg.contenu,
                'content': msg.contenu,  # Alias pour compatibilité
                'created_at': msg.created_at.strftime('%H:%M'),
                'sender_name': msg.sender.get_full_name() or msg.sender.username,
                'is_from_agent': msg.sender == user,
                'is_read': msg.is_read
            }
            
            # Ajouter les infos sur le fichier si présent
            if msg.fichier:
                message_data['fichier_url'] = msg.fichier.url
                message_data['file_name'] = msg.file_name
                message_data['is_image'] = msg.is_image
                message_data['file_size'] = msg.file_size
            
            messages_list.append(message_data)
        
        # Marquer les messages non lus comme lus
        conversation.messages.filter(is_read=False).exclude(sender=user).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        # Préparer les infos de la conversation
        declarant = conversation.declarant
        conversation_data = {
            'declarant_name': declarant.get_full_name() or declarant.username,
            'declarant_initial': (declarant.first_name[0] if declarant.first_name else declarant.username[0]).upper(),
            'sujet': conversation.signalement.nom_objet if conversation.signalement else 'Conversation générale'
        }
        
        return JsonResponse({
            'success': True,
            'messages': messages_list,
            'conversation': conversation_data
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@role_required(['agent'])
@require_POST
def valider_restitution(request, reclamation_id):
    """
    Valider la restitution finale d'un objet
    """
    user = request.user
    reclamation = get_object_or_404(Reclamation, id=reclamation_id, statut='approuvee')
    
    # Vérification des droits d'accès
    if not _agent_peut_acceder_signalement(user, reclamation.declaration):
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    # Marquer comme restitué
    reclamation.declaration.statut = 'restitue'
    reclamation.declaration.date_restitution = timezone.now()
    reclamation.declaration.save()
    
    # Log de l'action
    ActionLog.objects.create(
        utilisateur=user,
        declaration=reclamation.declaration,
        reclamation=reclamation,
        action='objet_restitue',
        description=f"Objet {reclamation.declaration.nom_objet} restitué à {reclamation.reclamant.get_full_name()}"
    )
    
    # Notification au réclamant
    Notification.objects.create(
        destinataire=reclamation.reclamant,
        declaration=reclamation.declaration,
        type_notification='objet_restitue',
        titre='Objet restitué',
        message=f'Votre objet {reclamation.declaration.nom_objet} a été officiellement restitué.',
    )
    
    messages.success(request, f'Restitution validée pour {reclamation.declaration.nom_objet}.')
    return JsonResponse({
        'success': True, 
        'message': 'Restitution validée avec succès',
        'recu_url': f'/agent/recu/{reclamation.id}/'
    })


@login_required
@role_required(['agent'])
def generer_recu_restitution(request, reclamation_id):
    """
    Générer un reçu de restitution
    """
    user = request.user
    reclamation = get_object_or_404(Reclamation, id=reclamation_id)
    
    # Vérification des droits d'accès
    if not _agent_peut_acceder_signalement(user, reclamation.declaration):
        messages.error(request, "Vous n'avez pas accès à cette réclamation.")
        return redirect('togo_agent:verification_identite')
    
    context = {
        'reclamation': reclamation,
        'agent': user,
        'date_impression': timezone.now(),
    }
    
    return render(request, 'agent/recu_restitution.html', context)


@login_required
@role_required(['agent'])
def ouvrir_conversation(request):
    """
    Ouvrir ou créer une conversation pour un signalement donné
    """
    user = request.user
    signalement_id = request.GET.get('signalement_id')
    declarant_id = request.GET.get('declarant_id')
    
    if not signalement_id or not declarant_id:
        return redirect('togo_agent:messagerie')
    
    signalement = get_object_or_404(Declaration, id=signalement_id)
    declarant = get_object_or_404(Utilisateur, id=declarant_id)
    
    # Récupérer ou créer la conversation
    conv, _ = Conversation.objects.get_or_create(
        signalement=signalement,
        agent=user,
        declarant=declarant
    )
    
    return redirect(f'/agent/messagerie/?conversation_id={conv.id}')


def _agent_peut_acceder_signalement(agent, signalement):
    """
    Vérifier si un agent peut accéder à un signalement
    basé sur sa structure locale uniquement
    """
    # Un agent ne peut accéder qu'aux signalements de sa structure locale
    if agent.structure_locale and signalement.structure_locale:
        return agent.structure_locale == signalement.structure_locale
    
    # Si l'agent n'a pas de structure définie, accès refusé
    return False


# ===== VUES AJAX =====

@login_required
@role_required(['agent'])
def ajax_statistiques_dashboard(request):
    """
    Données AJAX pour mettre à jour les statistiques du dashboard
    """
    user = request.user
    
    # Filtrage strict par structure locale uniquement
    if not user.structure_locale:
        return JsonResponse({'error': 'Structure locale non assignée'})
    
    base_filter = {'structure_locale': user.structure_locale}
    
    # Statistiques en temps réel
    stats = {
        'total_signalements': Declaration.objects.filter(**base_filter).count(),
        'objets_retrouves': Declaration.objects.filter(
            **base_filter, 
            type_declaration='trouve', 
            agent_validateur=user
        ).count(),
        'objets_restitues': Declaration.objects.filter(
            **base_filter, 
            statut='restitue'
        ).count(),
        'demandes_attente': Reclamation.objects.filter(
            declaration__in=Declaration.objects.filter(**base_filter),
            statut='soumise'
        ).count(),
    }
    
    return JsonResponse({'stats': stats})


@login_required
@role_required(['agent'])
def ajax_marquer_notification_lue(request, notification_id):
    """
    Marquer une notification comme lue
    """
    if request.method == 'POST':
        notification = get_object_or_404(Notification, id=notification_id, destinataire=request.user)
        notification.marquer_comme_lue()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})


@login_required
@role_required(['agent'])
def agent_profil(request):
    """
    Page de profil de l'agent
    """
    user = request.user
    
    if request.method == 'POST':
        # Mise à jour des informations de profil
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        telephone = request.POST.get('telephone', '').strip()
        
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if email:
            user.email = email
        if telephone:
            user.telephone = telephone
        
        user.save()
        messages.success(request, 'Votre profil a été mis à jour avec succès.')
        return redirect('togo_agent:profil')
    
    # Statistiques de l'agent
    base_filter = {'structure_locale': user.structure_locale}
    stats = {
        'signalements_traites': Declaration.objects.filter(**base_filter, agent_validateur=user).count(),
        'reclamations_verifiees': Reclamation.objects.filter(agent_traitant=user).count(),
        'objets_restitues': Declaration.objects.filter(**base_filter, statut='restitue', agent_validateur=user).count(),
    }
    
    context = {
        'agent': user,
        'stats': stats,
    }
    
    return render(request, 'agent/profil.html', context)


@login_required
@role_required(['agent'])
def agent_parametres(request):
    """
    Page des paramètres de l'agent
    """
    user = request.user
    
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not current_password or not new_password or not confirm_password:
            messages.error(request, 'Veuillez remplir tous les champs.')
        elif not user.check_password(current_password):
            messages.error(request, 'Le mot de passe actuel est incorrect.')
        elif new_password != confirm_password:
            messages.error(request, 'Les nouveaux mots de passe ne correspondent pas.')
        elif len(new_password) < 6:
            messages.error(request, 'Le mot de passe doit contenir au moins 6 caractères.')
        else:
            user.set_password(new_password)
            user.save()
            messages.success(request, 'Votre mot de passe a été modifié avec succès. Veuillez vous reconnecter.')
            return redirect('login')
        
        return redirect('togo_agent:parametres')
    
    context = {
        'agent': user,
    }
    
    return render(request, 'agent/parametres.html', context)


@login_required
@role_required(['agent'])
def valider_document_verification(request, reclamation_id):
    """
    API pour valider un document d'identité (AJAX)
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)
    
    user = request.user
    reclamation = get_object_or_404(Reclamation, id=reclamation_id)
    
    # Vérification des droits d'accès
    if not _agent_peut_acceder_signalement(user, reclamation.declaration):
        return JsonResponse({'success': False, 'message': "Vous n'avez pas accès à cette réclamation"}, status=403)
    
    # Validation
    reclamation.statut = 'approuvee'
    reclamation.agent_traitant = user
    reclamation.date_traitement = timezone.now()
    reclamation.save()
    
    # Log de l'action
    ActionLog.objects.create(
        utilisateur=user,
        reclamation=reclamation,
        action='reclamation_approuvee',
        description=f"Réclamation {reclamation.numero_reclamation} approuvée"
    )
    
    # Notification au réclamant
    Notification.objects.create(
        destinataire=reclamation.reclamant,
        reclamation=reclamation,
        type_notification='reclamation_approuvee',
        titre='Réclamation approuvée',
        message=f'Votre réclamation {reclamation.numero_reclamation} a été approuvée. Vous pouvez venir récupérer votre objet.',
    )
    
    return JsonResponse({'success': True, 'message': 'Document validé avec succès'})


@login_required
@role_required(['agent'])
def rejeter_document_verification(request, reclamation_id):
    """
    API pour rejeter un document d'identité (AJAX)
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)
    
    user = request.user
    reclamation = get_object_or_404(Reclamation, id=reclamation_id)
    
    # Vérification des droits d'accès
    if not _agent_peut_acceder_signalement(user, reclamation.declaration):
        return JsonResponse({'success': False, 'message': "Vous n'avez pas accès à cette réclamation"}, status=403)
    
    # Récupération de la raison du rejet
    import json
    try:
        data = json.loads(request.body)
        raison = data.get('raison', '')
    except:
        raison = ''
    
    # Rejet
    reclamation.statut = 'rejetee'
    reclamation.agent_traitant = user
    reclamation.date_traitement = timezone.now()
    reclamation.motif_rejet = raison
    reclamation.save()
    
    # Log de l'action
    ActionLog.objects.create(
        utilisateur=user,
        reclamation=reclamation,
        action='reclamation_rejetee',
        description=f"Réclamation {reclamation.numero_reclamation} rejetée"
    )
    
    # Notification au réclamant
    Notification.objects.create(
        destinataire=reclamation.reclamant,
        reclamation=reclamation,
        type_notification='reclamation_rejetee',
        titre='Réclamation rejetée',
        message=f'Votre réclamation {reclamation.numero_reclamation} a été rejetée. {raison}',
    )
    
    return JsonResponse({'success': True, 'message': 'Document rejeté'})