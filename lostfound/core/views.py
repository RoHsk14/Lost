from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

from .models import Signalement, Objet, Utilisateur, CommentaireAnonyme
from .forms import SignalementForm, SearchForm, CommentaireAnonymeForm
from .decorators import role_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .forms import AdminForm  # formulaire qu’on va créer
from rest_framework import viewsets
from .models import Region, Prefecture, StructureLocale, Signalement
from .serializers import RegionSerializer, PrefectureSerializer, StructureLocaleSerializer, SignalementSerializer


from django.shortcuts import render, redirect
# from core.forms import AdminCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

def superadmin_required(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(superadmin_required)
def creer_admin(request):
    if request.method == 'POST':
        form = AdminForm(request.POST)
        if form.is_valid():
            admin = form.save(commit=False)
            admin.role = 'admin'
            admin.save()
            messages.success(request, "Admin créé avec succès ✅")
            return redirect('superadmin_dashboard')
    else:
        form = AdminForm()
    return render(request, 'superadmin/creer_admin.html', {'form': form})


class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer

# class PrefectureViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = Prefecture.objects.all()
#     serializer_class = PrefectureSerializer

class PrefectureViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PrefectureSerializer

    def get_queryset(self):
        queryset = Prefecture.objects.all()
        region_id = self.request.query_params.get('region', None)
        if region_id is not None:
            queryset = queryset.filter(region__id=region_id)
        return queryset


class StructureLocaleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StructureLocale.objects.all()
    serializer_class = StructureLocaleSerializer

class SignalementViewSet(viewsets.ModelViewSet):
    queryset = Signalement.objects.all()
    serializer_class = SignalementSerializer
User = get_user_model()

# Liste des admins existants (déjà fait)
@login_required
@role_required(['superadmin'])
def superadmin_gestion_admins(request):
    admins = User.objects.filter(role='admin')
    return render(request, 'superadmin/gestion_admins.html', {'admins': admins})

# Créer un nouvel admin
@login_required
@role_required(['superadmin'])
# def superadmin_create_admin(request):
#     if request.method == 'POST':
#         form = AdminForm(request.POST)
#         if form.is_valid():
#             admin = form.save(commit=False)
#             admin.role = 'admin'
#             # Générer un mot de passe par défaut si vide
#             if not admin.password:
#                 admin.set_password('Admin@123')
#             else:
#                 admin.set_password(admin.password)
#             admin.save()
#             messages.success(request, f"Admin {admin.username} créé avec succès !")
#             return redirect('superadmin_gestion_admins')
#     else:
#         form = AdminForm()
#     return render(request, 'superadmin/admin_form.html', {'form': form, 'title': 'Créer un admin'})

# Modifier un admin existant
@login_required
@role_required(['superadmin'])
def superadmin_edit_admin(request, pk):
    admin = get_object_or_404(User, pk=pk, role='admin')
    if request.method == 'POST':
        form = AdminForm(request.POST, instance=admin)
        if form.is_valid():
            form.save()
            messages.success(request, f"Admin {admin.username} modifié avec succès !")
            return redirect('superadmin_gestion_admins')
    else:
        form = AdminForm(instance=admin)
    return render(request, 'superadmin/admin_form.html', {'form': form, 'title': 'Modifier un admin'})

# Supprimer un admin
@login_required
@role_required(['superadmin'])
def superadmin_delete_admin(request, pk):
    admin = get_object_or_404(User, pk=pk, role='admin')
    if request.method == 'POST':
        admin.delete()
        messages.warning(request, f"Admin {admin.username} supprimé.")
        return redirect('superadmin_gestion_admins')
    return render(request, 'superadmin/admin_delete_confirm.html', {'admin': admin})


User = get_user_model()

# ---------------------------
# Redirection selon rôle après login
# ---------------------------
@login_required
def home(request):
    if request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'superadmin'):
        return redirect('superadmin_dashboard')
    elif hasattr(request.user, 'role') and request.user.role == 'admin':
        return redirect('togo_admin:dashboard')  # Nouvelle interface TailAdmin
    elif request.user.is_staff:  # Admin Django classique
        return redirect('togo_admin:dashboard')
    else:
        return redirect('utilisateur_dashboard')

def home_redirect(request):
    user = request.user
    if user.is_authenticated:
        if user.is_superuser or (hasattr(user, 'role') and user.role == 'superadmin'):
            return redirect('superadmin_dashboard')
        elif hasattr(user, 'role') and user.role == 'admin':
            return redirect('togo_admin:dashboard')  # Nouvelle interface TailAdmin
        elif user.is_staff:  # Admin Django classique
            return redirect('togo_admin:dashboard')
    return redirect('index')

# ---------------------------
# Superadmin Views
# ---------------------------
@login_required
@role_required(['superadmin'])
def superadmin_dashboard(request):
    utilisateurs = User.objects.filter(role='admin')
    signalements = Signalement.objects.all()
    return render(request, 'superadmin/dashboard.html', {
        'utilisateurs': utilisateurs,
        'signalements': signalements,
    })

@login_required
@role_required(['superadmin'])
def superadmin_gestion_admins(request):
    admins = User.objects.filter(role='admin')
    return render(request, 'superadmin/gestion_admins.html', {'admins': admins})

@login_required
@role_required(['superadmin'])
def superadmin_users(request):
    utilisateurs = User.objects.all()
    return render(request, 'superadmin/utilisateurs.html', {'utilisateurs': utilisateurs})

# ---------------------------
# Admin Views
# ---------------------------
@login_required
@role_required(['admin'])
def admin_dashboard(request):
    # Filtre par région de l'utilisateur admin
    if request.user.region:
        signalements = Signalement.objects.filter(region=request.user.region)
    else:
        signalements = Signalement.objects.all()  # Si pas de région définie
    return render(request, 'admin/dashboard.html', {'signalements': signalements})

@login_required
@role_required(['admin'])
def admin_signalements(request):
    # Filtre par région de l'utilisateur admin
    if request.user.region:
        signalements = Signalement.objects.filter(region=request.user.region)
    else:
        signalements = Signalement.objects.all()
    return render(request, 'admin/signalements.html', {'signalements': signalements})

@login_required
@role_required(['admin'])
def admin_signalement_detail(request, pk):
    signalement = get_object_or_404(Signalement, pk=pk)
    return render(request, 'admin/signalement_detail.html', {'signalement': signalement})

# ---------------------------
# Utilisateur Views
# ---------------------------
@login_required
def utilisateur_dashboard(request):
    # Dashboard avec statistiques personnelles
    mes_signalements = Signalement.objects.filter(utilisateur=request.user)
    signalements_recents = Signalement.objects.all().order_by('-date_signalement')[:5]
    
    stats = {
        'mes_signalements_total': mes_signalements.count(),
        'mes_perdus': mes_signalements.filter(statut='perdu').count(),
        'mes_trouves': mes_signalements.filter(statut='trouve').count(),
        'mes_retournes': mes_signalements.filter(statut='retourne').count(),
    }
    
    context = {
        'mes_signalements': mes_signalements[:5],  # 5 derniers
        'signalements_recents': signalements_recents,
        'stats': stats,
    }
    return render(request, 'utilisateur/dashboard.html', context)

@login_required
def mes_signalements(request):
    """Page dédiée aux signalements de l'utilisateur connecté"""
    signalements = Signalement.objects.filter(utilisateur=request.user).order_by('-date_signalement')
    
    # Filtres
    statut_filter = request.GET.get('statut', '')
    if statut_filter:
        signalements = signalements.filter(statut=statut_filter)
    
    # Statistiques
    stats = {
        'total': signalements.count(),
        'perdus': signalements.filter(statut='perdu').count(),
        'trouves': signalements.filter(statut='trouve').count(),
        'retournes': signalements.filter(statut='retourne').count(),
    }
    
    context = {
        'signalements': signalements,
        'stats': stats,
        'statut_filter': statut_filter,
    }
    return render(request, 'utilisateur/mes_signalements.html', context)

@login_required
def utilisateur_signalement_detail(request, pk):
    signalement = get_object_or_404(Signalement, pk=pk)
    return render(request, 'utilisateur/signalement_detail.html', {'signalement': signalement})

# ---------------------------
# Pages publiques et recherche
# ---------------------------
def index(request):
    # Gestion de la recherche rapide depuis l'accueil
    nom = request.GET.get('nom')
    lieu = request.GET.get('lieu')
    date_perte = request.GET.get('date_perte')

    objets_resultats = []
    recherche_effectuee = False

    if nom or lieu or date_perte:
        recherche_effectuee = True
        objets_resultats = Objet.objects.all()
        if nom:
            objets_resultats = objets_resultats.filter(nom__icontains=nom)
        if lieu:
            objets_resultats = objets_resultats.filter(lieu_trouve__icontains=lieu)
        if date_perte:
            objets_resultats = objets_resultats.filter(date_creation__date=date_perte)

    # Récupération des signalements d'objets TROUVÉS (statut 'trouve')
    objets_trouves = Signalement.objects.filter(
        statut='trouve'
    ).select_related('objet', 'utilisateur', 'region', 'prefecture').order_by('-date_signalement')[:6]
    
    # Récupération des signalements d'objets PERDUS (statut 'perdu')
    objets_perdus = Signalement.objects.filter(
        statut='perdu'
    ).select_related('objet', 'utilisateur', 'region', 'prefecture').order_by('-date_signalement')[:6]

    # Récupération des signalements récents (tous types confondus)
    signalements_recents = Signalement.objects.select_related(
        'objet', 'utilisateur', 'region', 'prefecture'
    ).order_by('-date_signalement')[:4]

    # Statistiques pour l'affichage
    stats = {
        'total_objets': Objet.objects.count(),
        'total_signalements': Signalement.objects.count(),
        'signalements_perdus': Signalement.objects.filter(statut='perdu').count(),
        'signalements_trouves': Signalement.objects.filter(statut='trouve').count(),
    }

    return render(request, 'index.html', {
        'objets_resultats': objets_resultats,
        'objets_trouves': objets_trouves,  # Signalements d'objets trouvés
        'objets_perdus': objets_perdus,    # Signalements d'objets perdus
        'signalements_recents': signalements_recents,  # Tous signalements récents
        'recherche_effectuee': recherche_effectuee,
        'stats': stats,
    })

def search_objets(request):
    form = SearchForm(request.GET or None)
    objets = Objet.objects.all()
    if form.is_valid():
        nom = form.cleaned_data.get('nom')
        lieu = form.cleaned_data.get('lieu')
        date_perte = form.cleaned_data.get('date_perte')
        if nom:
            objets = objets.filter(nom__icontains=nom)
        if lieu:
            objets = objets.filter(lieu__icontains=lieu)
        if date_perte:
            objets = objets.filter(date_perte=date_perte)
    return render(request, 'search.html', {'form': form, 'objets': objets})

def objet_detail(request, pk):
    objet = get_object_or_404(Objet, pk=pk)
    return render(request, 'objet_detail.html', {'objet': objet})

# ---------------------------
# Gestion des signalements
# ---------------------------
def signalements_list(request):
    signalements = Signalement.objects.select_related('objet', 'utilisateur').all().order_by('-date_signalement')
    return render(request, 'signalements_list.html', {'signalements': signalements})

def signalement_detail(request, pk):
    signalement = get_object_or_404(Signalement, pk=pk)
    
    # Récupérer les commentaires anonymes pour ce signalement
    commentaires = CommentaireAnonyme.objects.filter(signalement=signalement).order_by('-date_creation')
    
    # Formulaire pour ajouter un commentaire anonyme
    if request.method == 'POST':
        form = CommentaireAnonymeForm(request.POST)
        if form.is_valid():
            commentaire = form.save(commit=False)
            commentaire.signalement = signalement
            commentaire.save()
            messages.success(request, "💬 Votre commentaire a été ajouté avec succès !")
            return redirect('signalement_detail', pk=pk)
        else:
            messages.error(request, "❌ Erreur lors de l'ajout du commentaire.")
    else:
        form = CommentaireAnonymeForm()
    
    context = {
        'signalement': signalement,
        'commentaires': commentaires,
        'form': form,
        'nb_commentaires': commentaires.count()
    }
    
    return render(request, 'signalement_detail.html', context)

# def signalement_add(request):
#     regions = Region.objects.all()
#     if request.method == 'POST':
#         form = SignalementForm(request.POST, request.FILES)
#         if form.is_valid():
#             objet_nom = form.cleaned_data.get('objet')
#             objet, _ = Objet.objects.get_or_create(nom=objet_nom)
#             signalement = form.save(commit=False)
#             signalement.objet = objet
#             if request.user.is_authenticated:
#                 signalement.utilisateur = request.user
#             else:
#                 messages.error(request, "❌ Vous devez être connecté pour signaler un objet.")
#                 return redirect('login')
#             signalement.save()
#             messages.success(request, "✅ Signalement ajouté avec succès !")
#             return redirect('signalements_list')
#         else:
#             messages.error(request, "❌ Erreur lors de l’ajout du signalement.")
#     else:
#         form = SignalementForm()
#     return render(request, 'signalement_add.html', {'form': form})

def signalement_add(request):
    regions = Region.objects.all()
    if request.method == 'POST':
        form = SignalementForm(request.POST, request.FILES)
        if form.is_valid():
            # Le formulaire va gérer la création de l'objet automatiquement
            signalement = form.save(commit=False)

            if request.user.is_authenticated:
                signalement.utilisateur = request.user
            else:
                messages.error(request, "❌ Vous devez être connecté pour signaler un objet.")
                return redirect('login')

            # Récupérer les données géographiques si elles sont fournies
            region_id = request.POST.get('region')
            prefecture_id = request.POST.get('prefecture')
            structure_id = request.POST.get('structure')

            if region_id:
                try:
                    signalement.region = Region.objects.get(id=region_id)
                except Region.DoesNotExist:
                    pass

            if prefecture_id:
                try:
                    signalement.prefecture = Prefecture.objects.get(id=prefecture_id)
                except Prefecture.DoesNotExist:
                    pass

            if structure_id:
                try:
                    signalement.structure_locale = StructureLocale.objects.get(id=structure_id)
                except StructureLocale.DoesNotExist:
                    pass

            signalement.save()
            messages.success(request, "✅ Signalement ajouté avec succès !")
            return redirect('signalements_list')
        else:
            messages.error(request, "❌ Erreur lors de l’ajout du signalement.")
    else:
        form = SignalementForm()

    return render(request, 'signalement_add.html', {
        'form': form,
        'regions': regions
    })


def signalement_edit(request, pk):
    signalement = get_object_or_404(Signalement, pk=pk)
    if request.method == 'POST':
        form = SignalementForm(request.POST, request.FILES, instance=signalement)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Signalement modifié avec succès !")
            return redirect('signalement_detail', pk=signalement.pk)
        else:
            messages.error(request, "❌ Erreur lors de la modification.")
    else:
        form = SignalementForm(instance=signalement)
    return render(request, 'signalement_edit.html', {'form': form, 'signalement': signalement})

def signalement_delete(request, pk):
    signalement = get_object_or_404(Signalement, pk=pk)
    if request.method == 'POST':
        signalement.delete()
        messages.warning(request, "🗑️ Signalement supprimé avec succès.")
        return redirect('signalements_list')
    return render(request, 'signalement_delete.html', {'signalement': signalement})

# ---------------------------
# Liste des objets
# ---------------------------
def objets_list(request):
    """Vue pour afficher tous les objets trouvés"""
    # Récupérer uniquement les signalements d'objets trouvés
    search_query = request.GET.get('search', '')
    
    if search_query:
        objets_trouves = Signalement.objects.filter(
            statut='trouve'
        ).filter(
            Q(objet__nom__icontains=search_query) |
            Q(objet__description__icontains=search_query) |
            Q(lieu__icontains=search_query) |
            Q(utilisateur__username__icontains=search_query)
        ).select_related('objet', 'utilisateur', 'region', 'prefecture').order_by('-date_signalement')
    else:
        objets_trouves = Signalement.objects.filter(
            statut='trouve'
        ).select_related('objet', 'utilisateur', 'region', 'prefecture').order_by('-date_signalement')
    
    context = {
        'objets_trouves': objets_trouves,
        'search_query': search_query,
        'total_count': objets_trouves.count(),
    }
    return render(request, 'objets_list.html', context)

def objets_perdus_list(request):
    """Vue pour afficher tous les objets perdus"""
    # Récupérer uniquement les signalements d'objets perdus
    search_query = request.GET.get('search', '')
    
    if search_query:
        objets_perdus = Signalement.objects.filter(
            statut='perdu'
        ).filter(
            Q(objet__nom__icontains=search_query) |
            Q(objet__description__icontains=search_query) |
            Q(lieu__icontains=search_query) |
            Q(utilisateur__username__icontains=search_query)
        ).select_related('objet', 'utilisateur', 'region', 'prefecture').order_by('-date_signalement')
    else:
        objets_perdus = Signalement.objects.filter(
            statut='perdu'
        ).select_related('objet', 'utilisateur', 'region', 'prefecture').order_by('-date_signalement')
    
    context = {
        'objets_perdus': objets_perdus,
        'search_query': search_query,
        'total_count': objets_perdus.count(),
    }
    return render(request, 'objets_perdus_list.html', context)

def objets_recents(request):
    objets = Objet.objects.order_by('-date_creation')[:6]
    return render(request, 'home.html', {'objets': objets})

# ---------------------------
# Liste des utilisateurs
# ---------------------------
def utilisateurs_list(request):
    utilisateurs = Utilisateur.objects.all()
    return render(request, 'utilisateurs_list.html', {'utilisateurs': utilisateurs})

# ---------------------------
# Authentification
# ---------------------------
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, "Connexion réussie !")
            
            # Redirection intelligente selon le rôle
            if user.is_superuser or (hasattr(user, 'role') and user.role == 'superadmin'):
                return redirect('superadmin_dashboard')
            elif hasattr(user, 'role') and user.role == 'admin':
                return redirect('togo_admin:dashboard')  # Vers la nouvelle interface TailAdmin
            elif user.is_staff:  # Admin Django classique
                return redirect('togo_admin:dashboard')
            else:
                return redirect('home')  # Utilisateurs normaux
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect('home')


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def ajouter_commentaire_ajax(request, signalement_id):
    """Vue AJAX pour ajouter un commentaire anonyme"""
    if request.method == 'POST':
        try:
            signalement = get_object_or_404(Signalement, id=signalement_id)
            
            # Parser les données JSON
            data = json.loads(request.body)
            
            # Créer le commentaire
            commentaire = CommentaireAnonyme.objects.create(
                signalement=signalement,
                pseudo=data.get('pseudo', ''),
                commentaire=data.get('commentaire', ''),
                contact=data.get('contact', '')
            )
            
            # Retourner la réponse JSON
            return JsonResponse({
                'success': True,
                'commentaire': {
                    'id': commentaire.id,
                    'pseudo': commentaire.get_display_name(),
                    'commentaire': commentaire.commentaire,
                    'date': commentaire.date_creation.strftime('%d/%m/%Y à %H:%M')
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return redirect('register')
        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur existe déjà.")
            return redirect('register')
        if User.objects.filter(email=email).exists():
            messages.error(request, "Un compte utilise déjà cet e-mail.")
            return redirect('register')

        user = User.objects.create_user(username=username, email=email, password=password1)
        user.save()
        login(request, user)
        messages.success(request, f"Bienvenue {user.username} 👋 Votre compte a été créé avec succès.")
        return redirect('home')

    return render(request, 'register.html')


# =============================================================================
# VUES UTILISATEUR SUPPLÉMENTAIRES
# =============================================================================

@login_required
def utilisateur_profil(request):
    """Vue pour gérer le profil utilisateur"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_profile':
            # Mise à jour des informations personnelles
            user = request.user
            user.username = request.POST.get('username', user.username)
            user.email = request.POST.get('email', user.email)
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.save()
            
            messages.success(request, "✅ Vos informations ont été mises à jour avec succès.")
            return redirect('utilisateur_profil')
            
        elif action == 'change_password':
            # Changement de mot de passe
            from django.contrib.auth import update_session_auth_hash
            from django.contrib.auth.forms import PasswordChangeForm
            
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)  # Important!
                messages.success(request, "🔒 Votre mot de passe a été changé avec succès.")
                return redirect('utilisateur_profil')
            else:
                for error in form.errors.values():
                    messages.error(request, error[0])
                return redirect('utilisateur_profil')
    
    # Calcul des statistiques utilisateur
    user_signalements = Signalement.objects.filter(utilisateur=request.user)
    stats = {
        'total': user_signalements.count(),
        'perdus': user_signalements.filter(statut='perdu').count(),
        'trouves': user_signalements.filter(statut='trouve').count(),
        'retournes': user_signalements.filter(statut='retourne').count(),
    }
    
    # Calcul du taux de réussite
    if stats['total'] > 0:
        stats['taux_reussite'] = round((stats['retournes'] / stats['total']) * 100, 1)
    else:
        stats['taux_reussite'] = 0
    
    context = {
        'stats': stats
    }
    
    return render(request, 'utilisateur/profil.html', context)


@login_required 
def utilisateur_parametres(request):
    """Vue pour gérer les paramètres utilisateur"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_notifications':
            # Mise à jour des préférences de notifications
            # Ici vous pourriez sauvegarder dans un modèle UserPreferences
            messages.success(request, "🔔 Vos préférences de notifications ont été sauvegardées.")
            
        elif action == 'update_privacy':
            # Mise à jour des préférences de confidentialité
            messages.success(request, "🔒 Vos paramètres de confidentialité ont été mis à jour.")
            
        elif action == 'update_location':
            # Mise à jour des paramètres de localisation
            messages.success(request, "📍 Vos paramètres de localisation ont été sauvegardés.")
            
        elif action == 'update_interface':
            # Mise à jour des préférences d'interface
            messages.success(request, "🎨 Vos préférences d'interface ont été appliquées.")
        
        return redirect('utilisateur_parametres')
    
    return render(request, 'utilisateur/parametres.html')
