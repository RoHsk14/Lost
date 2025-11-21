# from django.shortcuts import redirect
# from django.contrib import messages

# def role_required(roles):
#     def decorator(view_func):
#         def wrapper(request, *args, **kwargs):
#             if not request.user.is_authenticated:
#                 messages.error(request, "Connectez-vous pour accéder à cette page.")
#                 return redirect('login')
#             if request.user.role not in roles:
#                 messages.error(request, "Accès refusé.")
#                 return redirect('home')
#             return view_func(request, *args, **kwargs)
#         return wrapper
#     return decorator
# core/decorators.py
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

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
""