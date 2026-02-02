# from django.urls import path
# from . import views
# from django.conf import settings
# from django.conf.urls.static import static

# urlpatterns = [
#     # path('', views.home, name='home'),
#     path('', views.index, name='index'),
#     path('', views.objets_recents, name='home'),

#     path('signalements/', views.signalements_list, name='signalements_list'),
#     path('signalement/<int:pk>/', views.signalement_detail, name='signalement_detail'),
#     path('signalement/add/', views.signalement_add, name='signalement_add'),
#     path('signalement/<int:pk>/modifier/', views.signalement_edit, name='signalement_edit'),
#     path('signalement/<int:pk>/supprimer/', views.signalement_delete, name='signalement_delete'),
#     path('objets/', views.objets_list, name='objets_list'),
#     path('objets/<int:pk>/', views.objet_detail, name='objet_detail'),
#     path('signalements/<int:pk>/', views.signalement_detail, name='signalement_detail'),
#     path('utilisateurs/', views.utilisateurs_list, name='utilisateurs_list'),
#     path('login/', views.login_view, name='login'),
#     path('logout/', views.logout_view, name='logout'),
#     path('register/', views.register_view, name='register'),
#     path('search/', views.search_objets, name='search_objets'),
# path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
#     path('admin/signalements/', views.admin_signalements, name='admin_signalements'),
# path('redirect/', views.home_redirect, name='home_redirect'),

#     path('superadmin/dashboard/', views.superadmin_dashboard, name='superadmin_dashboard'),
#     path('superadmin/utilisateurs/', views.superadmin_users, name='superadmin_users'),
    
#     # Superadmin
#     path('superadmin/dashboard/', views.superadmin_dashboard, name='superadmin_dashboard'),
#     path('superadmin/admins/', views.superadmin_gestion_admins, name='superadmin_gestion_admins'),

#     # Admin
#     path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
#     path('admin/signalement/<int:pk>/', views.admin_signalement_detail, name='admin_signalement_detail'),

#     # Utilisateur
#     path('utilisateur/dashboard/', views.utilisateur_dashboard, name='utilisateur_dashboard'),
#     path('utilisateur/signalement/<int:pk>/', views.utilisateur_signalement_detail, name='utilisateur_signalement_detail'),
# ]

# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from .views import RegionViewSet, PrefectureViewSet, StructureLocaleViewSet, SignalementViewSet
from core import api_views
from core import api_django_views

router = DefaultRouter()
router.register(r'regions', RegionViewSet, basename='region')
router.register(r'prefectures', PrefectureViewSet, basename='prefecture')
router.register(r'structures_locales', StructureLocaleViewSet, basename='structurelocale')
router.register(r'signalements', SignalementViewSet, basename='signalement')

urlpatterns = [
    # ===== API =====
    # Endpoints fonctionnels (prioritaires)
    path('api/regions/', api_views.api_regions, name='api_regions'),
    # Endpoints spécifiques sans conflit avec le router DRF
    path('api/prefectures/region/<int:region_id>/', api_views.api_prefectures, name='api_prefectures'),
    path('api/structures/prefecture/<int:prefecture_id>/', api_views.api_structures, name='api_structures'),
    # Endpoints utilitaires (query params)
    path('api/query/prefectures/', views.api_prefectures, name='api_prefectures_query'),
    path('api/query/structures/', views.api_structures, name='api_structures_query'),
    # API Géolocalisation (AVANT le router DRF pour éviter les conflits)
    path('api/signalements/map-data/', views.signalements_map_data, name='signalements_map_data'),
    # Router DRF (list/detail)
    path('api/', include(router.urls)),
    
    # APIs pour le chat intégré dans les dashboards
    path('api/conversations/', api_views.api_conversations, name='api_conversations'),
    path('api/conversations/create/', api_views.api_create_conversation, name='api_create_conversation'),
    path('api/conversations/create-django/', api_django_views.api_create_conversation_django, name='api_create_conversation_django'),
    path('api/test-auth/', api_views.api_test_auth, name='api_test_auth'),
    path('api/conversations/<int:conversation_id>/messages/', api_views.api_conversation_messages, name='api_conversation_messages'),
    path('api/conversations/<int:conversation_id>/mark-read/', api_views.api_mark_conversation_read, name='api_mark_conversation_read'),
    path('api/upload-file/', views.api_upload_file, name='api_upload_file_main'),
    
    # ===== SYSTÈMES ADMIN AVANCÉS =====
    path('agent/', include('core.urls_agent')),
    path('togoretrouve-admin/', include('core.urls_admin')),
    
    # ===== PAGES PUBLIQUES =====
    path('', views.index, name='index'),
    path('home/', views.home, name='home'),
    
    # ===== AUTHENTIFICATION =====
    path('login/', views.login_view, name='login'),
    path('debug-login/', views.debug_login_view, name='debug_login'),  # Route de debug temporaire
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    
    # ===== DASHBOARDS EXISTANTS (compatibilité) =====
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/signalement/<int:pk>/', views.admin_signalement_detail, name='admin_signalement_detail'),
    
    # ===== ESPACE UTILISATEUR =====
    path('utilisateur/dashboard/', views.utilisateur_dashboard, name='utilisateur_dashboard'),
    path('utilisateur/profil/', views.utilisateur_profil, name='utilisateur_profil'),
    path('utilisateur/parametres/', views.utilisateur_parametres, name='utilisateur_parametres'),
    path('utilisateur/notifications/', views.utilisateur_notifications, name='utilisateur_notifications'),
    path('agent/notifications/', views.agent_notifications, name='agent_notifications'),
    path('agent/documents/', views.agent_documents, name='agent_documents'),
    path('agent/profil/', views.agent_profil, name='agent_profil'),
    path('agent/parametres/', views.agent_parametres, name='agent_parametres'),
    
    # ===== NOUVELLES FONCTIONNALITÉS AGENT =====
    path('agent/marquer-document-vu/<str:document_id>/', views.marquer_document_vu, name='marquer_document_vu'),
    path('agent/marquer-message-lu/<int:message_id>/', views.marquer_message_lu, name='marquer_message_lu'),
    path('agent/signalement/<int:signalement_id>/', views.agent_signalement_detail, name='agent_signalement_detail'),
    path('agent/messagerie/', views.agent_messagerie, name='agent_messagerie'),
    
    path('utilisateur/mes-signalements/', views.mes_signalements, name='mes_signalements'),
    path('utilisateur/messagerie/', views.messagerie, name='messagerie'),
    path('api/envoyer-message/', views.api_envoyer_message, name='api_envoyer_message'),
    path('api/messages/<int:conversation_id>/', views.api_messages_conversation, name='api_messages_conversation'),
    path('api/upload-file/', views.api_upload_file, name='api_upload_file'),
    path('debug/messagerie/', views.test_messagerie_debug, name='debug_messagerie'),
    path('utilisateur/signalement/<int:pk>/', views.utilisateur_signalement_detail, name='utilisateur_signalement_detail'),
    
    # ===== CONVERSATIONS DE RÉCLAMATION =====
    path('conversation/claim/<int:declaration_id>/', views.start_claim_object, name='start_claim_object'),
    path('conversation/found/<int:declaration_id>/', views.start_found_object, name='start_found_object'),
    
    # ===== SIGNALEMENTS =====
    path('signalements/', views.signalements_list, name='signalements_list'),
    path('signalement/<int:pk>/', views.signalement_detail, name='signalement_detail'),
    path('signalement/add/', views.signalement_add, name='signalement_add'),
    path('signalement/<int:pk>/modifier/', views.signalement_edit, name='signalement_edit'),
    path('signalement/<int:pk>/supprimer/', views.signalement_delete, name='signalement_delete'),
    path('api/signalement/<int:signalement_id>/commentaire/', views.ajouter_commentaire_ajax, name='ajouter_commentaire_ajax'),
    
    # ===== OBJETS =====
    path('objets/', views.objets_list, name='objets_list'),
    path('objets-perdus/', views.objets_perdus_list, name='objets_perdus_list'),
    path('objets/<int:pk>/', views.objet_detail, name='objet_detail'),
    
    # ===== DECLARATIONS =====
    path('declarations/<int:pk>/', views.declaration_detail_public, name='declaration_detail'),
    
    # ===== RECHERCHE =====
    path('search/', views.search_objets, name='search_objets'),
    
    # ===== AUTRES =====
    path('utilisateurs/', views.utilisateurs_list, name='utilisateurs_list'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
