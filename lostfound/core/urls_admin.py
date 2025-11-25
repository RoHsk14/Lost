from django.urls import path
from . import views_admin

app_name = 'togo_admin'

urlpatterns = [
    # Dashboard admin
    path('', views_admin.admin_dashboard, name='dashboard'),
    path('dashboard/', views_admin.admin_dashboard, name='dashboard_alt'),
    
    # Gestion des utilisateurs
    path('users/', views_admin.admin_users, name='users_list'),
    path('users/create/', views_admin.create_user, name='create_user'),
    path('users/<int:user_id>/edit/', views_admin.edit_user, name='edit_user'),
    path('users/<int:user_id>/delete/', views_admin.delete_user, name='delete_user'),
    
    # Gestion des agents - URLs réactivées temporairement avec redirection d'erreur
    path('agents/', views_admin.agents_list, name='agents_list'),
    path('agents/create/', views_admin.create_agent, name='create_agent'),
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
    
    # Rapports et statistiques
    path('rapports/', views_admin.admin_rapports, name='reports'),
    path('statistics/', views_admin.statistics, name='statistics'),
    
    # Régions et configuration
    path('regions/', views_admin.regions_list, name='regions_list'),
    path('settings/', views_admin.settings, name='settings'),
    
    # Superadmin (si applicable)
    path('superadmin/', views_admin.superadmin_dashboard, name='superadmin_dashboard'),
    path('superadmin/admins/', views_admin.superadmin_gestion_admins, name='superadmin_admins'),
    path('superadmin/creer-admin/', views_admin.creer_admin, name='creer_admin'),
]