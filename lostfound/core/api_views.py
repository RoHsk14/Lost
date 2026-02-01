def get_or_create_conversation(signalement, agent, declarant):
    """Récupère ou crée une conversation unique pour un signalement, un agent et un déclarant."""
    from core.models import Conversation
    conv, created = Conversation.objects.get_or_create(
        signalement=signalement,
        agent=agent,
        declarant=declarant
    )
    return conv
# core/api_views.py
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.db.models import Max, Q, Count, Value, CharField
from django.db.models.functions import Coalesce
from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.models import Region, Prefecture, StructureLocale, Conversation, Message, Declaration
from django.core.cache import cache

@api_view(['GET'])
def api_regions(request):
    """Renvoie la liste des régions"""
    data = [{"id": r.id, "nom": r.nom} for r in Region.objects.all()]
    return Response(data)

@api_view(['GET'])
def api_prefectures(request, region_id):
    """Renvoie les préfectures d'une région"""
    data = [{"id": p.id, "nom": p.nom} for p in Prefecture.objects.filter(region_id=region_id)]
    return Response(data)

@api_view(['GET'])
def api_structures(request, prefecture_id):
    """Renvoie les structures locales d'une préfecture"""
    data = [{"id": s.id, "nom": s.nom, "type_structure": s.type_structure} for s in StructureLocale.objects.filter(prefecture_id=prefecture_id)]
    return Response(data)


@login_required
@api_view(['GET'])
def api_conversations(request):
    """API ultra-optimisée pour récupérer les conversations"""
    user = request.user
    
    # Cache plus long et clé plus spécifique
    cache_key = f"conversations_fast_{user.id}_{user.role}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        print(f"🚀 Cache hit pour utilisateur {user.id}")
        return Response(cached_data)
    
    print(f"⚡ Génération optimisée pour utilisateur {user.id}")
    
    try:
        # Requête ultra-optimisée avec une seule requête SQL
        if user.role in ['agent', 'admin']:
            conversations = Conversation.objects.filter(
                agent=user
            ).select_related(
                'signalement', 'declarant'
            ).prefetch_related(
                'messages'
            ).annotate(
                # Calculer directement en SQL
                total_messages_count=Count('messages'),
                unread_messages_count=Count('messages', filter=Q(messages__receiver=user, messages__is_read=False)),
                last_message_date=Max('messages__created_at')
            ).order_by('-updated_at')[:20]  # Limiter à 20 conversations max
        else:
            conversations = Conversation.objects.filter(
                declarant=user
            ).select_related(
                'signalement', 'agent'
            ).prefetch_related(
                'messages'
            ).annotate(
                total_messages_count=Count('messages'),
                unread_messages_count=Count('messages', filter=Q(messages__receiver=user, messages__is_read=False)),
                last_message_date=Max('messages__created_at')
            ).order_by('-updated_at')[:20]
        
        # Construire la réponse rapidement
        data = []
        for conv in conversations:
            other_participant = conv.declarant if user == conv.agent else conv.agent
            
            # Récupérer le dernier message de manière efficace
            last_message = conv.messages.order_by('-created_at').first() if conv.messages.exists() else None
            
            # Déterminer le nom du déclarant de manière robuste
            declarant_nom = "Déclarant inconnu"
            if conv.declarant:
                # Essayer get_full_name d'abord
                full_name = conv.declarant.get_full_name().strip()
                if full_name:
                    declarant_nom = full_name
                else:
                    # Fallback sur username si first_name/last_name sont vides
                    declarant_nom = conv.declarant.username
            elif conv.signalement and conv.signalement.declarant:
                # Fallback : récupérer depuis le signalement
                signalement_declarant = conv.signalement.declarant
                full_name = signalement_declarant.get_full_name().strip()
                if full_name:
                    declarant_nom = full_name
                else:
                    declarant_nom = signalement_declarant.username
                    
            data.append({
                'id': conv.id,
                'signalement_numero': conv.signalement.numero_declaration,
                'signalement_id': conv.signalement.id,
                'objet_signalement': conv.signalement.nom_objet if hasattr(conv.signalement, 'nom_objet') else 'Objet non spécifié',
                'citoyen_nom': declarant_nom,
                'declarant_nom': declarant_nom,
                'derniere_activite': conv.updated_at.isoformat(),
                'unread_count': conv.unread_messages_count,
                'total_messages': conv.total_messages_count,
                'other_participant': {
                    'id': other_participant.id,
                    'nom': other_participant.get_full_name(),
                    'role': other_participant.role,
                },
                'last_message': {
                    'contenu': last_message.contenu[:50] + ('...' if len(last_message.contenu) > 50 else ''),
                    'created_at': last_message.created_at.isoformat(),
                    'sender_name': last_message.sender.get_full_name(),
                    'type_message': last_message.type_message
                } if last_message else None
            })
        
        # Cache plus long pour améliorer les performances
        cache.set(cache_key, data, 120)  # 2 minutes
        
        return Response(data)
        
    except Exception as e:
        print(f"❌ Erreur API conversations: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': 'Erreur serveur'}, status=500)


@login_required
@api_view(['GET'])
def api_conversations_counters(request):
    """API légère pour récupérer juste les compteurs non lus"""
    user = request.user
    
    cache_key = f"counters_{user.id}"
    cached_counters = cache.get(cache_key)
    
    if cached_counters:
        return Response(cached_counters)
    
    try:
        if user.role in ['agent', 'admin']:
            conversations = Conversation.objects.filter(agent=user)
        else:
            conversations = Conversation.objects.filter(declarant=user)
        
        counters = {}
        total_unread = 0
        
        for conv in conversations:
            if user.role in ['agent', 'admin']:
                unread = conv.unread_count_for_agent
            else:
                unread = conv.unread_count_for_declarant
            
            counters[conv.id] = unread
            total_unread += unread
        
        result = {
            'total_unread': total_unread,
            'counters': counters
        }
        
        # Cache court pour les compteurs
        cache.set(cache_key, result, 30)
        
        return Response(result)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@login_required
@require_POST
def api_mark_conversation_read(request, conversation_id):
    """API pour marquer une conversation comme lue"""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    user = request.user
    
    # Vérifier les permissions
    if not (conversation.agent == user or conversation.declarant == user):
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    
    # Marquer tous les messages reçus comme lus
    updated_count = Message.objects.filter(
        conversation=conversation,
        receiver=user,
        is_read=False
    ).update(is_read=True)
    
    return JsonResponse({
        'success': True,
        'marked_count': updated_count
    })


@csrf_exempt
@login_required
@require_POST 
def api_upload_file(request):
    """API pour uploader un fichier dans une conversation"""
    try:
        conversation_id = request.POST.get('conversation_id')
        if not conversation_id:
            return JsonResponse({'error': 'ID de conversation requis'}, status=400)
        
        conversation = get_object_or_404(Conversation, id=conversation_id)
        user = request.user
        
        # Vérifier les permissions
        if not (conversation.agent == user or conversation.declarant == user):
            return JsonResponse({'error': 'Accès non autorisé'}, status=403)
        
        if 'fichier' not in request.FILES:
            return JsonResponse({'error': 'Aucun fichier fourni'}, status=400)
        
        uploaded_file = request.FILES['fichier']
        
        # Déterminer le destinataire
        receiver = conversation.declarant if user == conversation.agent else conversation.agent
        
        # Créer le message avec le fichier
        message = Message.objects.create(
            conversation=conversation,
            sender=user,
            receiver=receiver,
            contenu=f'Fichier envoyé: {uploaded_file.name}',
            fichier=uploaded_file,
        )
        
        # Invalider le cache pour les deux participants
        cache.delete(f"conversations_user_{conversation.declarant.id}")
        cache.delete(f"conversations_user_{conversation.agent.id}")
        print(f"🔄 Cache invalidé pour les utilisateurs {conversation.declarant.id} et {conversation.agent.id}")
        
        # Envoyer notification via WebSocket
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        if channel_layer:
            conversation_group_name = f'chat_{conversation.id}'
            
            # Préparer les données du message
            message_data = {
                'id': message.id,
                'contenu': message.contenu,
                'expediteur': message.sender.id,
                'expediteur_nom': message.sender.get_full_name(),
                'created_at': message.created_at.isoformat(),
                'is_from_me': False,  # Sera recalculé côté client
                'fichier': {
                    'url': message.fichier.url,
                    'nom': uploaded_file.name
                } if message.fichier else None,
            }
            
            # Envoyer le message à tous les participants
            async_to_sync(channel_layer.group_send)(
                conversation_group_name,
                {
                    'type': 'chat_message',
                    'message': message_data
                }
            )
        
        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'file_url': message.fichier.url,
            'file_name': uploaded_file.name,
        })
        
    except Exception as e:
        print(f"❌ Erreur upload fichier: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
def api_create_conversation(request):
    """API pour créer ou récupérer une conversation"""
    try:
        print(f"🔍 [CHAT API] Nouvelle requête de {request.user}")
        print(f"🔍 [CHAT API] Données reçues: {request.data}")
        
        # Vérifier l'authentification
        if not request.user.is_authenticated:
            print("❌ [CHAT API] Utilisateur non authentifié")
            return Response({'error': 'Authentification requise'}, status=401)
            
        signalement_id = request.data.get('signalement_id')
        print(f"🔍 [CHAT API] ID signalement: {signalement_id}")
        
        if not signalement_id:
            print("❌ [CHAT API] ID manquant")
            return Response({'error': 'ID du signalement requis'}, status=400)
        
        try:
            signalement = get_object_or_404(Declaration, id=signalement_id)
            print(f"✅ [CHAT API] Signalement trouvé: {signalement.numero_declaration}")
        except Exception as e:
            print(f"❌ [CHAT API] Erreur récupération signalement: {e}")
            raise
        user = request.user
        print(f"🔍 [CHAT API] Utilisateur: {user.username} (role: {user.role})")
        print(f"🔍 [CHAT API] Structure locale utilisateur: {user.structure_locale}")
        
        # Déterminer qui est l'agent et qui est le déclarant
        if user.role in ['agent', 'admin']:
            agent = user
            declarant = signalement.declarant
            print(f"🔍 [CHAT API] Mode agent - Déclarant: {declarant}")
            
            # Vérifier que l'agent peut accéder à ce signalement
            can_access = _agent_peut_acceder_signalement(user, signalement)
            print(f"🔍 [CHAT API] Peut accéder: {can_access}")
            if not can_access:
                print(f"❌ [CHAT API] Accès refusé")
                return Response({'error': 'Accès non autorisé à ce signalement'}, status=403)
        else:
            print(f"🔍 [CHAT API] Mode citoyen")
            # L'utilisateur est un citoyen, vérifier que c'est bien son signalement
            if signalement.declarant != user:
                print(f"❌ [CHAT API] Pas le bon déclarant")
                return Response({'error': 'Vous ne pouvez contacter que vos propres signalements'}, status=403)
            
            # Trouver un agent de la même structure locale
            from core.models import Utilisateur
            agent = Utilisateur.objects.filter(
                role__in=['agent', 'admin'],
                structure_locale=signalement.structure_locale
            ).first()
            
            if not agent:
                print(f"❌ [CHAT API] Aucun agent disponible")
                return Response({'error': 'Aucun agent disponible pour cette zone'}, status=404)
            
            declarant = user
            print(f"🔍 [CHAT API] Agent trouvé: {agent}")
        
        print(f"🔍 [CHAT API] Création conversation: agent={agent}, declarant={declarant}")
        
        # Créer ou récupérer la conversation
        conversation, created = Conversation.objects.get_or_create(
            signalement=signalement,
            agent=agent,
            declarant=declarant
        )
        
        print(f"✅ [CHAT API] Conversation: {conversation.id} (created: {created})")
        
        return Response({
            'conversation_id': conversation.id,
            'created': created,
            'agent_name': agent.get_full_name() if agent else 'Agent',
            'declarant_name': declarant.get_full_name() if declarant else 'Déclarant',
            'signalement_numero': signalement.numero_declaration,
        })
        
    except Exception as e:
        print(f"❌ [CHAT API] Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': f'Erreur interne: {str(e)}'}, status=500)


@csrf_exempt
@api_view(['GET', 'POST'])
def api_test_auth(request):
    """API de test pour vérifier l'authentification"""
    return Response({
        'authenticated': request.user.is_authenticated,
        'user': request.user.username if request.user.is_authenticated else None,
        'role': getattr(request.user, 'role', None),
        'structure_locale': str(request.user.structure_locale) if hasattr(request.user, 'structure_locale') and request.user.structure_locale else None,
        'method': request.method,
        'data': dict(request.data) if hasattr(request, 'data') else 'no data'
    })


def _agent_peut_acceder_signalement(agent, signalement):
    """Vérifier si un agent peut accéder à un signalement"""
    if agent.role == 'admin':
        return True
    
    return (agent.structure_locale and 
           signalement.structure_locale and 
           agent.structure_locale == signalement.structure_locale)


@csrf_exempt
@api_view(['GET', 'POST'])
def api_conversation_messages(request, conversation_id):
    """API pour récupérer (GET) et envoyer (POST) des messages"""
    from core.models import Declaration, Utilisateur, Conversation
    conversation = get_object_or_404(Conversation, id=conversation_id)
    user = request.user

    # Vérifier les permissions
    if not (conversation.agent == user or conversation.declarant == user):
        return Response({'error': 'Accès non autorisé'}, status=403)

    if request.method == 'GET':
        # Logique existante pour récupérer les messages
        page = int(request.GET.get('page', 1))
        per_page = min(int(request.GET.get('per_page', 30)), 50)
        offset = (page - 1) * per_page
        
        cache_key = f"messages_{conversation_id}_p{page}_{per_page}"
        cached_messages = cache.get(cache_key)
        
        if cached_messages:
            return Response(cached_messages)
        
        total_messages = conversation.messages.count()
        messages = conversation.messages.select_related('sender', 'receiver').order_by('created_at')[offset:offset+per_page]
        
        data = []
        for message in messages:
            data.append({
                'id': message.id,
                'contenu': message.contenu,
                'expediteur': message.sender.id,
                'expediteur_nom': message.sender.get_full_name(),
                'destinataire': message.receiver.id,
                'destinataire_nom': message.receiver.get_full_name(),
                'date_envoi': message.created_at.isoformat(),
                'is_read': message.is_read,
                'fichier_joint': message.fichier.url if message.fichier else None,
                'type_message': getattr(message, 'type_message', 'text'),
            })
        
        return Response(data)
    elif request.method == 'POST':
        # Créer un nouveau message
        try:
            # Récupérer le contenu et le fichier
            contenu = request.data.get('contenu', '').strip()
            fichier = request.FILES.get('fichier')

            # Valider qu'il y a au moins un contenu ou un fichier
            if not contenu and not fichier:
                return Response({'error': 'Message vide'}, status=400)

            # S'assurer que la conversation est bien unique pour ce signalement/agent/déclarant
            signalement = conversation.signalement
            agent = conversation.agent
            declarant = conversation.declarant
            conversation = get_or_create_conversation(signalement, agent, declarant)

            # Déterminer le destinataire
            destinataire = conversation.declarant if user == conversation.agent else conversation.agent

            # Créer le message
            message = Message.objects.create(
                conversation=conversation,
                sender=user,
                receiver=destinataire,
                contenu=contenu,
                fichier=fichier
            )

            # Mettre à jour la conversation
            conversation.derniere_activite = message.created_at
            conversation.dernier_message = contenu or "Fichier joint"
            conversation.save()

            # Réponse avec les détails du message créé
            return Response({
                'id': message.id,
                'contenu': message.contenu,
                'expediteur': message.sender.id,
                'expediteur_nom': message.sender.get_full_name(),
                'destinataire': message.receiver.id,
                'destinataire_nom': message.receiver.get_full_name(),
                'date_envoi': message.created_at.isoformat(),
                'fichier_joint': message.fichier.url if message.fichier else None,
                'status': 'success'
            }, status=201)

        except Exception as e:
            print(f"Erreur création message: {e}")
            return Response({'error': f'Erreur interne: {str(e)}'}, status=500)
