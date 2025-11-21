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



from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegionViewSet, PrefectureViewSet, StructureLocaleViewSet, SignalementViewSet
from core import api_views

router = DefaultRouter()
# router.register(r'regions', RegionViewSet)
# router.register(r'prefectures', PrefectureViewSet)
# router.register(r'structures-locales', StructureLocaleViewSet)
# router.register(r'signalements', SignalementViewSet)


router.register(r'regions', RegionViewSet, basename='region')
router.register(r'prefectures', PrefectureViewSet, basename='prefecture')
router.register(r'structures_locales', StructureLocaleViewSet, basename='structurelocale')
router.register(r'signalements', SignalementViewSet, basename='signalement')


urlpatterns = [
    # ---------------------------
    # API REST
    # ---------------------------
    path('api/', include(router.urls)),
    path('api/regions/', api_views.api_regions, name='api_regions'),
    path('api/prefectures/<int:region_id>/', api_views.api_prefectures, name='api_prefectures'),
    path('api/structures/<int:prefecture_id>/', api_views.api_structures, name='api_structures'),

    # ---------------------------
    # Pages publiques
    # ---------------------------
    path('', views.index, name='index'),
    path('home/', views.home, name='home'),

    # ---------------------------
    # Authentification
    # ---------------------------
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # ---------------------------
    # Superadmin
    # ---------------------------
    path('superadmin/dashboard/', views.superadmin_dashboard, name='superadmin_dashboard'),
    path('superadmin/utilisateurs/', views.superadmin_users, name='superadmin_users'),
    path('superadmin/admins/', views.superadmin_gestion_admins, name='superadmin_gestion_admins'),
    path('superadmin/admins/creer/', views.creer_admin, name='superadmin_create_admins'),
    path('superadmin/admins/<int:pk>/modifier/', views.superadmin_edit_admin, name='superadmin_edit_admin'),
    path('superadmin/admins/<int:pk>/supprimer/', views.superadmin_delete_admin, name='superadmin_delete_admin'),

    # ---------------------------
    # Admin (zone)
    # ---------------------------
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/signalement/<int:pk>/', views.admin_signalement_detail, name='admin_signalement_detail'),

    # ---------------------------
    # Utilisateur dashboard
    # ---------------------------
    path('utilisateur/dashboard/', views.utilisateur_dashboard, name='utilisateur_dashboard'),
    path('utilisateur/signalement/<int:pk>/', views.utilisateur_signalement_detail, name='utilisateur_signalement_detail'),

    # ---------------------------
    # Signalements (ancien système)
    # ---------------------------
    path('signalements/', views.signalements_list, name='signalements_list'),
    path('signalement/<int:pk>/', views.signalement_detail, name='signalement_detail'),
    path('signalement/add/', views.signalement_add, name='signalement_add'),
    path('signalement/<int:pk>/modifier/', views.signalement_edit, name='signalement_edit'),
    path('signalement/<int:pk>/supprimer/', views.signalement_delete, name='signalement_delete'),

    # ---------------------------
    # Objets (nouveau système)
    # ---------------------------
    path('objets/', views.objets_publies_list, name='objets_publies_list'),
    path('objets/declarer/', views.objet_declarer, name='objet_declarer'),
    path('objets/<int:pk>/', views.objet_detail, name='objet_detail'),
    path('mes-objets/', views.mes_objets, name='mes_objets'),
    path('mes-declarations/', views.mes_declarations, name='mes_declarations'),

    # ---------------------------
    # Réclamations
    # ---------------------------
    path('reclamer/<int:objet_id>/', views.reclamer_objet, name='reclamer_objet'),
    path('mes-reclamations/', views.mes_reclamations, name='mes_reclamations'),
    path('reclamation/<int:pk>/', views.reclamation_detail, name='reclamation_detail'),

    # ---------------------------
    # Agent/Admin - Gestion
    # ---------------------------
    path('agent/dashboard/', views.agent_dashboard, name='agent_dashboard'),
    path('agent/declarations/', views.agent_declarations, name='agent_declarations'),
    path('agent/declaration/<int:pk>/valider/', views.agent_valider_declaration, name='agent_valider_declaration'),
    path('agent/reclamations/', views.agent_reclamations, name='agent_reclamations'),
    path('agent/reclamation/<int:pk>/valider/', views.agent_valider_reclamation, name='agent_valider_reclamation'),

    # ---------------------------
    # Notifications
    # ---------------------------
    path('notifications/', views.mes_notifications, name='mes_notifications'),
    path('notification/<int:pk>/lire/', views.notification_marquer_lue, name='notification_marquer_lue'),
    path('notifications/marquer-toutes-lues/', views.notifications_marquer_toutes_lues, name='notifications_marquer_toutes_lues'),

    # ---------------------------
    # Utilisateurs
    # ---------------------------
    path('utilisateurs/', views.utilisateurs_list, name='utilisateurs_list'),

    # ---------------------------
    # Recherche
    # ---------------------------
    path('search/', views.search_objets, name='search_objets'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
