from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

from .models import Signalement, Objet, Utilisateur
from .forms import SignalementForm, SearchForm
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
    if request.user.is_superuser or request.user.role == 'superadmin':
        return redirect('superadmin_dashboard')
    elif request.user.role == 'admin':
        return redirect('admin_dashboard')
    else:
        return redirect('utilisateur_dashboard')

def home_redirect(request):
    user = request.user
    if user.is_authenticated:
        if user.role == 'admin':
            return redirect('admin_dashboard')
        elif user.role == 'superadmin':
            return redirect('superadmin_dashboard')
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
    signalements = Signalement.objects.filter(zone=request.user.zone)
    return render(request, 'admin/dashboard.html', {'signalements': signalements})

@login_required
@role_required(['admin'])
def admin_signalements(request):
    signalements = Signalement.objects.filter(zone=request.user.zone)
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
    signalements = Signalement.objects.filter(zone=request.user.zone)
    return render(request, 'index.html', {'signalements': signalements})

@login_required
def utilisateur_signalement_detail(request, pk):
    signalement = get_object_or_404(Signalement, pk=pk)
    return render(request, 'utilisateur/signalement_detail.html', {'signalement': signalement})

# ---------------------------
# Pages publiques et recherche
# ---------------------------
def index(request):
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

    objets_recents = Objet.objects.order_by('-date_creation')[:3]
    signalements = Signalement.objects.order_by('-date_signalement')[:3]

    return render(request, 'index.html', {
        'objets_resultats': objets_resultats,
        'objets_recents': objets_recents,
        'signalements': signalements,
        'recherche_effectuee': recherche_effectuee,
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
    return render(request, 'signalement_detail.html', {'signalement': signalement})

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
            objet_nom = form.cleaned_data.get('objet')
            objet, _ = Objet.objects.get_or_create(nom=objet_nom)

            signalement = form.save(commit=False)
            signalement.objet = objet

            if request.user.is_authenticated:
                signalement.utilisateur = request.user
            else:
                messages.error(request, "❌ Vous devez être connecté pour signaler un objet.")
                return redirect('login')

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
    objets = Objet.objects.all()
    return render(request, 'objets_list.html', {'objets': objets})

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
            return redirect('home')
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect('home')

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
