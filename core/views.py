from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.conf import settings
import os

from .models import Signalement, Objet, Utilisateur, CommentaireAnonyme, Declaration, Conversation, Message
from .forms import SignalementForm, SearchForm, CommentaireAnonymeForm, DeclarationForm
from .decorators import role_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .forms import AdminForm  # formulaire qu’on va créer
from rest_framework import viewsets
from .models import Region, Prefecture, StructureLocale, Signalement
from .serializers import RegionSerializer, PrefectureSerializer, StructureLocaleSerializer, SignalementSerializer


from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test


class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer

# class PrefectureViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = Prefecture.objects.all()
#     serializer_class = PrefectureSerializer

class PrefectureViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PrefectureSerializer

    def get_queryset(self):
        queryset = Prefecture.objects.all()
        region_id = self.request.query_params.get('region', None)
        if region_id is not None:
            queryset = queryset.filter(region__id=region_id)
        return queryset


class StructureLocaleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StructureLocale.objects.all()
    serializer_class = StructureLocaleSerializer

class SignalementViewSet(viewsets.ModelViewSet):
    queryset = Signalement.objects.all()
    serializer_class = SignalementSerializer
User = get_user_model()

# ---------------------------
# Redirection selon rôle après login
# ---------------------------
@login_required
def home(request):
    if hasattr(request.user, 'role'):
        if request.user.role == 'admin':
            return redirect('togo_admin:dashboard')  # Interface admin
        elif request.user.role == 'agent':
            return redirect('togo_agent:dashboard')  # Interface agent
        else:
            return redirect('utilisateur_dashboard')
    elif request.user.is_staff:  # Admin Django classique
        return redirect('togo_admin:dashboard')
    else:
        return redirect('utilisateur_dashboard')

def home_redirect(request):
    user = request.user
    if user.is_authenticated:
        if hasattr(user, 'role'):
            if user.role == 'admin':
                return redirect('togo_admin:dashboard')
            elif user.role == 'agent':
                return redirect('togo_agent:dashboard')
            else:
                return redirect('utilisateur_dashboard')
        elif user.is_staff:  # Admin Django classique
            return redirect('togo_admin:dashboard')
    return redirect('index')

# ---------------------------
# Superadmin Views
# ---------------------------
# Admin Views
# ---------------------------
@login_required
@role_required(['admin'])
def admin_dashboard(request):
    # Filtre par région de l'utilisateur admin
    if request.user.region:
        signalements = Signalement.objects.filter(region=request.user.region)
    else:
        signalements = Signalement.objects.all()  # Si pas de région définie
    return render(request, 'admin/dashboard.html', {'signalements': signalements})

@login_required
@role_required(['admin'])
def admin_signalements(request):
    # Filtre par région de l'utilisateur admin
    if request.user.region:
        signalements = Signalement.objects.filter(region=request.user.region)
    else:
        signalements = Signalement.objects.all()
    return render(request, 'admin/signalements.html', {'signalements': signalements})

@login_required
@role_required(['admin'])
def admin_signalement_detail(request, pk):
    signalement = get_object_or_404(Signalement, pk=pk)
    return render(request, 'admin/signalement_detail.html', {'signalement': signalement})

# ---------------------------
# Utilisateur Views
# ---------------------------
@login_required
def utilisateur_dashboard(request):
    # Dashboard moderne avec statistiques basées sur le modèle Declaration
    mes_declarations = Declaration.objects.filter(declarant=request.user)
    declarations_recentes = mes_declarations.order_by('-date_declaration')[:5]
    
    # Enrichir avec les commentaires pour le dashboard
    for declaration in declarations_recentes:
        declaration.nb_commentaires = CommentaireAnonyme.objects.filter(declaration=declaration).count()
    
    # Récupérer les commentaires récents sur mes déclarations
    commentaires_recents = CommentaireAnonyme.objects.filter(
        declaration__declarant=request.user
    ).order_by('-date_creation')[:5]
    
    # Statistiques détaillées
    total_declarations = mes_declarations.count()
    objets_perdus = mes_declarations.filter(type_declaration='perdu').exclude(statut__in=['publie', 'restitue']).count()
    objets_trouves = mes_declarations.filter(Q(type_declaration='trouve') | Q(statut='publie')).count()
    objets_restitues = mes_declarations.filter(statut='restitue').count()
    total_commentaires = CommentaireAnonyme.objects.filter(declaration__declarant=request.user).count()
    
    context = {
        'total_declarations': total_declarations,
        'objets_perdus': objets_perdus,
        'objets_trouves': objets_trouves,
        'objets_restitues': objets_restitues,
        'total_commentaires': total_commentaires,
        'recent_declarations': declarations_recentes,
        'commentaires_recents': commentaires_recents,
    }
    return render(request, 'citoyen/dashboard.html', context)

@login_required
def utilisateur_notifications(request):
    """API pour récupérer les notifications de l'utilisateur (nouveaux commentaires et messages)"""
    from django.http import JsonResponse
    
    # Récupérer les commentaires récents (dernières 24h) sur les déclarations de l'utilisateur
    from datetime import datetime, timedelta
    depuis_24h = datetime.now() - timedelta(hours=24)
    
    notifications = []
    
    # 1. Nouveaux commentaires
    nouveaux_commentaires = CommentaireAnonyme.objects.filter(
        declaration__declarant=request.user,
        date_creation__gte=depuis_24h
    ).order_by('-date_creation')[:5]
    
    for commentaire in nouveaux_commentaires:
        notifications.append({
            'id': f'comment_{commentaire.id}',
            'type': 'nouveau_commentaire',
            'titre': f'Nouveau commentaire sur "{commentaire.declaration.nom_objet}"',
            'message': f'{commentaire.get_display_name()}: "{commentaire.contenu[:50]}..."',
            'url': f'/signalement/{commentaire.declaration.pk}/',
            'date': commentaire.date_creation.strftime('%d/%m à %H:%M'),
            'temps_ecoule': commentaire.date_creation,
            'icone': 'fa-comment',
            'couleur': 'blue'
        })
    
    # 2. Nouveaux messages des agents
    try:
        nouveaux_messages = Message.objects.filter(
            receiver=request.user,
            sender__role__in=['agent', 'admin'],
            created_at__gte=depuis_24h,
            is_read=False
        ).order_by('-created_at')[:5]
        
        for message in nouveaux_messages:
            notifications.append({
                'id': f'message_{message.id}',
                'type': 'nouveau_message',
                'titre': f'Message de {message.sender.get_full_name() or message.sender.username}',
                'message': message.contenu[:50] + ('...' if len(message.contenu) > 50 else ''),
                'url': f'/utilisateur/messagerie/conversation/{message.conversation.id}/',
                'date': message.created_at.strftime('%d/%m à %H:%M'),
                'temps_ecoule': message.created_at,
                'icone': 'fa-envelope',
                'couleur': 'green'
            })
    except Exception as e:
        # En cas d'erreur avec les messages, on continue avec juste les commentaires
        print(f"Erreur lors de la récupération des messages: {e}")
    
    # Trier toutes les notifications par date (plus récent en premier)
    notifications.sort(key=lambda x: x['temps_ecoule'], reverse=True)
    
    return JsonResponse({
        'notifications': notifications[:10],  # Limiter à 10 notifications
        'count': len(notifications),
        'unread_count': len(notifications)
    })

@login_required
def agent_notifications(request):
    """API pour récupérer les notifications de l'agent"""
    from django.http import JsonResponse
    
    # Vérifier que l'utilisateur est un agent
    if request.user.role not in ['agent', 'admin', 'superadmin']:
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    
    # Récupérer les notifications récentes (dernières 48h)
    from datetime import datetime, timedelta
    depuis_48h = datetime.now() - timedelta(hours=48)
    
    notifications = []
    
    # 1. Nouveaux messages des déclarants vers cet agent spécifiquement
    try:
        nouveaux_messages = Message.objects.filter(
            Q(receiver=request.user),  # Messages reçus par cet agent
            sender__role='citoyen',    # Envoyés par des citoyens
            created_at__gte=depuis_48h,
            is_read=False
        ).order_by('-created_at')[:10]
        
        for message in nouveaux_messages:
            notifications.append({
                'id': f'message_{message.id}',
                'type': 'nouveau_message_declarant',
                'titre': f'Message de {message.sender.get_full_name() or message.sender.username}',
                'message': f'Signalement: {message.conversation.signalement.nom_objet if hasattr(message, "conversation") and message.conversation and hasattr(message.conversation, "signalement") else "Message"} - "{message.contenu[:50]}..."',
                'url': f'/agent/chat/?conversation_id={message.conversation.id}' if hasattr(message, 'conversation') and message.conversation else '/agent/chat/',
                'date': message.created_at.strftime('%d/%m à %H:%M'),
                'temps_ecoule': message.created_at,
                'lu': False,
                'icone': 'fa-envelope',
                'couleur': 'green'
            })
    except Exception as e:
        print(f"Erreur lors de la récupération des messages agent: {e}")
    
    # 2. Nouveaux commentaires sur les signalements assignés à cet agent ou validés par lui
    try:
        nouveaux_commentaires = CommentaireAnonyme.objects.filter(
            Q(declaration__agent_validateur=request.user),  # Signalements assignés/validés par cet agent
            date_creation__gte=depuis_48h
        ).order_by('-date_creation')[:8]
        
        for commentaire in nouveaux_commentaires:
            notifications.append({
                'id': f'commentaire_{commentaire.id}',
                'type': 'nouveau_commentaire_signalement',
                'titre': f'Commentaire sur "{commentaire.declaration.nom_objet}"',
                'message': f'{commentaire.get_display_name()}: "{commentaire.contenu[:40]}..."',
                'url': f'/agent/signalement/{commentaire.declaration.pk}/',
                'date': commentaire.date_creation.strftime('%d/%m à %H:%M'),
                'temps_ecoule': commentaire.date_creation,
                'lu': False,
                'icone': 'fa-comment',
                'couleur': 'blue'
            })
    except Exception as e:
        print(f"Erreur lors de la récupération des commentaires: {e}")
    
    # Trier par date décroissante
    notifications.sort(key=lambda x: x['temps_ecoule'], reverse=True)
    
    # Limiter à 12 notifications max
    notifications = notifications[:12]
    
    return JsonResponse({
        'notifications': notifications,
        'count': len(notifications),
        'unread_count': len(notifications)
    })

@login_required
def agent_profil(request):
    """Page de profil de l'agent"""
    # Vérifier que l'utilisateur est un agent
    if request.user.role not in ['agent', 'admin', 'superadmin']:
        messages.error(request, "Accès non autorisé.")
        return redirect('login')
    
    if request.method == 'POST':
        # Traitement du formulaire de mise à jour du profil
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '')
        
        # Validation basique
        if first_name and last_name and email:
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.email = email
            request.user.save()
            messages.success(request, "Profil mis à jour avec succès.")
        else:
            messages.error(request, "Tous les champs sont obligatoires.")
    
    context = {
        'user': request.user,
        'title': 'Mon Profil',
        'subtitle': 'Gestion de vos informations personnelles'
    }
    return render(request, 'agent/profil.html', context)

@login_required 
def agent_parametres(request):
    """Page de paramètres de l'agent"""
    # Vérifier que l'utilisateur est un agent
    if request.user.role not in ['agent', 'admin', 'superadmin']:
        messages.error(request, "Accès non autorisé.")
        return redirect('login')
    
    if request.method == 'POST':
        # Traitement du changement de mot de passe
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if current_password and new_password and confirm_password:
            # Vérifier le mot de passe actuel
            if not request.user.check_password(current_password):
                messages.error(request, "Mot de passe actuel incorrect.")
            elif new_password != confirm_password:
                messages.error(request, "Les nouveaux mots de passe ne correspondent pas.")
            elif len(new_password) < 6:
                messages.error(request, "Le mot de passe doit contenir au moins 6 caractères.")
            else:
                request.user.set_password(new_password)
                request.user.save()
                messages.success(request, "Mot de passe modifié avec succès.")
    
    context = {
        'user': request.user,
        'title': 'Paramètres',
        'subtitle': 'Configuration de votre compte'
    }
    return render(request, 'agent/parametres.html', context)

@login_required
def agent_documents(request):
    """API pour récupérer les documents réellement échangés avec cet agent"""
    from django.http import JsonResponse
    
    # Vérifier que l'utilisateur est un agent
    if request.user.role not in ['agent', 'admin', 'superadmin']:
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    
    try:
        from datetime import datetime, timedelta
        depuis_30j = datetime.now() - timedelta(days=30)
        
        documents = []
        
        from core.models import PieceJustificative, Reclamation, Conversation, Message
        
        print(f"DEBUG: Recherche documents pour agent {request.user.username} (ID: {request.user.id})")
        
        # 1. Documents des réclamations assignées à cet agent
        pieces_reclamations = PieceJustificative.objects.filter(
            date_ajout__gte=depuis_30j,
            reclamation__agent_traitant=request.user
        ).select_related(
            'reclamation__reclamant', 
            'reclamation__declaration'
        ).order_by('-date_ajout')
        
        print(f"DEBUG: Trouvé {pieces_reclamations.count()} documents de réclamations assignées")
        
        # 2. Fichiers des conversations où cet agent participe
        conversations_agent = Conversation.objects.filter(agent=request.user)
        messages_avec_fichiers = Message.objects.filter(
            conversation__in=conversations_agent,
            fichier__isnull=False,
            created_at__gte=depuis_30j
        ).select_related('sender', 'conversation__declarant', 'conversation__signalement').order_by('-created_at')
        
        print(f"DEBUG: Trouvé {messages_avec_fichiers.count()} fichiers de conversations")
        
        # Traiter les documents de réclamations
        for piece in pieces_reclamations:
            try:
                # Déterminer l'icône selon le type de fichier
                nom_fichier = piece.nom_fichier or (piece.fichier.name.split('/')[-1] if piece.fichier else 'Document')
                extension = nom_fichier.lower().split('.')[-1] if '.' in nom_fichier else ''
                
                if extension == 'pdf':
                    icon, color = 'fa-file-pdf', 'text-red-600'
                elif extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    icon, color = 'fa-image', 'text-blue-600'
                elif extension in ['doc', 'docx']:
                    icon, color = 'fa-file-word', 'text-blue-800'
                else:
                    icon, color = 'fa-file', 'text-gray-600'
                    
                # Calculer la taille
                if piece.fichier and hasattr(piece.fichier, 'size'):
                    file_size = piece.fichier.size
                    size_display = f"{file_size/1024:.1f} KB" if file_size < 1024*1024 else f"{file_size/(1024*1024):.1f} MB"
                else:
                    size_display = "N/A"
                
                reclamant_nom = piece.reclamation.reclamant.get_full_name() or piece.reclamation.reclamant.username
                objet_nom = piece.reclamation.declaration.nom_objet
                
                documents.append({
                    'id': f"rec_{piece.id}",
                    'fileName': nom_fichier,
                    'type': piece.get_type_piece_display(),
                    'expediteur': reclamant_nom,
                    'objet': objet_nom,
                    'objetId': piece.reclamation.declaration.id,
                    'reclamationId': piece.reclamation.id,
                    'date': piece.date_ajout.strftime('%d/%m/%Y à %H:%M'),
                    'size': size_display,
                    'icon': icon,
                    'color': color,
                    'url': piece.fichier.url if piece.fichier else None,
                    'verifie': piece.verifie,
                    'agent_assigne': True,  # Toujours vrai pour les réclamations assignées
                    'source': 'réclamation'
                })
                
            except Exception as e:
                print(f"Erreur document réclamation {piece.id}: {e}")
                continue
        
        # Traiter les fichiers de conversations
        for message in messages_avec_fichiers:
            try:
                if not message.fichier:
                    continue
                
                nom_fichier = message.fichier.name.split('/')[-1]
                extension = nom_fichier.lower().split('.')[-1] if '.' in nom_fichier else ''
                
                if extension == 'pdf':
                    icon, color = 'fa-file-pdf', 'text-red-600'
                elif extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    icon, color = 'fa-image', 'text-blue-600'
                elif extension in ['doc', 'docx']:
                    icon, color = 'fa-file-word', 'text-blue-800'
                else:
                    icon, color = 'fa-file', 'text-gray-600'
                
                # Taille du fichier
                if hasattr(message.fichier, 'size'):
                    file_size = message.fichier.size
                    size_display = f"{file_size/1024:.1f} KB" if file_size < 1024*1024 else f"{file_size/(1024*1024):.1f} MB"
                else:
                    size_display = "N/A"
                
                expediteur_nom = message.sender.get_full_name() or message.sender.username if message.sender else "Système"
                objet_nom = message.conversation.signalement.nom_objet if message.conversation.signalement else "Conversation"
                
                documents.append({
                    'id': f"msg_{message.id}",
                    'fileName': nom_fichier,
                    'type': 'Fichier de conversation',
                    'expediteur': expediteur_nom,
                    'objet': objet_nom,
                    'objetId': message.conversation.signalement.id if message.conversation.signalement else None,
                    'conversationId': message.conversation.id,
                    'messageId': message.id,
                    'date': message.created_at.strftime('%d/%m/%Y à %H:%M'),
                    'size': size_display,
                    'icon': icon,
                    'color': color,
                    'url': message.fichier.url,
                    'verifie': message.is_read,
                    'agent_assigne': True,  # Toujours vrai pour les conversations de l'agent
                    'source': 'conversation'
                })
                
            except Exception as e:
                print(f"Erreur message {message.id}: {e}")
                continue
        
        # Trier tous les documents par date (plus récents d'abord)
        documents.sort(key=lambda d: datetime.strptime(d['date'], '%d/%m/%Y à %H:%M'), reverse=True)
        
        # Limiter à 20 documents
        documents = documents[:20]
        
        # Calculer les statistiques
        discussions_uniques = len(set([d['expediteur'] for d in documents]))
        documents_vus = len([d for d in documents if d['verifie']])
        
        print(f"DEBUG: Retour de {len(documents)} documents total ({discussions_uniques} discussions)")
        
        return JsonResponse({
            'documents': documents,
            'count': len(documents),
            'discussions_count': discussions_uniques,
            'vus_count': documents_vus,
            'success': True
        })
        
    except Exception as e:
        print(f"Erreur lors de la récupération des documents: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'documents': [],
            'count': 0, 
            'discussions_count': 0,
            'vus_count': 0,
            'error': f'Erreur serveur: {str(e)}',
            'success': False
        })

@login_required
def mes_signalements(request):
    """Page dédiée aux déclarations de l'utilisateur connecté"""
    declarations = Declaration.objects.filter(declarant=request.user).order_by('-date_declaration')
    
    # Filtres
    type_filter = request.GET.get('type', '')
    statut_filter = request.GET.get('statut', '')
    if type_filter:
        declarations = declarations.filter(type_declaration=type_filter)
    if statut_filter:
        declarations = declarations.filter(statut=statut_filter)
    
    # Enrichir avec les commentaires pour chaque déclaration
    declarations_avec_commentaires = []
    for declaration in declarations:
        commentaires = CommentaireAnonyme.objects.filter(declaration=declaration).order_by('-date_creation')
        declaration.nb_commentaires = commentaires.count()
        declaration.dernier_commentaire = commentaires.first() if commentaires.exists() else None
        declaration.nouveaux_commentaires = commentaires.filter(date_creation__gt=declaration.date_declaration).count()
        declarations_avec_commentaires.append(declaration)
    
    # Statistiques
    stats = {
        'total': declarations.count(),
        'perdus': declarations.filter(type_declaration='perdu').count(),
        'trouves': declarations.filter(type_declaration='trouve').count(),
        'retrouves': declarations.filter(statut='publie').count(),
        'restitues': declarations.filter(statut='restitue').count(),
        'total_commentaires': sum(d.nb_commentaires for d in declarations_avec_commentaires),
    }
    
    # Add boolean flags for template to avoid comparison syntax errors
    context = {
        'declarations': declarations_avec_commentaires,
        'stats': stats,
        'type_filter': type_filter,
        'statut_filter': statut_filter,
        # Boolean flags for type filters
        'is_perdu': type_filter == 'perdu',
        'is_trouve': type_filter == 'trouve',
        # Boolean flags for statut filters
        'is_cree': statut_filter == 'cree',
        'is_valide': statut_filter == 'valide',
        'is_publie': statut_filter == 'publie',
        'is_restitue': statut_filter == 'restitue',
    }
    return render(request, 'citoyen/mes_signalements.html', context)

@login_required
def utilisateur_signalement_detail(request, pk):
    signalement = get_object_or_404(Signalement, pk=pk)
    return render(request, 'utilisateur/signalement_detail.html', {'signalement': signalement})

# ---------------------------
# Pages publiques et recherche
# ---------------------------
def index(request):
    # Gestion de la recherche rapide depuis l'accueil
    nom = request.GET.get('nom')
    lieu = request.GET.get('lieu')
    date_perte = request.GET.get('date_perte')

    objets_resultats = []
    recherche_effectuee = False

    if nom or lieu or date_perte:
        recherche_effectuee = True
        # Recherche dans la table Declaration (élargie pour inclure les nouveaux signalements)
        base_search = Declaration.objects.filter(
            statut__in=['cree', 'en_validation', 'valide', 'publie'],
            visible_publiquement=True
        )
        if nom:
            base_search = base_search.filter(nom_objet__icontains=nom)
        if lieu:
            base_search = base_search.filter(
                Q(lieu_precis__icontains=lieu) |
                Q(prefecture__nom__icontains=lieu) |
                Q(region__nom__icontains=lieu)
            )
        if date_perte:
            base_search = base_search.filter(date_incident=date_perte)
        
        objets_resultats = base_search.select_related(
            'declarant', 'region', 'prefecture', 'categorie'
        ).order_by('-date_declaration')

    # Récupération des déclarations d'objets TROUVÉS (publiés)
    objets_trouves = Declaration.objects.filter(
        type_declaration='trouve',
        statut__in=['valide', 'publie'],
        visible_publiquement=True
    ).select_related('declarant', 'region', 'prefecture', 'categorie').order_by('-date_declaration')[:6]
    
    # Récupération des déclarations d'objets PERDUS (publiés)
    objets_perdus = Declaration.objects.filter(
        type_declaration='perdu',
        statut__in=['valide', 'publie'],
        visible_publiquement=True
    ).select_related('declarant', 'region', 'prefecture', 'categorie').order_by('-date_declaration')[:6]

    # Récupération des déclarations récentes (tous types confondus)
    signalements_recents = Declaration.objects.filter(
        statut__in=['cree', 'en_validation', 'valide', 'publie'],
        visible_publiquement=True
    ).select_related('declarant', 'region', 'prefecture', 'categorie').order_by('-date_declaration')[:4]

    # Statistiques pour l'affichage
    stats = {
        'total_objets': Declaration.objects.filter(statut__in=['valide', 'publie']).count(),
        'total_signalements': Declaration.objects.count(),
        'signalements_perdus': Declaration.objects.filter(type_declaration='perdu', statut__in=['valide', 'publie']).count(),
        'signalements_trouves': Declaration.objects.filter(type_declaration='trouve', statut__in=['valide', 'publie']).count(),
    }

    return render(request, 'index.html', {
        'objets_resultats': objets_resultats,
        'objets_trouves': objets_trouves,  # Déclarations d'objets trouvés
        'objets_perdus': objets_perdus,    # Déclarations d'objets perdus
        'signalements_recents': signalements_recents,  # Toutes déclarations récentes
        'recherche_effectuee': recherche_effectuee,
        'stats': stats,
    })

def search_objets(request):
    form = SearchForm(request.GET or None)
    objets = Objet.objects.all()
    if form.is_valid():
        nom = form.cleaned_data.get('nom')
        lieu = form.cleaned_data.get('lieu')
        date_perte = form.cleaned_data.get('date_perte')
        if nom:
            objets = objets.filter(nom__icontains=nom)
        if lieu:
            objets = objets.filter(lieu__icontains=lieu)
        if date_perte:
            objets = objets.filter(date_perte=date_perte)
    return render(request, 'search.html', {'form': form, 'objets': objets})

def objet_detail(request, pk):
    objet = get_object_or_404(Objet, pk=pk)
    return render(request, 'objet_detail.html', {'objet': objet})

def declaration_detail_public(request, pk):
    """Vue publique pour afficher le détail d'une déclaration"""
    declaration = get_object_or_404(
        Declaration, 
        pk=pk,
        statut__in=['valide', 'publie'],
        visible_publiquement=True
    )
    
    # Incrémenter le nombre de vues
    declaration.nombre_vues += 1
    declaration.save(update_fields=['nombre_vues'])
    
    # Récupérer les commentaires anonymes
    commentaires = CommentaireAnonyme.objects.filter(
        declaration=declaration,
        est_approuve=True
    ).order_by('-date_creation')
    
    # Formulaire pour ajouter un commentaire anonyme
    if request.method == 'POST':
        form = CommentaireAnonymeForm(request.POST)
        if form.is_valid():
            commentaire = form.save(commit=False)
            commentaire.declaration = declaration
            # Capturer l'IP de l'utilisateur
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                commentaire.ip_address = x_forwarded_for.split(',')[0]
            else:
                commentaire.ip_address = request.META.get('REMOTE_ADDR')
            commentaire.save()
            messages.success(request, "💬 Votre commentaire a été ajouté avec succès !")
            return redirect('declaration_detail', pk=pk)
        else:
            messages.error(request, "❌ Erreur lors de l'ajout du commentaire.")
    else:
        form = CommentaireAnonymeForm()
    
    context = {
        'declaration': declaration,
        'signalement': declaration,  # Alias pour compatibilité template
        'commentaires': commentaires,
        'form': form,
        'nb_commentaires': commentaires.count()
    }
    
    return render(request, 'declaration_detail_public.html', context)

# ---------------------------
# Gestion des signalements
# ---------------------------
def signalements_list(request):
    # Récupérer les paramètres de recherche
    query = request.GET.get('q')
    type_filter = request.GET.get('type')
    date_perte = request.GET.get('date_perte')
    
    # On filtre les signalements qui sont soit créés, soit validés, soit publiés
    base_queryset = Declaration.objects.filter(
        statut__in=['cree', 'valide', 'publie']
    ).select_related('declarant', 'prefecture', 'structure_locale', 'region').order_by('-date_declaration')

    if query:
        base_queryset = base_queryset.filter(
            Q(nom_objet__icontains=query) |
            Q(description__icontains=query) |
            Q(lieu_precis__icontains=query) |
            Q(prefecture__nom__icontains=query) |
            Q(region__nom__icontains=query)
        )
    
    if type_filter in ['perdu', 'trouve']:
        base_queryset = base_queryset.filter(type_declaration=type_filter)
        
    if date_perte:
        base_queryset = base_queryset.filter(date_incident=date_perte)
    
    context = {
        'signalements': base_queryset,
        'query': query,
        'type_filter': type_filter,
        'date_perte': date_perte,
        'total_count': base_queryset.count(),
    }
    return render(request, 'signalements_list_final.html', context)

def signalement_detail(request, pk):
    signalement = get_object_or_404(Declaration, pk=pk)
    
    # Récupérer les commentaires anonymes pour ce signalement
    commentaires = CommentaireAnonyme.objects.filter(declaration=signalement).order_by('-date_creation')
    
    # Formulaire pour ajouter un commentaire anonyme
    if request.method == 'POST':
        form = CommentaireAnonymeForm(request.POST)
        if form.is_valid():
            commentaire = form.save(commit=False)
            commentaire.declaration = signalement
            commentaire.save()
            messages.success(request, "💬 Votre commentaire a été ajouté avec succès !")
            return redirect('signalement_detail', pk=pk)
        else:
            # Afficher les erreurs spécifiques du formulaire
            for field, errors in form.errors.items():
                for error in errors:
                    if field == 'contenu':
                        messages.error(request, f"❌ Commentaire : {error}")
                    else:
                        messages.error(request, f"❌ {field.capitalize()} : {error}")
    else:
        form = CommentaireAnonymeForm()
    
    photos_supplementaires = signalement.photos_supplementaires.all()
    context = {
        'signalement': signalement,
        'commentaires': commentaires,
        'form': form,
        'nb_commentaires': commentaires.count(),
        'photos_supplementaires': photos_supplementaires,
    }
    return render(request, 'signalement_detail.html', context)

# Function to add signalement - Updated to use Declaration model
def signalement_add(request):
    regions = Region.objects.all()
    if request.method == 'POST':
        # DEBUG: Afficher les coordonnées GPS reçues
        print(f"🔍 DEBUG GPS - Latitude reçue: {request.POST.get('latitude', 'NON REÇUE')}")
        print(f"🔍 DEBUG GPS - Longitude reçue: {request.POST.get('longitude', 'NON REÇUE')}")
        print(f"🔍 DEBUG GPS - Tous les champs POST: {list(request.POST.keys())}")
        
        form = DeclarationForm(request.POST, request.FILES)
        if form.is_valid():
            # DEBUG: Afficher les données nettoyées du formulaire
            print(f"✅ DEBUG GPS - Latitude dans form.cleaned_data: {form.cleaned_data.get('latitude', 'NON PRÉSENTE')}")
            print(f"✅ DEBUG GPS - Longitude dans form.cleaned_data: {form.cleaned_data.get('longitude', 'NON PRÉSENTE')}")
            
            # Créer une déclaration avec le nouveau formulaire
            declaration = form.save(commit=False)

            # --- FIX GPS START ---
            # Force la récupération des coordonnées depuis POST car le formulaire semble les ignorer
            lat_raw = request.POST.get('latitude')
            lon_raw = request.POST.get('longitude')
            
            if lat_raw and str(lat_raw).strip():
                try:
                    # Conversion manuelle sécurisée
                    from decimal import Decimal
                    # Remplacer la virgule par un point si nécessaire (gestion locale)
                    declaration.latitude = Decimal(str(lat_raw).replace(',', '.'))
                except Exception:
                    pass

            if lon_raw and str(lon_raw).strip():
                try:
                    from decimal import Decimal
                    declaration.longitude = Decimal(str(lon_raw).replace(',', '.'))
                except Exception:
                    pass
            # --- FIX GPS END ---

            if request.user.is_authenticated:
                declaration.declarant = request.user
                # Le type_declaration vient maintenant du formulaire
                declaration.statut = 'cree'  # État initial
            else:
                messages.error(request, "❌ Vous devez être connecté pour signaler un objet.")
                return redirect('login')

            # Récupérer les données géographiques si elles sont fournies
            region_id = request.POST.get('region')
            prefecture_id = request.POST.get('prefecture')
            structure_id = request.POST.get('structure_locale')

            if region_id:
                try:
                    declaration.region = Region.objects.get(id=region_id)
                except Region.DoesNotExist:
                    pass

            if prefecture_id:
                try:
                    declaration.prefecture = Prefecture.objects.get(id=prefecture_id)
                except Prefecture.DoesNotExist:
                    pass

            if structure_id:
                try:
                    declaration.structure_locale = StructureLocale.objects.get(id=structure_id)
                    # Assigner automatiquement la région et préfecture depuis la structure
                    if declaration.structure_locale:
                        declaration.prefecture = declaration.structure_locale.prefecture
                        declaration.region = declaration.structure_locale.prefecture.region
                except StructureLocale.DoesNotExist:
                    pass

            # Correction : prise en compte de l'image principale si uploadée
            if 'photo_principale' in request.FILES:
                declaration.photo_principale = request.FILES['photo_principale']

            try:
                declaration.save()
                # DEBUG: Vérifier si les coordonnées ont été sauvegardées
                print(f"💾 DEBUG GPS - Déclaration sauvegardée avec:")
                print(f"   - Latitude: {declaration.latitude}")
                print(f"   - Longitude: {declaration.longitude}")
                
                messages.success(request, "✅ Déclaration ajoutée avec succès !")
                return redirect('signalements_list')

            except Exception as e:
                # Log de l'erreur pour debug
                print(f"❌ Erreur lors de la sauvegarde: {e}")
                # Si c'est une erreur d'unicité sur numero_declaration, régénérer
                if 'UNIQUE constraint failed: core_declaration.numero_declaration' in str(e):
                    try:
                        # Forcer la régénération du numéro
                        declaration.numero_declaration = None
                        declaration.save()
                        messages.success(request, "✅ Déclaration ajoutée avec succès !")
                        return redirect('signalements_list')
                    except Exception as e2:
                        print(f"❌ Erreur lors de la seconde tentative: {e2}")
                        messages.error(request, f"❌ Erreur technique lors de l'ajout: {str(e2)}")
                else:
                    messages.error(request, f"❌ Erreur lors de l'ajout: {str(e)}")
        else:
            # Log des erreurs pour le debug
            print("❌ Erreurs formulaire:", form.errors)
            print("❌ Erreurs non-field:", form.non_field_errors())
            
            # Messages d'erreur détaillés pour l'utilisateur
            if form.errors:
                for field, errors in form.errors.items():
                    field_name = form.fields[field].label if field in form.fields else field
                    for error in errors:
                        messages.error(request, f"❌ {field_name}: {error}")
            else:
                messages.error(request, "❌ Erreur lors de l'ajout de la déclaration.")
    else:
        form = DeclarationForm()

    return render(request, 'signalement_add.html', {
        'form': form,
        'regions': regions
    })


def signalement_edit(request, pk):
    from .models import Declaration
    try:
        signalement = Declaration.objects.get(pk=pk)
    except Declaration.DoesNotExist:
        messages.error(request, "Signalement introuvable.")
        return redirect('signalements_list')
    if signalement.statut != 'cree':
        messages.error(request, "Ce signalement ne peut plus être modifié car il a déjà été traité.")
        return redirect('signalement_detail', pk=signalement.pk)
    from .forms import DeclarationForm
    if request.method == 'POST':
        form = DeclarationForm(request.POST, request.FILES, instance=signalement)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Signalement modifié avec succès !")
            return redirect('signalement_detail', pk=signalement.pk)
        else:
            messages.error(request, "❌ Erreur lors de la modification.")
    else:
        form = DeclarationForm(instance=signalement)
    return render(request, 'signalement_edit.html', {'form': form, 'signalement': signalement})

def signalement_delete(request, pk):
    from .models import Declaration
    signalement = get_object_or_404(Declaration, pk=pk)
    if request.user != signalement.declarant:
        messages.error(request, "Vous n'avez pas l'autorisation de supprimer ce signalement.")
        return redirect('signalement_detail', pk=pk)
    if request.method == 'POST':
        signalement.delete()
        messages.warning(request, "🗑️ Signalement supprimé avec succès.")
        return redirect('signalements_list')
    return render(request, 'signalement_delete.html', {'signalement': signalement})

# ---------------------------
# Liste des objets
# ---------------------------
def objets_list(request):
    """Vue pour afficher tous les objets trouvés"""
    nom = request.GET.get('nom')
    lieu = request.GET.get('lieu')
    date_perte = request.GET.get('date_perte')
    
    base_queryset = Declaration.objects.filter(
        Q(
            # Objets trouvés à l'origine (seulement les validés, pas les restitués)
            (Q(type_declaration='trouve') & Q(statut__in=['valide', 'publie', 'cree'])) |
            # Objets perdus qui ont été retrouvés (pas les restitués)
            (Q(type_declaration='perdu') & Q(statut__in=['publie']))
        )
    ).select_related('declarant', 'prefecture', 'structure_locale', 'region').order_by('-date_declaration')

    if nom:
        base_queryset = base_queryset.filter(nom_objet__icontains=nom)
    if lieu:
        base_queryset = base_queryset.filter(
            Q(lieu_precis__icontains=lieu) |
            Q(prefecture__nom__icontains=lieu) |
            Q(region__nom__icontains=lieu)
        )
    if date_perte:
        base_queryset = base_queryset.filter(date_incident=date_perte)
    
    context = {
        'objets_trouves': base_queryset,
        'nom': nom,
        'lieu': lieu,
        'date_perte': date_perte,
        'total_count': base_queryset.count(),
    }
    return render(request, 'objets_list_new.html', context)

def objets_perdus_list(request):
    """Vue pour afficher tous les objets perdus qui ne sont pas encore retrouvés"""
    nom = request.GET.get('nom')
    lieu = request.GET.get('lieu')
    date_perte = request.GET.get('date_perte')
    
    base_queryset = Declaration.objects.filter(
        type_declaration='perdu',
        statut__in=['cree', 'en_validation', 'valide']  # Exclure 'publie' (retrouvé) et 'restitue'
    ).select_related('declarant', 'prefecture', 'structure_locale', 'region').order_by('-date_declaration')

    if nom:
        base_queryset = base_queryset.filter(nom_objet__icontains=nom)
    if lieu:
        base_queryset = base_queryset.filter(
            Q(lieu_precis__icontains=lieu) |
            Q(prefecture__nom__icontains=lieu) |
            Q(region__nom__icontains=lieu)
        )
    if date_perte:
        base_queryset = base_queryset.filter(date_incident=date_perte)
    
    context = {
        'objets_perdus': base_queryset,
        'nom': nom,
        'lieu': lieu,
        'date_perte': date_perte,
        'total_count': base_queryset.count(),
    }
    return render(request, 'objets_perdus_list_new.html', context)

def objets_recents(request):
    objets = Objet.objects.order_by('-date_creation')[:6]
    return render(request, 'home.html', {'objets': objets})

# ---------------------------
# Liste des utilisateurs
# ---------------------------
def utilisateurs_list(request):
    utilisateurs = Utilisateur.objects.all()
    return render(request, 'utilisateurs_list.html', {'utilisateurs': utilisateurs})

# ---------------------------
# Authentification
# ---------------------------
def login_view(request):
    # Forcer la régénération du token CSRF si nécessaire
    from django.middleware.csrf import get_token
    get_token(request)  # Force la création d'un nouveau token
    
    if request.method == 'POST':
        # Supporter la saisie par nom d'utilisateur ou par email
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username_or_email or not password:
            messages.error(request, "Veuillez remplir tous les champs.")
            return render(request, 'login.html')
            
        # Si l'utilisateur a fourni un email, on essaie de le résoudre en username
        username = username_or_email
        if username_or_email and '@' in username_or_email:
            try:
                u = User.objects.get(email__iexact=username_or_email)
                username = u.username
            except User.DoesNotExist:
                # On laisse la valeur fournie (peut être un username contenant '@')
                username = username_or_email

        user = authenticate(request, username=username, password=password)
        if user:
            if not user.is_active:
                messages.error(request, "Votre compte est désactivé. Contactez un administrateur.")
                return render(request, 'login.html')
                
            login(request, user)
            messages.success(request, f"Bienvenue {user.username} !")
            
            # Redirection intelligente selon le rôle avec diagnostics
            print(f"DEBUG: User {user.username} - role: {user.role}, is_staff: {user.is_staff}, is_superuser: {user.is_superuser}")
            
            if hasattr(user, 'role') and user.role == 'admin':
                print(f"DEBUG: Redirecting {user.username} to admin dashboard")
                return redirect('togo_admin:dashboard')  
            elif hasattr(user, 'role') and user.role == 'agent':
                print(f"DEBUG: Redirecting {user.username} to agent dashboard")
                return redirect('togo_agent:dashboard')
            elif user.is_staff:  # Admin Django classique
                print(f"DEBUG: Redirecting {user.username} to admin dashboard (staff)")
                return redirect('togo_admin:dashboard')
            else:
                print(f"DEBUG: Redirecting {user.username} to home")
                return redirect('home')  # Utilisateurs normaux
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
            
    return render(request, 'login.html')

def debug_login_view(request):
    """Vue de debug temporaire pour diagnostiquer les problèmes CSRF"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        print(f"DEBUG: Username: {username}")
        print(f"DEBUG: CSRF Token in POST: {request.POST.get('csrfmiddlewaretoken', 'MANQUANT')}")
        print(f"DEBUG: Session key: {request.session.session_key}")
        
        if not username or not password:
            messages.error(request, "Veuillez remplir tous les champs.")
            return render(request, 'debug_login.html')
            
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f"✅ Connexion réussie! Bienvenue {user.username}")
            
            # Affichage des informations utilisateur pour debug
            print(f"DEBUG: User authenticated - {user.username}")
            print(f"  - role: {getattr(user, 'role', 'Non défini')}")
            print(f"  - is_staff: {user.is_staff}")
            print(f"  - is_superuser: {user.is_superuser}")
            print(f"  - is_active: {user.is_active}")
            
            # Redirection intelligente selon le rôle
            if hasattr(user, 'role') and user.role == 'admin':
                return redirect('togo_admin:dashboard')
            else:
                return redirect('home')
        else:
            messages.error(request, "❌ Nom d'utilisateur ou mot de passe incorrect.")
            
    return render(request, 'debug_login.html')

def logout_view(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect('home')


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def ajouter_commentaire_ajax(request, signalement_id):
    """Vue AJAX pour ajouter un commentaire anonyme"""
    if request.method == 'POST':
        try:
            signalement = get_object_or_404(Signalement, id=signalement_id)
            
            # Parser les données JSON
            data = json.loads(request.body)
            
            # Créer le commentaire
            commentaire = CommentaireAnonyme.objects.create(
                signalement=signalement,
                pseudo=data.get('pseudo', ''),
                commentaire=data.get('commentaire', ''),
                contact=data.get('contact', '')
            )
            
            # Retourner la réponse JSON
            return JsonResponse({
                'success': True,
                'commentaire': {
                    'id': commentaire.id,
                    'pseudo': commentaire.get_display_name(),
                    'commentaire': commentaire.commentaire,
                    'date': commentaire.date_creation.strftime('%d/%m/%Y à %H:%M')
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return redirect('register')
        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur existe déjà.")
            return redirect('register')
        if User.objects.filter(email=email).exists():
            messages.error(request, "Un compte utilise déjà cet e-mail.")
            return redirect('register')

        user = User.objects.create_user(username=username, email=email, password=password1)
        user.save()
        login(request, user)
        messages.success(request, f"Bienvenue {user.username} 👋 Votre compte a été créé avec succès.")
        return redirect('home')

    return render(request, 'register.html')


# =============================================================================
# VUES UTILISATEUR SUPPLÉMENTAIRES
# =============================================================================

@login_required
def utilisateur_profil(request):
    """Vue pour gérer le profil utilisateur"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_profile':
            # Mise à jour des informations personnelles
            user = request.user
            user.username = request.POST.get('username', user.username)
            user.email = request.POST.get('email', user.email)
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.save()
            
            messages.success(request, "✅ Vos informations ont été mises à jour avec succès.")
            return redirect('utilisateur_profil')
            
        elif action == 'change_password':
            # Changement de mot de passe
            from django.contrib.auth import update_session_auth_hash
            from django.contrib.auth.forms import PasswordChangeForm
            
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)  # Important!
                messages.success(request, "🔒 Votre mot de passe a été changé avec succès.")
                return redirect('utilisateur_profil')
            else:
                for error in form.errors.values():
                    messages.error(request, error[0])
                return redirect('utilisateur_profil')
    
    # Calcul des statistiques utilisateur
    user_declarations = Declaration.objects.filter(declarant=request.user)
    stats = {
        'total': user_declarations.count(),
        'perdus': user_declarations.filter(type_declaration='perdu').exclude(statut__in=['publie', 'restitue']).count(),
        'trouves': user_declarations.filter(Q(type_declaration='trouve') | Q(statut='publie')).count(),
        'restitues': user_declarations.filter(statut='restitue').count(),
    }
    
    # Calcul du taux de réussite
    if stats['total'] > 0:
        stats['taux_reussite'] = round((stats['restitues'] / stats['total']) * 100, 1)
    else:
        stats['taux_reussite'] = 0
    
    context = {
        'stats': stats
    }
    
    return render(request, 'citoyen/profil.html', context)


@login_required 
def utilisateur_parametres(request):
    """Vue pour gérer les paramètres utilisateur"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_notifications':
            # Mise à jour des préférences de notifications
            # Ici vous pourriez sauvegarder dans un modèle UserPreferences
            messages.success(request, "🔔 Vos préférences de notifications ont été sauvegardées.")
            
        elif action == 'update_privacy':
            # Mise à jour des préférences de confidentialité
            messages.success(request, "🔒 Vos paramètres de confidentialité ont été mis à jour.")
            
        elif action == 'update_location':
            # Mise à jour des paramètres de localisation
            messages.success(request, "📍 Vos paramètres de localisation ont été sauvegardés.")
            
        elif action == 'update_interface':
            # Mise à jour des préférences d'interface
            messages.success(request, "🎨 Vos préférences d'interface ont été appliquées.")
        
        return redirect('utilisateur_parametres')
    
    return render(request, 'utilisateur/parametres.html')


# ===== API ENDPOINTS POUR LES STRUCTURES =====

def api_prefectures(request):
    """API pour récupérer les préfectures d'une région"""
    region_id = request.GET.get('region')
    if not region_id:
        return JsonResponse([], safe=False)
    
    try:
        prefectures = Prefecture.objects.filter(
            region_id=region_id
        ).values('id', 'nom').order_by('nom')
        return JsonResponse(list(prefectures), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def api_structures(request):
    """API pour récupérer les structures locales d'une préfecture"""
    prefecture_id = request.GET.get('prefecture')
    if not prefecture_id:
        return JsonResponse([], safe=False)
    
    try:
        structures = StructureLocale.objects.filter(
            prefecture_id=prefecture_id,
            actif=True
        ).values('id', 'nom', 'type_structure').order_by('nom')
        
        # Formater le nom avec le type pour plus de clarté
        result = []
        for structure in structures:
            result.append({
                'id': structure['id'],
                'nom': f"{structure['nom']} ({structure['type_structure'].title()})"
            })
        
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def signalements_map_data(request):
    """API pour récupérer les données de géolocalisation des signalements"""
    try:
        # Récupérer les paramètres de recherche
        query = request.GET.get('q')
        type_filter = request.GET.get('type')
        date_perte = request.GET.get('date_perte')

        signalements = Declaration.objects.filter(
            visible_publiquement=True,
            statut__in=['cree', 'publie', 'valide']  # Inclure aussi 'cree' pour les nouveaux signalements
        ).exclude(
            latitude__isnull=True
        ).exclude(
            longitude__isnull=True
        ).select_related('declarant', 'region', 'prefecture')

        # Appliquer les filtres
        if query:
            signalements = signalements.filter(
                Q(nom_objet__icontains=query) |
                Q(description__icontains=query) |
                Q(lieu_precis__icontains=query) |
                Q(prefecture__nom__icontains=query) |
                Q(region__nom__icontains=query)
            )
        
        if type_filter in ['perdu', 'trouve']:
            signalements = signalements.filter(type_declaration=type_filter)
            
        if date_perte:
            signalements = signalements.filter(date_incident=date_perte)
        
        data = [{
            'id': s.id,
            'nom_objet': s.nom_objet,
            'latitude': float(s.latitude),
            'longitude': float(s.longitude),
            'type_declaration': s.type_declaration,
            'date_incident': s.date_incident.isoformat(),
            'lieu_precis': s.lieu_precis,
            'numero_declaration': s.numero_declaration,
            'photo_url': s.photo_principale.url if s.photo_principale else None,
        } for s in signalements]
        
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def api_envoyer_message(request):
    """API pour envoyer un message dans une conversation"""
    if request.method == 'POST':
        import json
        
        try:
            data = json.loads(request.body)
            conversation_id = data.get('conversation_id')
            contenu = data.get('contenu', '').strip()
            
            if not contenu:
                return JsonResponse({'error': 'Le message ne peut pas être vide'}, status=400)
            
            # Vérifier que la conversation appartient à l'utilisateur
            try:
                conversation = Conversation.objects.get(
                    id=conversation_id,
                    declarant=request.user
                )
            except Conversation.DoesNotExist:
                return JsonResponse({'error': 'Conversation introuvable'}, status=404)
            
            # Créer le message
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                receiver=conversation.agent,
                contenu=contenu,
                type_message='texte',
                is_read=False
            )
            
            # Mettre à jour la conversation
            conversation.updated_at = message.created_at
            conversation.save()
            
            return JsonResponse({
                'success': True,
                'message': {
                    'id': message.id,
                    'contenu': message.contenu,
                    'expediteur': message.sender.get_full_name() or message.sender.username,
                    'date_envoi': message.created_at.strftime('%H:%M'),
                    'is_from_user': True
                }
            })
            
        except Conversation.DoesNotExist:
            print(f"❌ Conversation {conversation_id} non trouvée pour l'utilisateur {request.user.username}")
            return JsonResponse({'error': 'Conversation introuvable'}, status=404)
        except json.JSONDecodeError:
            print(f"❌ Erreur JSON dans la requête")
            return JsonResponse({'error': 'Données JSON invalides'}, status=400)
        except Exception as e:
            print(f"❌ Erreur envoi message: {e}")
            return JsonResponse({'error': f'Erreur serveur: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


@login_required
def api_messages_conversation(request, conversation_id):
    """API pour récupérer les messages d'une conversation"""
    if request.method == 'GET':
        try:
            # Vérifier que la conversation appartient à l'utilisateur
            conversation = Conversation.objects.get(
                id=conversation_id,
                declarant=request.user
            )
            
            # Récupérer les messages
            messages = conversation.messages.select_related(
                'sender', 'receiver'
            ).order_by('created_at')
            
            # Marquer les messages reçus comme lus
            Message.objects.filter(
                conversation=conversation,
                receiver=request.user,
                is_read=False
            ).update(is_read=True)
            
            # Préparer les données
            messages_data = []
            for message in messages:
                msg_data = {
                    'id': message.id,
                    'contenu': message.contenu,
                    'expediteur': message.sender.get_full_name() or message.sender.username,
                    'is_from_user': message.sender == request.user,
                    'date_envoi': message.created_at.strftime('%H:%M'),
                    'is_read': message.is_read,
                    'created_at': message.created_at.isoformat(),
                    'type_message': message.type_message
                }
                
                # Ajouter les informations de fichier si nécessaire
                if message.type_message == 'fichier' and message.fichier:
                    msg_data['file_url'] = settings.MEDIA_URL + str(message.fichier)
                    msg_data['file_name'] = os.path.basename(str(message.fichier))
                    
                messages_data.append(msg_data)
            
            return JsonResponse({
                'success': True,
                'messages': messages_data,
                'conversation': {
                    'id': conversation.id,
                    'agent_name': conversation.agent.get_full_name() or conversation.agent.username if conversation.agent else 'Support',
                    'status': 'active'  # Par défaut
                }
            })
            
        except Conversation.DoesNotExist:
            return JsonResponse({'error': 'Conversation introuvable'}, status=404)
        except Exception as e:
            print(f"❌ Erreur API messages: {e}")
            return JsonResponse({'error': f'Erreur serveur: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


@login_required
def api_upload_file(request):
    """API pour uploader un fichier dans une conversation"""
    if request.method == 'POST':
        import os
        from django.conf import settings
        from django.core.files.storage import default_storage
        
        try:
            conversation_id = request.POST.get('conversation_id')
            uploaded_file = request.FILES.get('file')
            
            if not uploaded_file:
                return JsonResponse({'error': 'Aucun fichier fourni'}, status=400)
                
            if not conversation_id:
                return JsonResponse({'error': 'ID de conversation manquant'}, status=400)
            
            # Vérifier que la conversation appartient à l'utilisateur
            try:
                conversation = Conversation.objects.get(
                    id=conversation_id,
                    declarant=request.user
                )
            except Conversation.DoesNotExist:
                return JsonResponse({'error': 'Conversation introuvable'}, status=404)
            
            # Vérifier la taille du fichier (10MB max)
            if uploaded_file.size > 10 * 1024 * 1024:
                return JsonResponse({'error': 'Fichier trop volumineux (max 10MB)'}, status=400)
            
            # Vérifier le type de fichier
            allowed_types = [
                'image/jpeg', 'image/png', 'image/gif', 'image/webp',
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'text/plain'
            ]
            
            if uploaded_file.content_type not in allowed_types:
                return JsonResponse({'error': 'Type de fichier non autorisé'}, status=400)
            
            # Créer le répertoire si nécessaire
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'chat_files')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Générer un nom de fichier unique
            import uuid
            file_extension = os.path.splitext(uploaded_file.name)[1]
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            file_path = os.path.join('chat_files', unique_filename)
            
            # Sauvegarder le fichier
            saved_path = default_storage.save(file_path, uploaded_file)
            
            # Créer le message avec fichier
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                receiver=conversation.agent,
                contenu=f"Fichier envoyé: {uploaded_file.name}",
                type_message='fichier',
                fichier=saved_path,
                is_read=False
            )
            
            # Mettre à jour la conversation
            conversation.updated_at = message.created_at
            conversation.save()
            
            # URL du fichier
            file_url = settings.MEDIA_URL + saved_path
            
            return JsonResponse({
                'success': True,
                'message': {
                    'id': message.id,
                    'contenu': message.contenu,
                    'file_name': uploaded_file.name,
                    'file_url': file_url,
                    'file_type': uploaded_file.content_type,
                    'date_envoi': message.created_at.strftime('%H:%M'),
                    'is_from_user': True
                }
            })
            
        except Exception as e:
            print(f"❌ Erreur upload fichier: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': f'Erreur serveur: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


# ==== FONCTIONS DE TEST ====


@login_required
def messagerie(request):
    """Vue pour l'interface de messagerie citoyenne"""
    try:
        # Récupérer toutes les conversations du citoyen connecté
        conversations = Conversation.objects.filter(
            declarant=request.user
        ).select_related('agent', 'signalement').prefetch_related(
            'messages__sender', 'messages__receiver'
        ).order_by('-updated_at')
        
        # Si aucune conversation n'existe, créer une conversation par défaut avec un agent
        if not conversations.exists():
            # Trouver un agent disponible (staff ou superuser)
            agent = Utilisateur.objects.filter(
                is_staff=True
            ).first()
            
            if not agent:
                # Créer un agent par défaut si aucun n'existe
                agent = Utilisateur.objects.create_user(
                    username='agent_support',
                    first_name='Agent',
                    last_name='Support',
                    email='support@togoretrouve.com',
                    is_staff=True
                )
                agent.set_password('agent123')
                agent.save()
                print(f"ℹ️ Agent par défaut créé: {agent.username}")
            
            # Créer une conversation par défaut (sans signalement spécifique)
            conversation = Conversation.objects.create(
                declarant=request.user,
                agent=agent,
                signalement=None  # Support général
            )
            
            # Message de bienvenue automatique
            Message.objects.create(
                conversation=conversation,
                sender=agent,
                receiver=request.user,
                contenu=f"Bonjour {request.user.get_full_name() or request.user.username} ! 👋\n\nBienvenue dans votre espace de messagerie. Je suis là pour vous aider avec toutes vos questions concernant vos déclarations d'objets trouvés ou perdus.\n\nN'hésitez pas à me poser toutes vos questions !",
                type_message='texte',
                is_read=False
            )
            
            # Recharger les conversations
            conversations = Conversation.objects.filter(
                declarant=request.user
            ).select_related('agent', 'signalement').prefetch_related(
                'messages__sender', 'messages__receiver'
            ).order_by('-updated_at')
        
        # Conversation active (la première par défaut)
        conversation_active = conversations.first() if conversations.exists() else None
        messages = []
        
        if conversation_active:
            # Récupérer tous les messages de la conversation active
            messages = conversation_active.messages.select_related(
                'sender', 'receiver'
            ).order_by('created_at')
            
            # Marquer les messages reçus comme lus
            Message.objects.filter(
                conversation=conversation_active,
                receiver=request.user,
                is_read=False
            ).update(is_read=True)
        
        context = {
            'conversations': conversations,
            'conversation_active': conversation_active,
            'messages': messages,
        }
        
    except Exception as e:
        import traceback
        print(f"❌ Erreur messagerie: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        # En cas d'erreur, afficher un message d'erreur
        context = {
            'conversations': [],
            'conversation_active': None,
            'messages': [],
            'error_message': f'Problème de chargement de la messagerie: {str(e)}',
        }
    
    return render(request, 'citoyen/messagerie.html', context)


# Vue de debug pour la messagerie
@login_required 
def test_messagerie_debug(request):
    """Vue de débogage pour la messagerie"""
    try:
        user = request.user
        print(f"🧪 Test pour l'utilisateur: {user.username}")
        
        # Test 1: Vérifier les conversations existantes
        conversations = Conversation.objects.filter(declarant=user)
        print(f"📊 Conversations trouvées: {conversations.count()}")
        
        # Test 2: Créer une conversation de test si nécessaire
        if not conversations.exists():
            # Créer/trouver un agent
            agent = Utilisateur.objects.filter(is_staff=True).first()
            if not agent:
                agent = Utilisateur.objects.create_user(
                    username='test_agent',
                    first_name='Test',
                    last_name='Agent',
                    is_staff=True
                )
                agent.set_password('test123')
                agent.save()
                print(f"✅ Agent créé: {agent.username}")
            
            # Créer conversation
            conversation = Conversation.objects.create(
                declarant=user,
                agent=agent
            )
            print(f"✅ Conversation créée: {conversation.id}")
            
            # Créer message de test
            message = Message.objects.create(
                conversation=conversation,
                sender=agent,
                receiver=user,
                contenu="Message de test pour vérifier la messagerie",
                type_message='texte'
            )
            print(f"✅ Message créé: {message.id}")
            
        # Test 3: Retourner les données
        conversations = Conversation.objects.filter(declarant=user)
        conversation_active = conversations.first()
        messages = []
        
        if conversation_active:
            messages = list(conversation_active.messages.all().order_by('created_at'))
            print(f"📬 Messages dans la conversation: {len(messages)}")
        
        return JsonResponse({
            'success': True,
            'user': user.username,
            'conversations_count': conversations.count(),
            'messages_count': len(messages),
            'conversation_id': conversation_active.id if conversation_active else None,
            'debug_info': 'Conversation et messages créés avec succès'
        })
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"❌ Erreur test: {e}")
        print(f"❌ Détail: {error_detail}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'detail': error_detail
        })


@login_required
def start_claim_conversation(request, declaration_id, claim_type):
    """
    Démarre une conversation de réclamation pour un objet trouvé ou perdu
    claim_type: 'claim' (c'est le mien) ou 'found' (j'ai trouvé)
    """
    try:
        # Récupérer la déclaration
        declaration = get_object_or_404(Declaration, id=declaration_id)
        
        # Vérifier que l'utilisateur n'est pas le déclarant original
        if declaration.declarant == request.user:
            messages.warning(request, "Vous ne pouvez pas réclamer votre propre objet.")
            return redirect('signalements_list')
        
        # Déterminer l'agent (celui de la structure locale de la déclaration)
        agent = None
        if declaration.structure_locale:
            # Trouver un agent de cette structure locale
            agents_structure = Utilisateur.objects.filter(
                role='agent',
                structure_locale=declaration.structure_locale
            ).first()
            if agents_structure:
                agent = agents_structure
        
        # Fallback : prendre un agent administrateur
        if not agent:
            agent = Utilisateur.objects.filter(
                role__in=['agent', 'admin']
            ).first()
        
        if not agent:
            messages.error(request, "Aucun agent disponible pour traiter votre demande.")
            return redirect('signalements_list')
        
        # Vérifier si une conversation existe déjà
        conversation, created = Conversation.objects.get_or_create(
            signalement=declaration,
            agent=agent,
            declarant=request.user
        )
        
        # Si c'est une nouvelle conversation, créer le message d'ouverture
        if created:
            # Déterminer le type de réclamation
            if claim_type == 'claim':
                message_content = f"""🔔 DEMANDE DE RÉCLAMATION D'OBJET

📋 Objet concerné : {declaration.nom_objet}
🔢 Référence : {declaration.numero_declaration}
📍 Lieu : {declaration.lieu_precis}
📅 Date de déclaration : {declaration.date_declaration.strftime('%d/%m/%Y')}

Bonjour,

Je pense que cet objet m'appartient. Pourriez-vous me contacter pour organiser la vérification et la restitution ?

Merci de me dire quels documents ou preuves je dois fournir pour confirmer que cet objet est bien le mien.

Cordialement."""

            else:  # claim_type == 'found'
                message_content = f"""🔔 SIGNALEMENT - OBJET RETROUVÉ

📋 Objet concerné : {declaration.nom_objet}
🔢 Référence : {declaration.numero_declaration}
📍 Lieu de la perte : {declaration.lieu_precis}
📅 Date de déclaration : {declaration.date_declaration.strftime('%d/%m/%Y')}

Bonjour,

Je pense avoir trouvé l'objet correspondant à cette déclaration. Pourriez-vous me contacter pour organiser la vérification et la restitution au propriétaire ?

Je suis disponible pour fournir plus de détails ou photos si nécessaire.

Cordialement."""

            # Créer le message automatique
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                receiver=agent,
                contenu=message_content,
                type_message='texte',
                is_read=False
            )
            
            # Message de succès
            if claim_type == 'claim':
                messages.success(request, f"Demande de réclamation envoyée pour '{declaration.nom_objet}'. Un agent vous contactera bientôt.")
            else:
                messages.success(request, f"Signalement d'objet retrouvé envoyé pour '{declaration.nom_objet}'. Un agent vous contactera bientôt.")
        else:
            # Conversation existante
            messages.info(request, "Une conversation existe déjà pour cet objet. Consultez vos messages.")
        
        # Rediriger vers la messagerie avec l'ID de conversation
        return redirect(f'/utilisateur/messagerie/?conversation_id={conversation.id}')
        
    except Exception as e:
        messages.error(request, f"Erreur lors de la création de la conversation : {str(e)}")
        return redirect('signalements_list')


@login_required
def start_claim_object(request, declaration_id):
    """Vue pour le bouton 'C'est le mien' (objets trouvés)"""
    return start_claim_conversation(request, declaration_id, 'claim')


@login_required  
def start_found_object(request, declaration_id):
    """Vue pour le bouton 'Trouvé' (objets perdus)"""
    return start_claim_conversation(request, declaration_id, 'found')


# ===== NOUVELLES VUES POUR AGENT DOCUMENTS =====

@login_required
def marquer_document_vu(request, document_id):
    """Marquer un document de réclamation comme vu"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    
    if request.user.role not in ['agent', 'admin', 'superadmin']:
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    
    try:
        from core.models import PieceJustificative
        
        # Récupérer le document
        document = PieceJustificative.objects.get(
            id=document_id,
            reclamation__agent_traitant=request.user
        )
        
        # Marquer comme vérifié
        document.verifie = True
        document.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Document marqué comme vu'
        })
        
    except PieceJustificative.DoesNotExist:
        return JsonResponse({'error': 'Document introuvable'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def marquer_message_lu(request, message_id):
    """Marquer un message comme lu"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    
    if request.user.role not in ['agent', 'admin', 'superadmin']:
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    
    try:
        from core.models import Message
        
        # Récupérer le message
        message = Message.objects.get(
            id=message_id,
            conversation__agent=request.user
        )
        
        # Marquer comme lu
        message.is_read = True
        message.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Message marqué comme lu'
        })
        
    except Message.DoesNotExist:
        return JsonResponse({'error': 'Message introuvable'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def agent_signalement_detail(request, signalement_id):
    """Vue détaillée d'un signalement pour l'agent"""
    if request.user.role not in ['agent', 'admin', 'superadmin']:
        return redirect('login')
    
    try:
        from core.models import Declaration
        
        signalement = get_object_or_404(Declaration, id=signalement_id)
        
        # Vérifier que l'agent a accès à ce signalement
        if request.user.role == 'agent':
            # Vérifier si l'agent traite des réclamations pour ce signalement
            # ou si c'est dans sa région
            has_access = (
                signalement.reclamations.filter(agent_traitant=request.user).exists() or
                (signalement.region == request.user.region)
            )
            
            if not has_access:
                return render(request, '403.html', status=403)
        
        context = {
            'signalement': signalement,
            'user': request.user,
            'title': f'Signalement - {signalement.nom_objet}',
            'subtitle': f'Déclaration #{signalement.numero_declaration}'
        }
        
        return render(request, 'agent/signalement_detail.html', context)
        
    except Exception as e:
        messages.error(request, f'Erreur lors du chargement du signalement: {e}')
        return redirect('agent_dashboard')


@login_required  
def agent_messagerie(request):
    """Redirection vers le chat agent avec ID de réclamation"""
    if request.user.role not in ['agent', 'admin', 'superadmin']:
        return redirect('login')
    
    from core.models import Conversation, Message
    
    # Paramètres URL
    conversation_id = request.GET.get('conversation')
    reclamation_id = request.GET.get('reclamation')
    user_param = request.GET.get('user')
    
    # Si une conversation spécifique est demandée
    if conversation_id:
        return redirect(f'/agent/chat/?conversation_id={conversation_id}')
    
    # Si une réclamation est spécifiée, rediriger vers le chat avec cette réclamation
    if reclamation_id:
        return redirect(f'/agent/chat/?reclamation_id={reclamation_id}')
    
    # Sinon, rediriger vers le chat général
    return redirect('/agent/chat/')

from django.contrib.auth.decorators import login_required
from .decorators import role_required
from django.shortcuts import get_object_or_404, redirect
from .models import Declaration, Utilisateur, Conversation

@login_required
@role_required(['agent'])
def ouvrir_conversation(request):
    user = request.user
    signalement_id = request.GET.get('signalement_id')
    declarant_id = request.GET.get('declarant_id')
    if not signalement_id or not declarant_id:
        return redirect('togo_agent:messagerie')
    signalement = get_object_or_404(Declaration, id=signalement_id)
    declarant = get_object_or_404(Utilisateur, id=declarant_id)
    conv, _ = Conversation.objects.get_or_create(
        signalement=signalement,
        agent=user,
        declarant=declarant
    )
    return redirect(f'/agent/messagerie/?conversation_id={conv.id}')
