from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
import json
from core.models import Declaration, Conversation

@csrf_exempt
@login_required
@require_POST
def api_create_conversation_django(request):
    """API Django classique pour créer une conversation"""
    try:
        print(f"🔍 [DJANGO API] Nouvelle requête de {request.user}")
        print(f"🔍 [DJANGO API] User authenticated: {request.user.is_authenticated}")
        print(f"🔍 [DJANGO API] User role: {getattr(request.user, 'role', 'no role')}")
        
        data = json.loads(request.body)
        signalement_id = data.get('signalement_id')
        
        print(f"🔍 [DJANGO API] ID signalement: {signalement_id}")
        
        if not signalement_id:
            return JsonResponse({'error': 'ID du signalement requis'}, status=400)
        
        signalement = get_object_or_404(Declaration, id=signalement_id)
        user = request.user
        
        print(f"🔍 [DJANGO API] Signalement trouvé: {signalement.numero_declaration}")
        print(f"🔍 [DJANGO API] Structure signalement: {signalement.structure_locale}")
        print(f"🔍 [DJANGO API] Structure utilisateur: {user.structure_locale}")
        
        # Déterminer qui est l'agent et qui est le déclarant
        if user.role in ['agent', 'admin']:
            agent = user
            declarant = signalement.declarant
            
            print(f"🔍 [DJANGO API] Mode agent - Déclarant: {declarant}")
            
            # Vérifier que l'agent peut accéder à ce signalement
            if user.role != 'admin' and (not user.structure_locale or user.structure_locale != signalement.structure_locale):
                print(f"❌ [DJANGO API] Accès refusé - structures différentes")
                return JsonResponse({'error': 'Accès non autorisé à ce signalement'}, status=403)
        else:
            print(f"🔍 [DJANGO API] Mode citoyen")
            # L'utilisateur est un citoyen, vérifier que c'est bien son signalement
            if signalement.declarant != user:
                print(f"❌ [DJANGO API] Pas le bon déclarant")
                return JsonResponse({'error': 'Vous ne pouvez contacter que vos propres signalements'}, status=403)
            
            # Trouver un agent de la même structure locale
            from core.models import Utilisateur
            agent = Utilisateur.objects.filter(
                role__in=['agent', 'admin'],
                structure_locale=signalement.structure_locale
            ).first()
            
            if not agent:
                print(f"❌ [DJANGO API] Aucun agent disponible")
                return JsonResponse({'error': 'Aucun agent disponible pour cette zone'}, status=404)
            
            declarant = user
            print(f"🔍 [DJANGO API] Agent trouvé: {agent}")
        
        print(f"🔍 [DJANGO API] Création conversation: agent={agent}, declarant={declarant}")
        
        # Créer ou récupérer la conversation
        conversation, created = Conversation.objects.get_or_create(
            signalement=signalement,
            agent=agent,
            declarant=declarant
        )
        
        print(f"✅ [DJANGO API] Conversation: {conversation.id} (created: {created})")
        
        return JsonResponse({
            'conversation_id': conversation.id,
            'created': created,
            'agent_name': agent.get_full_name() if agent else 'Agent',
            'declarant_name': declarant.get_full_name() if declarant else 'Déclarant',
            'signalement_numero': signalement.numero_declaration,
        })
        
    except Exception as e:
        print(f"❌ [DJANGO API] Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Erreur interne: {str(e)}'}, status=500)