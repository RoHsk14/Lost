from django.urls import path
from . import views_agent

app_name = 'togo_agent'

urlpatterns = [
    # Dashboard principal
    path('', views_agent.agent_dashboard, name='dashboard'),
    path('dashboard/', views_agent.agent_dashboard, name='dashboard_alt'),
    path('chat/', views_agent.agent_chat_dashboard, name='chat'),
    
    # Module "Mes signalements"
    path('mes-signalements/', views_agent.mes_signalements, name='mes_signalements'),
    path('signalement/<int:signalement_id>/', views_agent.signalement_detail, name='signalement_detail'),
    path('signalement/<int:signalement_id>/valider/', views_agent.valider_signalement, name='valider_signalement'),
    path('signalement/<int:signalement_id>/retrouve/', views_agent.marquer_retrouve, name='marquer_retrouve'),
    path('signalement/<int:signalement_id>/restitue/', views_agent.marquer_restitue, name='marquer_restitue'),
    path('signalement/<int:signalement_id>/contacter/', views_agent.contacter_declarant, name='contacter_declarant'),
    path('signalement/<int:signalement_id>/rapport/', views_agent.generer_rapport, name='generer_rapport'),
    
    # Module "Commentaires et échanges"
    path('commentaires/', views_agent.commentaires_echanges, name='commentaires_echanges'),
    path('commentaires/repondre/<int:commentaire_id>/', views_agent.repondre_commentaire, name='repondre_commentaire'),
    path('commentaires/approuver/<int:commentaire_id>/', views_agent.approuver_commentaire, name='approuver_commentaire'),
    path('commentaires/rejeter/<int:commentaire_id>/', views_agent.rejeter_commentaire, name='rejeter_commentaire'),
    path('signalement/<int:signalement_id>/repondre/', views_agent.repondre_signalement, name='repondre_signalement'),
    
    # Module "Vérification d'identité"
    path('verification/', views_agent.verification_identite, name='verification_identite'),
    path('verification/<int:reclamation_id>/', views_agent.verifier_reclamation, name='verifier_reclamation'),
    path('verification/<int:reclamation_id>/valider/', views_agent.valider_document_verification, name='valider_document_verification'),
    path('verification/<int:reclamation_id>/rejeter/', views_agent.rejeter_document_verification, name='rejeter_document_verification'),
    
    # Module "Messagerie directe"
    path('messagerie/', views_agent.messagerie, name='messagerie'),
    path('conversation/<int:conversation_id>/', views_agent.conversation_detail, name='conversation_detail'),
    path('conversation/<int:conversation_id>/send/', views_agent.send_message, name='send_message'),
    path('conversation/<int:conversation_id>/messages/', views_agent.get_conversation_messages, name='get_conversation_messages'),
    
    # Fonction de validation finale et restitution
    path('restitution/<int:reclamation_id>/valider/', views_agent.valider_restitution, name='valider_restitution'),
    path('recu/<int:reclamation_id>/', views_agent.generer_recu_restitution, name='generer_recu_restitution'),
    
    # Profil et paramètres
    path('profil/', views_agent.agent_profil, name='profil'),
    path('parametres/', views_agent.agent_parametres, name='parametres'),
    
    # APIs AJAX
    path('ajax/stats/', views_agent.ajax_statistiques_dashboard, name='ajax_stats'),
    path('ajax/statistiques/', views_agent.ajax_statistiques_dashboard, name='ajax_statistiques_dashboard'),
    path('ajax/notification/<int:notification_id>/lue/', views_agent.ajax_marquer_notification_lue, name='ajax_marquer_notification_lue'),
    
    # Ouvrir une conversation
    path('ouvrir_conversation/', views_agent.ouvrir_conversation, name='ouvrir_conversation'),
]