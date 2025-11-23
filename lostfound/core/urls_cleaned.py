from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

from . import views, api_views
from .views import RegionViewSet, PrefectureViewSet, StructureLocaleViewSet, SignalementViewSet

# Configuration du routeur pour l'API REST
router = DefaultRouter()
router.register(r'regions', RegionViewSet, basename='region')
router.register(r'prefectures', PrefectureViewSet, basename='prefecture')
router.register(r'structures_locales', StructureLocaleViewSet, basename='structurelocale')
router.register(r'signalements', SignalementViewSet, basename='signalement')

urlpatterns = [
    # ---------------------------
    # API Routes
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
    # Dashboards
    # ---------------------------
    # Superadmin
    path('superadmin/dashboard/', views.superadmin_dashboard, name='superadmin_dashboard'),
    path('superadmin/utilisateurs/', views.superadmin_users, name='superadmin_users'),
    path('superadmin/admins/', views.superadmin_gestion_admins, name='superadmin_gestion_admins'),
    path('superadmin/admins/creer/', views.creer_admin, name='superadmin_create_admins'),
    path('superadmin/admins/<int:pk>/modifier/', views.superadmin_edit_admin, name='superadmin_edit_admin'),
    path('superadmin/admins/<int:pk>/supprimer/', views.superadmin_delete_admin, name='superadmin_delete_admin'),

    # Admin
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/signalement/<int:pk>/', views.admin_signalement_detail, name='admin_signalement_detail'),

    # Utilisateur
    path('utilisateur/dashboard/', views.utilisateur_dashboard, name='utilisateur_dashboard'),
    path('utilisateur/signalement/<int:pk>/', views.utilisateur_signalement_detail, name='utilisateur_signalement_detail'),

    # ---------------------------
    # Signalements CRUD
    # ---------------------------
    path('signalements/', views.signalements_list, name='signalements_list'),
    path('signalement/<int:pk>/', views.signalement_detail, name='signalement_detail'),
    path('signalement/add/', views.signalement_add, name='signalement_add'),
    path('signalement/<int:pk>/modifier/', views.signalement_edit, name='signalement_edit'),
    path('signalement/<int:pk>/supprimer/', views.signalement_delete, name='signalement_delete'),

    # ---------------------------
    # Objets
    # ---------------------------
    path('objets/', views.objets_list, name='objets_list'),
    path('objets/<int:pk>/', views.objet_detail, name='objet_detail'),

    # ---------------------------
    # Utilisateurs (superadmin)
    # ---------------------------
    path('utilisateurs/', views.utilisateurs_list, name='utilisateurs_list'),

    # ---------------------------
    # Recherche
    # ---------------------------
    path('search/', views.search_objets, name='search_objets'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
