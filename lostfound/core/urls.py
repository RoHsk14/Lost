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

router = DefaultRouter()
router.register(r'regions', RegionViewSet, basename='region')
router.register(r'prefectures', PrefectureViewSet, basename='prefecture')
router.register(r'structures_locales', StructureLocaleViewSet, basename='structurelocale')
router.register(r'signalements', SignalementViewSet, basename='signalement')

urlpatterns = [
    # ===== API =====
    path('api/', include(router.urls)),
    path('api/regions/', api_views.api_regions, name='api_regions'),
    path('api/prefectures/<int:region_id>/', api_views.api_prefectures, name='api_prefectures'),
    path('api/structures/<int:prefecture_id>/', api_views.api_structures, name='api_structures'),
    
    # ===== SYSTÈMES ADMIN AVANCÉS =====
    path('agent/', include('core.urls_agent')),
    path('togoretrouve-admin/', include('core.urls_admin')), 
    path('superadmin/', include('core.urls_superadmin')),
    
    # ===== PAGES PUBLIQUES =====
    path('', views.index, name='index'),
    path('home/', views.home, name='home'),
    
    # ===== AUTHENTIFICATION =====
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    
    # ===== DASHBOARDS EXISTANTS (compatibilité) =====
    path('superadmin/dashboard/', views.superadmin_dashboard, name='superadmin_dashboard'),
    path('superadmin/utilisateurs/', views.superadmin_users, name='superadmin_users'),
    path('superadmin/admins/', views.superadmin_gestion_admins, name='superadmin_gestion_admins'),
    path('superadmin/admins/creer/', views.creer_admin, name='superadmin_create_admins'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/signalement/<int:pk>/', views.admin_signalement_detail, name='admin_signalement_detail'),
    
    # ===== ESPACE UTILISATEUR =====
    path('utilisateur/dashboard/', views.utilisateur_dashboard, name='utilisateur_dashboard'),
    path('utilisateur/profil/', views.utilisateur_profil, name='utilisateur_profil'),
    path('utilisateur/parametres/', views.utilisateur_parametres, name='utilisateur_parametres'),
    path('utilisateur/mes-signalements/', views.mes_signalements, name='mes_signalements'),
    path('utilisateur/signalement/<int:pk>/', views.utilisateur_signalement_detail, name='utilisateur_signalement_detail'),
    
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
    
    # ===== RECHERCHE =====
    path('search/', views.search_objets, name='search_objets'),
    
    # ===== AUTRES =====
    path('utilisateurs/', views.utilisateurs_list, name='utilisateurs_list'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
