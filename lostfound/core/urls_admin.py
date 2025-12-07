from django.urls import path
from . import views_admin

app_name = 'togo_admin'

urlpatterns = [
    # Dashboard admin
    path('', views_admin.admin_dashboard, name='dashboard'),
    path('dashboard/', views_admin.admin_dashboard, name='dashboard_alt'),
    
    # Gestion des utilisateurs
    path('users/', views_admin.admin_users, name='users'),
    path('users/create/', views_admin.create_user, name='create_user'),
    path('users/<int:user_id>/', views_admin.user_detail, name='user_detail'),
    path('users/<int:user_id>/edit/', views_admin.edit_user, name='edit_user'),
    path('users/<int:user_id>/delete/', views_admin.delete_user, name='delete_user'),
    path('users/<int:user_id>/verify/', views_admin.verify_user, name='verify_user'),
    path('users/<int:user_id>/toggle-status/', views_admin.toggle_user_status_api, name='toggle_user_status_api'),
    path('users/<int:user_id>/reset-password/', views_admin.reset_user_password, name='reset_user_password'),
    path('users/<int:user_id>/message/', views_admin.send_user_message, name='send_user_message'),
    path('users/bulk-action/', views_admin.bulk_user_action, name='bulk_user_action'),
    path('users/notify/', views_admin.notify_users, name='notify_users'),
    
    # Gestion des agents - Création d'agent avec formulaire complet
    path('agents/', views_admin.agents_list, name='agents_list'),
    path('agents/create/', views_admin.creer_agent, name='create_agent'),
    path('agents/<int:agent_id>/edit/', views_admin.edit_agent, name='edit_agent'),
    path('agents/<int:agent_id>/delete/', views_admin.delete_agent, name='delete_agent'),
    
    # Gestion des déclarations
    path('declarations/', views_admin.admin_declarations, name='declarations_list'),
    path('declarations/<int:declaration_id>/', views_admin.declaration_detail, name='declaration_detail'),
    path('declarations/<int:declaration_id>/valider/', views_admin.valider_declaration, name='valider_declaration'),
    path('declarations/<int:declaration_id>/validate/', views_admin.validate_declaration, name='validate_declaration'),
    path('declarations/<int:declaration_id>/reject/', views_admin.reject_declaration, name='reject_declaration'),
    path('declarations/<int:declaration_id>/edit/', views_admin.edit_declaration, name='edit_declaration'),
    path('declarations/pending/', views_admin.pending_declarations, name='pending_declarations'),
    path('toggle-user-status/', views_admin.toggle_user_status, name='toggle_user_status'),
    
    # Gestion des signalements
    path('signalements/', views_admin.signalements_list, name='signalements_list'),
    path('signalements/<int:signalement_id>/', views_admin.signalement_detail, name='signalement_detail'),
    path('signalements/<int:signalement_id>/edit/', views_admin.signalement_edit, name='signalement_edit'),
    path('signalements/<int:signalement_id>/delete/', views_admin.signalement_delete, name='signalement_delete'),
    
    # Rapports et statistiques
    path('rapports/', views_admin.admin_rapports, name='reports'),
    path('statistics/', views_admin.statistics, name='statistics'),
    
    # Régions et configuration
    path('regions/', views_admin.regions_list, name='regions_list'),
    path('api/prefectures/<int:region_id>/', views_admin.get_prefectures, name='get_prefectures'),
    path('settings/', views_admin.settings, name='settings'),
]