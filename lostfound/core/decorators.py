# core/decorators.py
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.http import JsonResponse


def role_required(allowed_roles):
    """
    Décorateur pour restreindre l'accès à certaines vues selon le rôle de l'utilisateur.
    allowed_roles : liste de rôles autorisés, ex : ['admin', 'superadmin']
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrap(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "❌ Vous devez être connecté pour accéder à cette page.")
                return redirect('login')
            
            if request.user.role in allowed_roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            messages.error(request, f"❌ Vous êtes connecté en tant que {request.user.role}, mais vous n'êtes pas autorisé à accéder à cette page.")
            return redirect('home')
        return wrap
    return decorator


def agent_required(view_func):
    """Décorateur pour vérifier que l'utilisateur est un agent ou plus"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not request.user.is_agent_or_above():
            messages.error(request, "Accès non autorisé. Vous devez être agent, admin ou super admin.")
            return redirect('index')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required(view_func):
    """Décorateur pour vérifier que l'utilisateur est un admin ou plus"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Vérifier si l'utilisateur a le rôle admin ou superadmin, OU est superuser Django
        if not (request.user.is_admin_or_above() or request.user.is_superuser):
            messages.error(request, "Accès non autorisé. Vous devez être administrateur ou super administrateur.")
            return redirect('index')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def superadmin_required(view_func):
    """Décorateur pour vérifier que l'utilisateur est un super admin"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if request.user.role != 'superadmin':
            messages.error(request, "Accès non autorisé. Vous devez être super administrateur.")
            return redirect('index')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def region_required(view_func):
    """Décorateur pour vérifier que l'utilisateur a une région assignée"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not (request.user.region or request.user.prefecture):
            messages.error(request, "Aucune région assignée. Contactez votre administrateur.")
            return redirect('index')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def ajax_login_required(view_func):
    """Décorateur pour les vues AJAX qui nécessitent une authentification"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentification requise'}, status=401)
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def can_manage_declaration(user, declaration):
    """Vérifie si un utilisateur peut gérer une déclaration donnée"""
    if user.role == 'superadmin':
        return True
    
    if user.role == 'admin':
        # Admin peut gérer dans sa région
        return declaration.region == user.region if user.region else True
    
    if user.role == 'agent':
        # Agent peut gérer dans sa région/préfecture
        if user.region:
            return declaration.region == user.region
        elif user.prefecture:
            return declaration.prefecture == user.prefecture
    
    return False


def can_manage_user(manager, target_user):
    """Vérifie si un utilisateur peut gérer un autre utilisateur"""
    if manager.role == 'superadmin':
        return True
    
    if manager.role == 'admin':
        # Admin peut gérer les citoyens et agents de sa région
        if target_user.role in ['citoyen', 'agent']:
            return target_user.region == manager.region if manager.region else True
        return False
    
    return False


def require_permission(permission_name):
    """Décorateur pour vérifier une permission Django spécifique"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            if not request.user.has_perm(permission_name):
                messages.error(request, f"Permission requise : {permission_name}")
                return redirect('index')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
""