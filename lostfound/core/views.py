from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.exceptions import ValidationError

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
            objets_resultats = objets_resultats.filter(
                Q(lieuPerte__quartier__icontains=lieu) |
                Q(lieuPerte__prefecture__icontains=lieu) |
                Q(lieuPerte__region__icontains=lieu)
            )
        if date_perte:
            objets_resultats = objets_resultats.filter(dateDeclaration__date=date_perte)

    objets_recents = Objet.objects.order_by('-dateDeclaration')[:3]
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


# ============================================================================
# VUES POUR LES NOUVEAUX MODÈLES
# ============================================================================
from .models import Localisation, Declaration, Reclamation, Notification
from .forms import (
    LocalisationForm, ObjetForm, ObjetQuickForm, DeclarationForm,
    ReclamationForm, ValidationDeclarationForm, ValidationReclamationForm,
    ObjetSearchForm
)
from django.core.paginator import Paginator
from django.utils import timezone


# ---------------------------
# Vues pour les Objets
# ---------------------------
def objets_publies_list(request):
    """Liste des objets publiés (perdus et trouvés)."""
    objets = Objet.objects.filter(etat='PUBLIE').order_by('-dateDeclaration')
    
    # Recherche
    form = ObjetSearchForm(request.GET)
    if form.is_valid():
        if form.cleaned_data.get('typeObjet'):
            objets = objets.filter(typeObjet=form.cleaned_data['typeObjet'])
        if form.cleaned_data.get('nom'):
            objets = objets.filter(nom__icontains=form.cleaned_data['nom'])
        if form.cleaned_data.get('couleur'):
            objets = objets.filter(couleur__icontains=form.cleaned_data['couleur'])
        if form.cleaned_data.get('est_perdu') != '':
            est_perdu = form.cleaned_data['est_perdu'] == 'True'
            objets = objets.filter(est_perdu=est_perdu)
        if form.cleaned_data.get('etat'):
            objets = objets.filter(etat=form.cleaned_data['etat'])
    
    # Pagination
    paginator = Paginator(objets, 12)
    page = request.GET.get('page')
    objets_page = paginator.get_page(page)
    
    return render(request, 'objets/liste.html', {
        'objets': objets_page,
        'form': form,
        'total': objets.count()
    })


@login_required
def objet_declarer(request):
    """Déclarer un nouvel objet perdu ou trouvé."""
    if request.method == 'POST':
        form = ObjetQuickForm(request.POST, request.FILES)
        if form.is_valid():
            objet = form.save(commit=False)
            objet.save()
            
            # Créer une déclaration automatiquement
            type_decl = 'PERDU' if objet.est_perdu else 'TROUVE'
            Declaration.objects.create(
                utilisateur=request.user,
                objet=objet,
                type_declaration=type_decl,
                statut='SOUMIS'
            )
            
            # Créer une notification
            Notification.objects.create(
                utilisateur=request.user,
                titre="Déclaration créée",
                message=f"Votre déclaration pour '{objet.nom}' a été créée et est en attente de validation.",
                type_notification='SYSTEME'
            )
            
            messages.success(request, f"Objet '{objet.nom}' déclaré avec succès!")
            return redirect('mes_declarations')
    else:
        form = ObjetQuickForm()
    
    return render(request, 'objets/declarer.html', {'form': form})


def objet_detail(request, pk):
    """Détail d'un objet."""
    objet = get_object_or_404(Objet, pk=pk)
    peut_reclamer = objet.peut_etre_reclame() and request.user.is_authenticated
    
    return render(request, 'objets/detail.html', {
        'objet': objet,
        'peut_reclamer': peut_reclamer
    })


@login_required
def mes_objets(request):
    """Liste des objets déclarés par l'utilisateur connecté."""
    declarations = Declaration.objects.filter(utilisateur=request.user).order_by('-date_soumission')
    return render(request, 'objets/mes_objets.html', {'declarations': declarations})


@login_required
def mes_declarations(request):
    """Alias de mes_objets."""
    return mes_objets(request)


# ---------------------------
# Vues pour les Réclamations
# ---------------------------
@login_required
def reclamer_objet(request, objet_id):
    """Réclamer un objet trouvé."""
    objet = get_object_or_404(Objet, pk=objet_id)
    
    if not objet.peut_etre_reclame():
        messages.error(request, "Cet objet ne peut pas être réclamé actuellement.")
        return redirect('objet_detail', pk=objet_id)
    
    # Vérifier si l'utilisateur a déjà réclamé cet objet
    if Reclamation.objects.filter(utilisateur=request.user, objet=objet).exists():
        messages.warning(request, "Vous avez déjà réclamé cet objet.")
        return redirect('mes_reclamations')
    
    if request.method == 'POST':
        form = ReclamationForm(request.POST, request.FILES)
        if form.is_valid():
            reclamation = form.save(commit=False)
            reclamation.utilisateur = request.user
            reclamation.objet = objet
            reclamation.save()
            
            # Changer l'état de l'objet
            try:
                objet.change_etat('RECLAME')
            except ValidationError as e:
                # Log l'erreur mais continue le processus
                messages.warning(request, f"Note: L'état de l'objet n'a pas pu être changé: {str(e)}")
            
            # Créer une notification
            Notification.objects.create(
                utilisateur=request.user,
                titre="Réclamation enregistrée",
                message=f"Votre réclamation pour '{objet.nom}' a été enregistrée et sera vérifiée par un agent.",
                type_notification='SYSTEME'
            )
            
            messages.success(request, "Votre réclamation a été enregistrée avec succès!")
            return redirect('mes_reclamations')
    else:
        form = ReclamationForm()
    
    return render(request, 'reclamations/formulaire.html', {
        'form': form,
        'objet': objet
    })


@login_required
def mes_reclamations(request):
    """Liste des réclamations de l'utilisateur."""
    reclamations = Reclamation.objects.filter(utilisateur=request.user).order_by('-date_reclamation')
    return render(request, 'reclamations/mes_reclamations.html', {'reclamations': reclamations})


@login_required
def reclamation_detail(request, pk):
    """Détail d'une réclamation."""
    reclamation = get_object_or_404(Reclamation, pk=pk)
    
    # Vérifier que l'utilisateur a le droit de voir cette réclamation
    if reclamation.utilisateur != request.user and not request.user.can_validate_objects():
        messages.error(request, "Vous n'avez pas accès à cette réclamation.")
        return redirect('home')
    
    return render(request, 'reclamations/detail.html', {'reclamation': reclamation})


# ---------------------------
# Vues pour les Agents/Admin
# ---------------------------
@login_required
def agent_dashboard(request):
    """Tableau de bord pour les agents et administrateurs."""
    if not request.user.can_validate_objects():
        messages.error(request, "Accès réservé aux agents et administrateurs.")
        return redirect('home')
    
    # Statistiques
    declarations_en_attente = Declaration.objects.filter(statut='SOUMIS').count()
    reclamations_en_verification = Reclamation.objects.filter(statut='EN_VERIFICATION').count()
    objets_en_validation = Objet.objects.filter(etat='EN_VALIDATION').count()
    
    # Listes récentes
    declarations_recentes = Declaration.objects.filter(statut='SOUMIS').order_by('-date_soumission')[:5]
    reclamations_recentes = Reclamation.objects.filter(statut='EN_VERIFICATION').order_by('-date_reclamation')[:5]
    
    return render(request, 'agent/dashboard.html', {
        'declarations_en_attente': declarations_en_attente,
        'reclamations_en_verification': reclamations_en_verification,
        'objets_en_validation': objets_en_validation,
        'declarations_recentes': declarations_recentes,
        'reclamations_recentes': reclamations_recentes,
    })


@login_required
def agent_declarations(request):
    """Liste des déclarations à valider."""
    if not request.user.can_validate_objects():
        messages.error(request, "Accès réservé aux agents et administrateurs.")
        return redirect('home')
    
    declarations = Declaration.objects.all().order_by('-date_soumission')
    
    # Filtres
    statut = request.GET.get('statut')
    if statut:
        declarations = declarations.filter(statut=statut)
    
    paginator = Paginator(declarations, 20)
    page = request.GET.get('page')
    declarations_page = paginator.get_page(page)
    
    return render(request, 'agent/declarations.html', {'declarations': declarations_page})


@login_required
def agent_valider_declaration(request, pk):
    """Valider ou rejeter une déclaration."""
    if not request.user.can_validate_objects():
        messages.error(request, "Accès réservé aux agents et administrateurs.")
        return redirect('home')
    
    declaration = get_object_or_404(Declaration, pk=pk)
    
    if request.method == 'POST':
        form = ValidationDeclarationForm(request.POST, instance=declaration)
        if form.is_valid():
            declaration = form.save(commit=False)
            declaration.agent_validateur = request.user
            declaration.date_validation = timezone.now()
            declaration.save()
            
            # Changer l'état de l'objet selon la validation
            if declaration.statut == 'VALIDE':
                try:
                    declaration.objet.change_etat('VALIDE', request.user)
                    declaration.objet.change_etat('PUBLIE', request.user)
                except:
                    pass
            elif declaration.statut == 'REJETE':
                try:
                    declaration.objet.change_etat('REFUSE', request.user)
                except:
                    pass
            
            # Créer une notification pour l'utilisateur
            Notification.objects.create(
                utilisateur=declaration.utilisateur,
                titre=f"Déclaration {declaration.get_statut_display().lower()}",
                message=f"Votre déclaration pour '{declaration.objet.nom}' a été {declaration.get_statut_display().lower()}.",
                type_notification='SYSTEME'
            )
            
            messages.success(request, "Déclaration traitée avec succès!")
            return redirect('agent_declarations')
    else:
        form = ValidationDeclarationForm(instance=declaration)
    
    return render(request, 'agent/valider_declaration.html', {
        'form': form,
        'declaration': declaration
    })


@login_required
def agent_reclamations(request):
    """Liste des réclamations à vérifier."""
    if not request.user.can_validate_objects():
        messages.error(request, "Accès réservé aux agents et administrateurs.")
        return redirect('home')
    
    reclamations = Reclamation.objects.all().order_by('-date_reclamation')
    
    # Filtres
    statut = request.GET.get('statut')
    if statut:
        reclamations = reclamations.filter(statut=statut)
    
    paginator = Paginator(reclamations, 20)
    page = request.GET.get('page')
    reclamations_page = paginator.get_page(page)
    
    return render(request, 'agent/reclamations.html', {'reclamations': reclamations_page})


@login_required
def agent_valider_reclamation(request, pk):
    """Valider ou refuser une réclamation."""
    if not request.user.can_validate_objects():
        messages.error(request, "Accès réservé aux agents et administrateurs.")
        return redirect('home')
    
    reclamation = get_object_or_404(Reclamation, pk=pk)
    
    if request.method == 'POST':
        form = ValidationReclamationForm(request.POST, instance=reclamation)
        if form.is_valid():
            reclamation = form.save(commit=False)
            reclamation.agent_verificateur = request.user
            reclamation.date_verification = timezone.now()
            reclamation.save()
            
            # Changer l'état de l'objet selon la validation
            if reclamation.statut == 'VALIDEE':
                try:
                    reclamation.objet.change_etat('EN_VERIFICATION', request.user)
                    reclamation.objet.change_etat('RESTITUE', request.user)
                except:
                    pass
            elif reclamation.statut == 'REFUSEE':
                # Remettre l'objet en PUBLIE pour permettre d'autres réclamations
                try:
                    reclamation.objet.etat = 'PUBLIE'
                    reclamation.objet.save()
                except:
                    pass
            
            # Créer une notification pour l'utilisateur
            Notification.objects.create(
                utilisateur=reclamation.utilisateur,
                titre=f"Réclamation {reclamation.get_statut_display().lower()}",
                message=f"Votre réclamation pour '{reclamation.objet.nom}' a été {reclamation.get_statut_display().lower()}.",
                type_notification='SYSTEME'
            )
            
            messages.success(request, "Réclamation traitée avec succès!")
            return redirect('agent_reclamations')
    else:
        form = ValidationReclamationForm(instance=reclamation)
    
    return render(request, 'agent/valider_reclamation.html', {
        'form': form,
        'reclamation': reclamation
    })


# ---------------------------
# Vues pour les Notifications
# ---------------------------
@login_required
def mes_notifications(request):
    """Liste des notifications de l'utilisateur."""
    notifications = Notification.objects.filter(utilisateur=request.user).order_by('-date_creation')
    
    # Marquer les non-lues comme lues (optionnel)
    notifications_non_lues = notifications.filter(lu=False)
    
    paginator = Paginator(notifications, 20)
    page = request.GET.get('page')
    notifications_page = paginator.get_page(page)
    
    return render(request, 'notifications/liste.html', {
        'notifications': notifications_page,
        'non_lues': notifications_non_lues.count()
    })


@login_required
def notification_marquer_lue(request, pk):
    """Marquer une notification comme lue."""
    notification = get_object_or_404(Notification, pk=pk, utilisateur=request.user)
    notification.marquer_comme_lu()
    return redirect('mes_notifications')


@login_required
def notifications_marquer_toutes_lues(request):
    """Marquer toutes les notifications comme lues."""
    Notification.objects.filter(utilisateur=request.user, lu=False).update(
        lu=True,
        date_lecture=timezone.now()
    )
    messages.success(request, "Toutes les notifications ont été marquées comme lues.")
    return redirect('mes_notifications')
