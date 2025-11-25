from django.urls import path
from . import views_admin

app_name = 'superadmin'

urlpatterns = [
    # Dashboard superadmin
    path('dashboard/', views_admin.superadmin_dashboard, name='dashboard'),
    
    # Gestion des administrateurs
    path('admins/', views_admin.superadmin_gestion_admins, name='gestion_admins'),
    path('admins/creer/', views_admin.creer_admin, name='creer_admin'),
]