from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Avg, F
from django.db.models.functions import TruncMonth, TruncDate
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth.decorators import user_passes_test
import json

from .models import (
    Declaration, Reclamation, Utilisateur, Region, Prefecture, 
    StatistiqueRegion, ActionLog, CategorieObjet, StructureLocale
)
from .forms import AdminForm
from django.contrib.auth.hashers import make_password
from .decorators import admin_required, superadmin_required
from .utils import create_notification, log_action, update_region_statistics


# ============ VUES ADMIN ============

@admin_required
def admin_dashboard(request):
    """Dashboard principal pour les administrateurs avec statistiques réelles"""
    from datetime import datetime, timedelta
    from django.db.models import Count, Q
    from django.utils import timezone
    
    # Période par défaut : 30 derniers jours
    periode = request.GET.get('periode', '30')
    
    # Calcul de la date de début selon la période
    if periode == '7':
        date_debut = timezone.now() - timedelta(days=7)
        titre_periode = "7 derniers jours"
    elif periode == '30':
        date_debut = timezone.now() - timedelta(days=30)
        titre_periode = "30 derniers jours"
    elif periode == '90':
        date_debut = timezone.now() - timedelta(days=90)
        titre_periode = "3 derniers mois"
    elif periode == '365':
        date_debut = timezone.now() - timedelta(days=365)
        titre_periode = "12 derniers mois"
    else:
        date_debut = timezone.now() - timedelta(days=30)
        titre_periode = "30 derniers jours"
    
    # === STATISTIQUES RÉELLES ===
    
    # 1. Déclarations
    total_declarations = Declaration.objects.count()
    declarations_periode = Declaration.objects.filter(date_declaration__gte=date_debut).count()
    declarations_en_attente = Declaration.objects.filter(statut='cree').count()
    declarations_validees = Declaration.objects.filter(statut__in=['publie', 'restitue']).count()
    
    # 2. Utilisateurs
    total_utilisateurs = Utilisateur.objects.count()
    nouveaux_utilisateurs = Utilisateur.objects.filter(date_joined__gte=date_debut).count()
    utilisateurs_actifs = Utilisateur.objects.filter(last_login__gte=date_debut).count()
    
    # 3. Agents
    total_agents = Utilisateur.objects.filter(role='agent').count()
    agents_actifs = Utilisateur.objects.filter(role='agent', actif=True).count()
    agents_periode = Utilisateur.objects.filter(role='agent', date_joined__gte=date_debut).count()
    
    # 4. Objets retrouvés/perdus
    objets_retrouves = Declaration.objects.filter(
        statut='restitue',
        date_restitution__gte=date_debut
    ).count()
    objets_perdus = Declaration.objects.filter(
        type_declaration='perte',
        date_declaration__gte=date_debut
    ).count()
    objets_trouves = Declaration.objects.filter(
        type_declaration='trouvaille',
        date_declaration__gte=date_debut
    ).count()
    
    # 5. Taux de réussite
    taux_restitution = 0
    if total_declarations > 0:
        restitutions = Declaration.objects.filter(statut='restitue').count()
        taux_restitution = round((restitutions / total_declarations) * 100, 1)
    
    # === DONNÉES POUR LES GRAPHIQUES ===
    
    # Évolution mensuelle des déclarations (6 derniers mois)
    evolution_data = []
    for i in range(6):
        date_fin = timezone.now() - timedelta(days=30*i)
        date_debut_mois = date_fin - timedelta(days=30)
        count = Declaration.objects.filter(
            date_declaration__gte=date_debut_mois,
            date_declaration__lte=date_fin
        ).count()
        evolution_data.append({
            'mois': date_fin.strftime('%b'),
            'declarations': count
        })
    evolution_data.reverse()
    
    # Répartition par type
    repartition_types = Declaration.objects.values('type_declaration').annotate(
        count=Count('id')
    )
    
    # Répartition par statut
    repartition_statuts = Declaration.objects.values('statut').annotate(
        count=Count('id')
    )
    
    # === ACTIVITÉS RÉCENTES ===
    
    # Dernières déclarations en attente
    declarations_recentes = Declaration.objects.filter(
        statut='cree'
    ).select_related('declarant').order_by('-date_declaration')[:5]
    
    # Agents les plus actifs avec statistiques détaillées
    agents_actifs_stats = Utilisateur.objects.filter(
        role='agent',
        actif=True
    ).select_related('region').annotate(
        nb_validations=Count('declarations_validees'),
        declarations_traitees=Count('mes_declarations', filter=Q(mes_declarations__statut__in=['valide', 'publie', 'restitue'])),
    ).order_by('-nb_validations')[:5]
    
    # Ajouter score d'efficacité calculé pour chaque agent
    for agent in agents_actifs_stats:
        total_declarations = agent.declarations_traitees + agent.nb_validations
        agent.score_efficacite = round((agent.nb_validations / max(total_declarations, 1)) * 100, 1) if total_declarations > 0 else 95
    
    # Contexte pour le template
    context = {
        'stats': {
            'total_declarations': total_declarations,
            'declarations_periode': declarations_periode,
            'declarations_en_attente': declarations_en_attente,
            'declarations_validees': declarations_validees,
            'total_utilisateurs': total_utilisateurs,
            'nouveaux_utilisateurs': nouveaux_utilisateurs,
            'utilisateurs_actifs': utilisateurs_actifs,
            'total_agents': total_agents,
            'agents_actifs': agents_actifs,
            'agents_periode': agents_periode,
            'objets_retrouves': objets_retrouves,
            'objets_perdus': objets_perdus,
            'objets_trouves': objets_trouves,
            'taux_restitution': taux_restitution,
        },
        'periode': periode,
        'titre_periode': titre_periode,
        'evolution_data': evolution_data,
        'repartition_types': list(repartition_types),
        'repartition_statuts': list(repartition_statuts),
        'declarations_recentes': declarations_recentes,
        'agents_actifs': agents_actifs_stats,
    }
    
    return render(request, 'admin/dashboard.html', context)


@admin_required
def statistics(request):
    """Page des statistiques détaillées"""
    user = request.user
    
    # Filtrer par région de l'admin
    region_filter = Q()
    if user.region:
        region_filter = Q(region=user.region)
    
    # KPI principaux
    kpi = {
        'total_declarations': Declaration.objects.filter(region_filter).count(),
        'resolution_rate': 75.5,  # Calculer le taux réel
        'avg_response_time': 24,  # Temps moyen en heures
        'user_satisfaction': 4.2,
    }
    
    # Données pour les graphiques
    evolution_data = {
        'labels': json.dumps(['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun']),
        'declarations': json.dumps([10, 15, 12, 20, 18, 25]),
        'resolutions': json.dumps([8, 12, 10, 16, 15, 20])
    }
    
    # Statistiques par statut
    status_stats = {
        'pending': Declaration.objects.filter(region_filter & Q(statut='cree')).count(),
        'validated': Declaration.objects.filter(region_filter & Q(statut='valide')).count(),
        'published': Declaration.objects.filter(region_filter & Q(statut='publie')).count(),
        'returned': Declaration.objects.filter(region_filter & Q(statut='restitue')).count(),
    }
    
    context = {
        'kpi': kpi,
        'evolution_data': evolution_data,
        'status_stats': status_stats,
        'agent_stats': [],  # Liste des agents avec leurs stats
        'category_stats': [],  # Stats par catégorie
        'advanced_stats': []  # Stats avancées par région
    }
    
    return render(request, 'admin/statistics.html', context)


@admin_required
def regions_list(request):
    """Gestion des régions et préfectures"""
    from django.db.models import Count
    
    user = request.user
    
    # Régions accessibles selon le rôle
    if user.role == 'superadmin':
        regions = Region.objects.all()
    else:
        regions = Region.objects.filter(id=user.region_id) if user.region else Region.objects.none()
    
    # Ajouter les statistiques pour chaque région
    regions = regions.prefetch_related('prefectures').annotate(
        agents_count=Count('utilisateur', filter=Q(utilisateur__role='agent')),
        declarations_count=Count('declaration')
    )
    
    # Statistiques globales
    stats = {
        'total_regions': Region.objects.count(),
        'total_prefectures': Prefecture.objects.count(),
        'total_agents': Utilisateur.objects.filter(role='agent').count(),
        'coverage_rate': 85.0  # Pourcentage de couverture
    }
    
    context = {
        'regions': regions,
        'stats': stats
    }
    
    return render(request, 'admin/regions_list.html', context)


@admin_required
def settings(request):
    """Paramètres et configuration du système"""
    if request.method == 'POST':
        # Traitement des paramètres
        section = request.GET.get('section', 'general')
        
        if section == 'general':
            # Sauvegarder les paramètres généraux
            messages.success(request, "Paramètres généraux enregistrés avec succès.")
        elif section == 'email':
            # Sauvegarder les paramètres email
            messages.success(request, "Configuration email enregistrée avec succès.")
        
        return redirect('togo_admin:settings')
    
    # Paramètres actuels (en dur pour la démo)
    settings_data = {
        'site_name': 'TogoRetrouvé',
        'site_url': 'https://togoretrouve.tg',
        'contact_email': 'contact@togoretrouve.tg',
        'support_phone': '+228 XX XX XX XX',
        'site_description': 'Plateforme nationale de gestion des objets trouvés et perdus au Togo',
        'max_file_size': 5,
        'max_photos_per_declaration': 5,
        'validation_timeout': 48,
        'publication_duration': 90
    }
    
    email_settings = {
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'smtp_username': '',
        'smtp_use_tls': True
    }
    
    system_info = {
        'database_type': 'SQLite',
        'disk_usage': 25,
        'disk_used': '2.5 GB',
        'disk_total': '10 GB',
        'last_backup': None
    }
    
    # Logs récents
    recent_logs = ActionLog.objects.select_related('utilisateur').order_by('-date_action')[:10]
    
    context = {
        'settings': settings_data,
        'email_settings': email_settings,
        'system_info': system_info,
        'recent_logs': recent_logs
    }
    
    return render(request, 'admin/settings.html', context)


@admin_required
def agents_list(request):
    """Gestion des agents pour l'admin - TEMPORAIREMENT DÉSACTIVÉ"""
    from django.http import HttpResponseNotFound
    return HttpResponseNotFound("Page des agents temporairement indisponible")


@admin_required
def admin_declarations(request):
    """Gestion des déclarations par les admins"""
    user = request.user
    
    # Filtres
    statut_filter = request.GET.get('statut', 'all')
    search = request.GET.get('search', '')
    region_filter_param = request.GET.get('region', '')
    
    # Query de base
    declarations = Declaration.objects.select_related(
        'declarant', 'categorie', 'region', 'prefecture', 'agent_validateur'
    ).prefetch_related('reclamations')
    
    # Filtrer par région de l'admin si ce n'est pas un superadmin
    if user.region:
        declarations = declarations.filter(region=user.region)
    
    # Filtres supplémentaires
    if statut_filter != 'all':
        declarations = declarations.filter(statut=statut_filter)
    
    if search:
        declarations = declarations.filter(
            Q(nom_objet__icontains=search) |
            Q(description__icontains=search) |
            Q(numero_declaration__icontains=search) |
            Q(declarant__username__icontains=search)
        )
    
    if region_filter_param and user.role == 'superadmin':
        declarations = declarations.filter(region_id=region_filter_param)
    
    # Tri
    ordre = request.GET.get('ordre', '-date_declaration')
    declarations = declarations.order_by(ordre)
    
    # Pagination
    paginator = Paginator(declarations, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiques pour les onglets
    base_query = Declaration.objects.filter(
        region=user.region if user.region else Q()
    )
    
    stats_onglets = {
        'all': base_query.count(),
        'cree': base_query.filter(statut='cree').count(),
        'valide': base_query.filter(statut='valide').count(),
        'publie': base_query.filter(statut='publie').count(),
        'reclame': base_query.filter(statut='reclame').count(),
        'restitue': base_query.filter(statut='restitue').count(),
        'rejete': base_query.filter(statut='rejete').count(),
    }
    
    # Régions pour le filtre (si superadmin)
    regions = Region.objects.all() if user.role == 'superadmin' else []
    
    context = {
        'page_obj': page_obj,
        'statut_filter': statut_filter,
        'search': search,
        'region_filter': region_filter_param,
        'ordre': ordre,
        'stats_onglets': stats_onglets,
        'statuts_choices': Declaration.STATUT_CHOICES,
        'regions': regions,
        'is_superadmin': user.role == 'superadmin',
    }
    
    return render(request, 'admin/declarations.html', context)


@admin_required
def admin_users(request):
    """Gestion des utilisateurs avec statistiques détaillées"""
    user = request.user
    
    # Filtres
    role_filter = request.GET.get('role', 'all')
    search = request.GET.get('search', '')
    actif_filter = request.GET.get('actif', 'all')
    region_filter = request.GET.get('region_filter', '')
    
    # Query de base
    utilisateurs = Utilisateur.objects.select_related('region', 'prefecture')
    
    # Filtrer selon le rôle de l'utilisateur connecté
    if user.role == 'admin':
        # Admin peut voir les citoyens et agents de sa région
        utilisateurs = utilisateurs.filter(
            Q(region=user.region) | Q(prefecture__region=user.region),
            role__in=['citoyen', 'agent']
        )
    elif user.role == 'superadmin':
        # Superadmin peut voir tous les utilisateurs sauf autres superadmins
        utilisateurs = utilisateurs.exclude(role='superadmin', id=user.id)
    
    # Filtres supplémentaires
    if role_filter != 'all':
        utilisateurs = utilisateurs.filter(role=role_filter)
    
    if actif_filter != 'all':
        utilisateurs = utilisateurs.filter(actif=actif_filter == 'true')
        
    if region_filter:
        utilisateurs = utilisateurs.filter(region_id=region_filter)
    
    if search:
        utilisateurs = utilisateurs.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(telephone__icontains=search)
        )
    
    # Ajouter les statistiques d'activité pour chaque utilisateur
    utilisateurs = utilisateurs.annotate(
        declarations_count=Count('mes_declarations'),
        reclamations_count=Count('mes_reclamations'),
        nb_declarations_validees=Count('declarations_validees')
    )
    
    # Tri
    ordre = request.GET.get('ordre', '-date_joined')
    utilisateurs = utilisateurs.order_by(ordre)
    
    # Pagination
    paginator = Paginator(utilisateurs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiques détaillées
    base_query = Utilisateur.objects.all()
    if user.role == 'admin':
        base_query = base_query.filter(
            Q(region=user.region) | Q(prefecture__region=user.region)
        )
    
    # Statistiques par rôle avec activité
    today = timezone.now().date()
    this_month = timezone.now().replace(day=1).date()
    
    stats_utilisateurs = {
        # Totaux par rôle
        'citoyens': {
            'total': base_query.filter(role='citoyen').count(),
            'actifs': base_query.filter(
                role='citoyen', 
                actif=True,
                last_login__gte=timezone.now() - timezone.timedelta(days=30)
            ).count(),
            'nouveaux_ce_mois': base_query.filter(
                role='citoyen',
                date_joined__gte=this_month
            ).count(),
            'avec_declarations': base_query.filter(
                role='citoyen'
            ).annotate(nb_decl=Count('mes_declarations')).filter(nb_decl__gt=0).count(),
        },
        'agents': {
            'total': base_query.filter(role='agent').count(),
            'actifs': base_query.filter(
                role='agent',
                actif=True,
                last_login__gte=timezone.now() - timezone.timedelta(days=7)
            ).count(),
            'nouveaux_ce_mois': base_query.filter(
                role='agent',
                date_joined__gte=this_month
            ).count(),
            'declarations_validees_aujourd_hui': Declaration.objects.filter(
                agent_validateur__in=base_query.filter(role='agent'),
                date_publication__date=today
            ).count(),
        },
    }
    
    if user.role == 'superadmin':
        stats_utilisateurs['admins'] = {
            'total': base_query.filter(role='admin').count(),
            'actifs': base_query.filter(
                role='admin',
                actif=True,
                last_login__gte=timezone.now() - timezone.timedelta(days=7)
            ).count(),
        }
    
    # Top utilisateurs actifs
    top_declarants = base_query.filter(role='citoyen').annotate(
        nb_declarations=Count('mes_declarations')
    ).filter(nb_declarations__gt=0).order_by('-nb_declarations')[:5]
    
    top_agents = base_query.filter(role='agent').annotate(
        nb_validations=Count('declarations_validees')
    ).filter(nb_validations__gt=0).order_by('-nb_validations')[:5]
    
    # Régions disponibles pour les filtres
    if user.role == 'superadmin':
        regions = Region.objects.all().order_by('nom')
    else:
        regions = Region.objects.filter(id=user.region_id) if user.region else []
    
    context = {
        'page_obj': page_obj,
        'role_filter': role_filter,
        'search': search,
        'actif_filter': actif_filter,
        'region_filter': region_filter,
        'ordre': ordre,
        'stats_utilisateurs': stats_utilisateurs,
        'top_declarants': top_declarants,
        'top_agents': top_agents,
        'role_choices': Utilisateur.ROLE_CHOICES,
        'regions': regions,
        'can_create_agents': True,
        'can_create_admins': user.role == 'superadmin',
        'is_superadmin': user.role == 'superadmin',
    }
    
    return render(request, 'admin/users.html', context)


@admin_required
def admin_rapports(request):
    """Rapports et analytiques pour les admins"""
    user = request.user
    
    # Période sélectionnée
    periode = request.GET.get('periode', '30')  # 30 jours par défaut
    
    try:
        jours = int(periode)
    except:
        jours = 30
    
    date_debut = timezone.now() - timezone.timedelta(days=jours)
    
    # Filtrer par région de l'admin
    region_filter = Q()
    if user.region:
        region_filter = Q(region=user.region)
    
    # Statistiques de performance
    stats_performance = {
        'temps_moyen_validation': Declaration.objects.filter(
            region_filter,
            statut__in=['valide', 'publie', 'restitue'],
            date_publication__isnull=False
        ).count(),
        
        'temps_moyen_traitement': 2.5,  # Jours simulés
        
        'taux_restitution': Declaration.objects.filter(region_filter).aggregate(
            total=Count('id'),
            restitue=Count('id', filter=Q(statut='restitue'))
        ),
    }
    
    # Évolution quotidienne sur la période
    evolution_quotidienne = Declaration.objects.filter(
        region_filter,
        date_declaration__gte=date_debut
    ).annotate(
        jour=TruncDate('date_declaration')
    ).values('jour').annotate(
        nouvelles=Count('id'),
        validees=Count('id', filter=Q(statut__in=['valide', 'publie', 'restitue']))
    ).order_by('jour')
    
    # Top catégories
    top_categories = Declaration.objects.filter(
        region_filter,
        date_declaration__gte=date_debut
    ).values('categorie__nom').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Agents les plus actifs
    agents_actifs = Utilisateur.objects.filter(
        region=user.region if user.region else None,
        role='agent'
    ).annotate(
        nb_declarations_validees=Count(
            'declarations_validees',
            filter=Q(declarations_validees__date_publication__gte=date_debut)
        ),
        nb_reclamations_traitees=Count(
            'reclamations_traitees',
            filter=Q(reclamations_traitees__date_traitement__gte=date_debut)
        )
    ).order_by('-nb_declarations_validees')[:10]
    
    context = {
        'periode': periode,
        'date_debut': date_debut,
        'stats_performance': stats_performance,
        'evolution_quotidienne': evolution_quotidienne,
        'top_categories': top_categories,
        'agents_actifs': agents_actifs,
        'user_region': user.region,
    }
    
    return render(request, 'admin/rapports.html', context)


# ============ VUES SUPERADMIN ============

@superadmin_required
def superadmin_dashboard(request):
    """Dashboard pour les super administrateurs"""
    
    # Statistiques globales
    stats = {
        'total_users': Utilisateur.objects.count(),
        'total_declarations': Declaration.objects.count(),
        'total_reclamations': Reclamation.objects.count(),
        'total_regions': Region.objects.count(),
        'admins_actifs': Utilisateur.objects.filter(role='admin', actif=True).count(),
        'agents_actifs': Utilisateur.objects.filter(role='agent', actif=True).count(),
        'declarations_en_attente': Declaration.objects.filter(statut='cree').count(),
        'reclamations_en_attente': Reclamation.objects.filter(statut__in=['soumise', 'en_cours']).count(),
    }
    
    # Activité récente
    today = timezone.now().date()
    stats['activite_aujourd_hui'] = {
        'nouvelles_declarations': Declaration.objects.filter(date_declaration__date=today).count(),
        'declarations_validees': Declaration.objects.filter(date_publication__date=today).count(),
        'nouvelles_reclamations': Reclamation.objects.filter(date_reclamation__date=today).count(),
        'nouvelles_inscriptions': Utilisateur.objects.filter(date_joined__date=today).count(),
    }
    
    # Top régions par activité
    top_regions = Region.objects.annotate(
        nb_declarations=Count('declaration'),
        nb_reclamations=Count('declaration__reclamations')
    ).order_by('-nb_declarations')[:10]
    
    # Récente activité système
    recent_actions = ActionLog.objects.select_related('utilisateur').order_by('-date_action')[:20]
    
    # Statistiques par région
    regions_stats = Region.objects.annotate(
        declarations_count=Count('declaration'),
        declarations_publiees=Count('declaration', filter=Q(declaration__statut='publie')),
        objets_restitues=Count('declaration', filter=Q(declaration__statut='restitue')),
        agents_count=Count('utilisateur', filter=Q(utilisateur__role='agent', utilisateur__actif=True))
    ).order_by('-declarations_count')[:10]
    
    context = {
        'stats': stats,
        'top_regions': top_regions,
        'recent_actions': recent_actions,
        'regions_stats': regions_stats,
    }
    
    return render(request, 'superadmin/dashboard.html', context)


@superadmin_required
def superadmin_gestion_admins(request):
    """Gestion des administrateurs"""
    
    # Filtres
    search = request.GET.get('search', '')
    region_filter = request.GET.get('region', '')
    actif_filter = request.GET.get('actif', 'all')
    
    # Query des admins
    admins = Utilisateur.objects.filter(role='admin').select_related('region', 'prefecture')
    
    if search:
        admins = admins.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    
    if region_filter:
        admins = admins.filter(region_id=region_filter)
    
    if actif_filter != 'all':
        admins = admins.filter(actif=actif_filter == 'true')
    
    # Pagination
    paginator = Paginator(admins.order_by('-date_joined'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Régions pour le filtre
    regions = Region.objects.all().order_by('nom')
    
    # Statistiques
    stats = {
        'total_admins': Utilisateur.objects.filter(role='admin').count(),
        'admins_actifs': Utilisateur.objects.filter(role='admin', actif=True).count(),
        'regions_sans_admin': Region.objects.exclude(utilisateur__role='admin').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'region_filter': region_filter,
        'actif_filter': actif_filter,
        'regions': regions,
        'stats': stats,
    }
    
    return render(request, 'superadmin/gestion_admins.html', context)


def superadmin_required_decorator(user):
    return user.is_authenticated and (user.is_superuser or user.role == 'superadmin')


@user_passes_test(superadmin_required_decorator)
def creer_admin(request):
    """Créer un nouvel administrateur"""
    if request.method == 'POST':
        form = AdminForm(request.POST)
        if form.is_valid():
            admin = form.save(commit=False)
            admin.role = 'admin'
            admin.save()
            
            # Log de l'action
            log_action(
                user=request.user,
                action='utilisateur_cree',
                description=f"Administrateur {admin.username} créé par {request.user.username}",
                donnees_supplementaires={
                    'admin_id': admin.id, 
                    'admin_region': admin.region.nom if admin.region else None
                }
            )
            
            messages.success(request, f"Administrateur {admin.username} créé avec succès ✅")
            return redirect('superadmin:dashboard')
    else:
        form = AdminForm()
    
    context = {'form': form}
    return render(request, 'superadmin/creer_admin.html', context)


# ============ NOUVELLES VUES POUR GESTION AVANCÉE ============

@admin_required
def creer_agent(request):
    """Créer un nouvel agent pour la région de l'admin"""
    user = request.user
    
    if request.method == 'POST':
        # Récupération des données du formulaire
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        telephone = request.POST.get('telephone')
        prefecture_id = request.POST.get('prefecture')
        structure_locale_id = request.POST.get('structure_locale')
        
        # Validation de base
        if not all([username, email, password, first_name, last_name]):
            messages.error(request, "Tous les champs obligatoires doivent être renseignés.")
        elif Utilisateur.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur existe déjà.")
        elif Utilisateur.objects.filter(email=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
        else:
            try:
                # Création de l'agent
                agent = Utilisateur.objects.create(
                    username=username,
                    email=email,
                    password=make_password(password),
                    first_name=first_name,
                    last_name=last_name,
                    telephone=telephone,
                    role='agent',
                    region=user.region,  # Même région que l'admin
                    prefecture_id=prefecture_id if prefecture_id else None,
                    actif=True,
                    verifie=True,  # Les agents créés par admin sont automatiquement vérifiés
                    date_verification=timezone.now()
                )
                
                # Assigner une structure locale si spécifiée
                if structure_locale_id:
                    structure = get_object_or_404(StructureLocale, id=structure_locale_id)
                    # Note: Le champ responsable n'existe pas dans le modèle StructureLocale
                
                # Log de l'action
                log_action(
                    user=user,
                    action='utilisateur_cree',
                    description=f"Agent {agent.username} créé par {user.username}",
                    donnees_supplementaires={
                        'agent_id': agent.id,
                        'agent_region': agent.region.nom if agent.region else None,
                        'agent_prefecture': agent.prefecture.nom if agent.prefecture else None
                    }
                )
                
                # Créer une notification pour l'agent
                create_notification(
                    destinataire=agent,
                    type_notification='systeme',
                    titre='Compte agent créé',
                    message=f'Votre compte agent a été créé par {user.get_full_name() or user.username}. Vous pouvez maintenant vous connecter.',
                    lien_action='/agent/login/'
                )
                
                messages.success(request, f"Agent {agent.get_full_name()} créé avec succès ✅")
                return redirect('togo_admin:users')
                
            except Exception as e:
                messages.error(request, f"Erreur lors de la création de l'agent: {str(e)}")
    
    # Préfectures de la région de l'admin
    prefectures = []
    structures_locales = []
    
    if user.region:
        prefectures = Prefecture.objects.filter(region=user.region, actif=True).order_by('nom')
        structures_locales = StructureLocale.objects.filter(
            prefecture__region=user.region,
            actif=True
        ).select_related('prefecture').order_by('nom')
    
    context = {
        'prefectures': prefectures,
        'structures_locales': structures_locales,
        'user_region': user.region,
        'structure_types': StructureLocale.TYPE_CHOICES,
    }
    
    return render(request, 'admin/creer_agent.html', context)


@admin_required
def creer_utilisateur(request):
    """Créer un nouvel utilisateur (citoyen, agent ou admin selon permissions)"""
    user = request.user
    
    if request.method == 'POST':
        # Récupération des données
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        telephone = request.POST.get('telephone')
        role = request.POST.get('role')
        region_id = request.POST.get('region')
        prefecture_id = request.POST.get('prefecture')
        
        # Validation des permissions
        allowed_roles = ['citoyen', 'agent']
        if user.role == 'superadmin':
            allowed_roles.append('admin')
        
        if role not in allowed_roles:
            messages.error(request, "Vous n'avez pas les permissions pour créer ce type d'utilisateur.")
            return redirect('togo_admin:creer_utilisateur')
        
        # Validation de base
        if not all([username, email, password, first_name, last_name, role]):
            messages.error(request, "Tous les champs obligatoires doivent être renseignés.")
        elif Utilisateur.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur existe déjà.")
        elif Utilisateur.objects.filter(email=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
        else:
            try:
                # Déterminer la région selon le rôle de l'admin
                target_region = None
                if user.role == 'admin' and role in ['agent', 'citoyen']:
                    target_region = user.region
                elif user.role == 'superadmin' and region_id:
                    target_region = get_object_or_404(Region, id=region_id)
                
                # Création de l'utilisateur
                new_user = Utilisateur.objects.create(
                    username=username,
                    email=email,
                    password=make_password(password),
                    first_name=first_name,
                    last_name=last_name,
                    telephone=telephone,
                    role=role,
                    region=target_region,
                    prefecture_id=prefecture_id if prefecture_id else None,
                    actif=True,
                    verifie=True if role in ['agent', 'admin'] else False,
                    date_verification=timezone.now() if role in ['agent', 'admin'] else None
                )
                
                # Log de l'action
                log_action(
                    user=user,
                    action='utilisateur_cree',
                    description=f"{role.title()} {new_user.username} créé par {user.username}",
                    donnees_supplementaires={
                        'new_user_id': new_user.id,
                        'new_user_role': role,
                        'new_user_region': target_region.nom if target_region else None
                    }
                )
                
                messages.success(request, f"{role.title()} {new_user.get_full_name()} créé avec succès ✅")
                return redirect('togo_admin:users')
                
            except Exception as e:
                messages.error(request, f"Erreur lors de la création: {str(e)}")
    
    # Données pour le formulaire
    regions = []
    prefectures = []
    
    if user.role == 'superadmin':
        regions = Region.objects.all().order_by('nom')
    if user.region:
        prefectures = Prefecture.objects.filter(region=user.region, actif=True).order_by('nom')
    
    # Rôles autorisés
    role_choices = [
        ('citoyen', 'Citoyen'),
        ('agent', 'Agent de gestion'),
    ]
    if user.role == 'superadmin':
        role_choices.append(('admin', 'Administrateur'))
    
    context = {
        'regions': regions,
        'prefectures': prefectures,
        'role_choices': role_choices,
        'user_region': user.region,
        'is_superadmin': user.role == 'superadmin',
    }
    
    return render(request, 'admin/creer_utilisateur.html', context)


@admin_required
def valider_declaration(request, declaration_id):
    """Valider ou rejeter une déclaration"""
    user = request.user
    declaration = get_object_or_404(Declaration, id=declaration_id)
    
    # Vérifier que l'admin a accès à cette déclaration
    if user.region and declaration.region != user.region:
        messages.error(request, "Vous n'avez pas accès à cette déclaration.")
        return redirect('togo_admin:declarations')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        commentaire_agent = request.POST.get('commentaire_agent', '')
        
        if action == 'valider':
            if declaration.peut_etre_valide():
                declaration.statut = 'valide'
                declaration.agent_validateur = user
                declaration.commentaire_agent = commentaire_agent
                declaration.date_publication = timezone.now()
                declaration.save()
                
                # Log de l'action
                log_action(
                    user=user,
                    action='declaration_validee',
                    declaration=declaration,
                    description=f"Déclaration {declaration.numero_declaration} validée",
                    donnees_supplementaires={'commentaire': commentaire_agent}
                )
                
                # Notification au déclarant
                create_notification(
                    destinataire=declaration.declarant,
                    declaration=declaration,
                    type_notification='declaration_validee',
                    titre='Déclaration validée',
                    message=f'Votre déclaration "{declaration.nom_objet}" a été validée et sera bientôt publiée.',
                    lien_action=f'/declarations/{declaration.uuid}/'
                )
                
                messages.success(request, f"Déclaration {declaration.numero_declaration} validée avec succès ✅")
            else:
                messages.error(request, "Cette déclaration ne peut pas être validée dans son état actuel.")
        
        elif action == 'rejeter':
            if declaration.statut == 'cree':
                declaration.statut = 'rejete'
                declaration.agent_validateur = user
                declaration.commentaire_agent = commentaire_agent
                declaration.save()
                
                # Log de l'action
                log_action(
                    user=user,
                    action='declaration_rejetee',
                    declaration=declaration,
                    description=f"Déclaration {declaration.numero_declaration} rejetée",
                    donnees_supplementaires={'motif': commentaire_agent}
                )
                
                # Notification au déclarant
                create_notification(
                    destinataire=declaration.declarant,
                    declaration=declaration,
                    type_notification='declaration_rejetee',
                    titre='Déclaration rejetée',
                    message=f'Votre déclaration "{declaration.nom_objet}" a été rejetée. Motif: {commentaire_agent}',
                    lien_action=f'/declarations/{declaration.uuid}/'
                )
                
                messages.success(request, f"Déclaration {declaration.numero_declaration} rejetée.")
            else:
                messages.error(request, "Cette déclaration ne peut plus être rejetée.")
        
        elif action == 'publier':
            if declaration.peut_etre_publiee():
                declaration.statut = 'publie'
                declaration.visible_publiquement = True
                if not declaration.date_publication:
                    declaration.date_publication = timezone.now()
                declaration.save()
                
                # Log de l'action
                log_action(
                    user=user,
                    action='declaration_publiee',
                    declaration=declaration,
                    description=f"Déclaration {declaration.numero_declaration} publiée",
                    donnees_supplementaires={'commentaire': commentaire_agent}
                )
                
                # Notification au déclarant
                create_notification(
                    destinataire=declaration.declarant,
                    declaration=declaration,
                    type_notification='declaration_publiee',
                    titre='Déclaration publiée',
                    message=f'Votre déclaration "{declaration.nom_objet}" est maintenant visible publiquement.',
                    lien_action=f'/objets/{declaration.uuid}/'
                )
                
                messages.success(request, f"Déclaration {declaration.numero_declaration} publiée avec succès ✅")
            else:
                messages.error(request, "Cette déclaration ne peut pas être publiée.")
        
        return redirect('togo_admin:declaration_detail', declaration_id=declaration.id)
    
    # Affichage de la déclaration pour validation
    context = {
        'declaration': declaration,
        'peut_valider': declaration.peut_etre_valide(),
        'peut_publier': declaration.peut_etre_publiee(),
        'peut_rejeter': declaration.statut == 'cree',
    }
    
    return render(request, 'admin/valider_declaration.html', context)


@admin_required
def declaration_detail(request, declaration_id):
    """Détail d'une déclaration avec options d'administration"""
    user = request.user
    declaration = get_object_or_404(Declaration, id=declaration_id)
    
    # Vérifier l'accès
    if user.region and declaration.region != user.region:
        messages.error(request, "Vous n'avez pas accès à cette déclaration.")
        return redirect('togo_admin:declarations')
    
    # Réclamations associées
    reclamations = declaration.reclamations.all().select_related('reclamant', 'agent_traitant')
    
    # Historique des actions
    historique = ActionLog.objects.filter(declaration=declaration).select_related('utilisateur').order_by('-date_action')[:20]
    
    # Photos supplémentaires
    photos = declaration.photos_supplementaires.all().order_by('ordre')
    
    # Commentaires
    commentaires = declaration.commentaires_anonymes.filter(est_approuve=True).order_by('-date_creation')[:10]
    
    context = {
        'declaration': declaration,
        'reclamations': reclamations,
        'historique': historique,
        'photos': photos,
        'commentaires': commentaires,
        'peut_modifier': declaration.statut in ['cree', 'en_validation'],
        'peut_valider': declaration.peut_etre_valide(),
        'peut_publier': declaration.peut_etre_publiee(),
        'peut_rejeter': declaration.statut == 'cree',
    }
    
    return render(request, 'admin/declaration_detail.html', context)


@admin_required
def toggle_user_status(request):
    """Activer/désactiver un utilisateur via AJAX"""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        target_user = get_object_or_404(Utilisateur, id=user_id)
        user = request.user
        
        # Vérifier les permissions
        if user.role == 'admin':
            # Admin peut gérer les citoyens et agents de sa région
            if target_user.role not in ['citoyen', 'agent'] or \
               (target_user.region and target_user.region != user.region):
                return JsonResponse({'success': False, 'message': 'Permissions insuffisantes'})
        
        # Basculer le statut
        target_user.actif = not target_user.actif
        target_user.save()
        
        # Log de l'action
        action = 'utilisateur_active' if target_user.actif else 'utilisateur_desactive'
        log_action(
            user=user,
            action='utilisateur_modifie',
            description=f"Utilisateur {target_user.username} {'activé' if target_user.actif else 'désactivé'}",
            donnees_supplementaires={
                'target_user_id': target_user.id,
                'nouveau_statut': target_user.actif
            }
        )
        
        return JsonResponse({
            'success': True,
            'nouvelle_valeur': target_user.actif,
            'message': f"Utilisateur {'activé' if target_user.actif else 'désactivé'} avec succès"
        })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


# ============ GESTION DES UTILISATEURS ÉTENDUE ============

@admin_required
def create_user(request):
    """Créer un nouvel utilisateur standard"""
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            last_name = request.POST.get('nom')
            first_name = request.POST.get('prenom')
            email = request.POST.get('email')
            username = request.POST.get('username')
            telephone = request.POST.get('telephone', '')
            password = request.POST.get('password')
            role = request.POST.get('role')
            prefecture_id = request.POST.get('prefecture')
            region_id = request.POST.get('region')
            is_active = request.POST.get('is_active') == 'on'
            
            # Validation
            if Utilisateur.objects.filter(email=email).exists():
                messages.error(request, 'Un utilisateur avec cet email existe déjà.')
                return render(request, 'admin/create_user.html', get_create_user_context())
                
            if Utilisateur.objects.filter(username=username).exists():
                messages.error(request, 'Ce nom d\'utilisateur est déjà pris.')
                return render(request, 'admin/create_user.html', get_create_user_context())
            
            # Créer l'utilisateur
            user = Utilisateur.objects.create(
                last_name=last_name,
                first_name=first_name,
                email=email,
                username=username,
                telephone=telephone,
                password=make_password(password),
                role=role,
                is_active=is_active,
                prefecture_id=prefecture_id if prefecture_id else None,
                region_id=region_id if region_id else None
            )
            
            # Log de l'action
            log_action(
                user=request.user,
                action='utilisateur_cree',
                description=f'Nouvel utilisateur créé: {user.username} ({user.get_full_name()})',
                donnees_supplementaires={
                    'user_id': user.id,
                    'role': role,
                    'email': email
                }
            )
            
            messages.success(request, f'Utilisateur {user.get_full_name()} créé avec succès.')
            return redirect('togo_admin:users_list')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la création: {str(e)}')
            
    return render(request, 'admin/create_user.html', get_create_user_context())


@admin_required
def create_agent(request):
    """Créer un nouvel agent - TEMPORAIREMENT DÉSACTIVÉ"""
    from django.http import HttpResponseNotFound
    return HttpResponseNotFound("Page de création d'agents temporairement indisponible")


@admin_required
def pending_declarations(request):
    """Gestion des déclarations en attente de validation"""
    user = request.user
    
    # Filtrer par région de l'admin
    region_filter = Q()
    if user.region:
        region_filter = Q(region=user.region)
    
    # Filtres depuis les paramètres GET
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    
    # Requête de base pour les déclarations en attente
    declarations_query = Declaration.objects.filter(
        region_filter & (
            Q(statut='cree') | 
            Q(statut='incomplet') | 
            Q(statut='a_verifier')
        )
    )
    
    # Appliquer les filtres
    if status_filter:
        if status_filter == 'en_attente':
            declarations_query = declarations_query.filter(statut='cree')
        elif status_filter == 'incomplet':
            declarations_query = declarations_query.filter(statut='incomplet')
        elif status_filter == 'a_verifier':
            declarations_query = declarations_query.filter(statut='a_verifier')
    
    if type_filter:
        declarations_query = declarations_query.filter(signalement_type=type_filter)
    
    # Ordonner par date de création (plus récentes en premier)
    declarations = declarations_query.order_by('-date_declaration')
    
    # Pagination
    paginator = Paginator(declarations, 20)
    page_number = request.GET.get('page')
    pending_declarations = paginator.get_page(page_number)
    
    # Statistiques
    today = timezone.now().date()
    stats = {
        'pending_count': declarations_query.filter(statut='cree').count(),
        'incomplete_count': declarations_query.filter(statut='incomplet').count(),
        'today_count': declarations_query.filter(date_declaration__date=today).count(),
        'validated_today': Declaration.objects.filter(
            region_filter & Q(date_publication__date=today)
        ).count(),
    }
    
    context = {
        'pending_declarations': pending_declarations,
        'pending_count': stats['pending_count'],
        'incomplete_count': stats['incomplete_count'],
        'today_count': stats['today_count'],
        'validated_today': stats['validated_today'],
        'current_status_filter': status_filter,
        'current_type_filter': type_filter,
    }
    
    return render(request, 'admin/pending_declarations.html', context)


@admin_required 
def validate_declaration(request, declaration_id):
    """Valider une déclaration"""
    if request.method == 'POST':
        declaration = get_object_or_404(Declaration, id=declaration_id)
        user = request.user
        
        # Vérifier les permissions
        if user.region and declaration.region != user.region:
            return JsonResponse({'success': False, 'message': 'Permissions insuffisantes'})
        
        try:
            # Valider la déclaration
            declaration.statut = 'publie'
            declaration.date_publication = timezone.now()
            declaration.validee_par = user
            declaration.save()
            
            # Log de l'action
            log_action(
                user=user,
                action='declaration_validee',
                description=f'Déclaration #{declaration.id} validée et publiée',
                donnees_supplementaires={
                    'declaration_id': declaration.id,
                    'type': declaration.signalement_type
                }
            )
            
            # Notification au déclarant (si système de notifications activé)
            create_notification(
                utilisateur=declaration.declarant if hasattr(declaration, 'declarant') else None,
                titre='Déclaration validée',
                message=f'Votre déclaration #{declaration.id} a été validée et publiée.',
                type_notification='validation'
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Déclaration validée avec succès'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors de la validation: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


@admin_required
def reject_declaration(request, declaration_id):
    """Rejeter une déclaration"""
    if request.method == 'POST':
        declaration = get_object_or_404(Declaration, id=declaration_id)
        user = request.user
        
        # Vérifier les permissions
        if user.region and declaration.region != user.region:
            return JsonResponse({'success': False, 'message': 'Permissions insuffisantes'})
        
        try:
            # Récupérer la raison du rejet
            data = json.loads(request.body)
            reason = data.get('reason', '')
            
            # Rejeter la déclaration
            declaration.statut = 'rejete'
            declaration.date_rejet = timezone.now()
            declaration.rejetee_par = user
            declaration.raison_rejet = reason
            declaration.save()
            
            # Log de l'action
            log_action(
                user=user,
                action='declaration_rejetee',
                description=f'Déclaration #{declaration.id} rejetée - Raison: {reason}',
                donnees_supplementaires={
                    'declaration_id': declaration.id,
                    'reason': reason
                }
            )
            
            # Notification au déclarant
            create_notification(
                utilisateur=declaration.declarant if hasattr(declaration, 'declarant') else None,
                titre='Déclaration rejetée',
                message=f'Votre déclaration #{declaration.id} a été rejetée. {reason}',
                type_notification='rejet'
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Déclaration rejetée'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors du rejet: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


@admin_required
def edit_declaration(request, declaration_id):
    """Modifier une déclaration pour compléter les informations manquantes"""
    declaration = get_object_or_404(Declaration, id=declaration_id)
    user = request.user
    
    # Vérifier les permissions
    if user.region and declaration.region != user.region:
        messages.error(request, 'Permissions insuffisantes')
        return redirect('togo_admin:pending_declarations')
    
    if request.method == 'POST':
        try:
            # Mettre à jour les champs modifiables
            declaration.description = request.POST.get('description', declaration.description)
            declaration.lieu_incident = request.POST.get('lieu_incident', declaration.lieu_incident)
            
            # Gérer la photo si uploadée
            if 'photo' in request.FILES:
                declaration.photo = request.FILES['photo']
            
            # Marquer comme complète si tous les champs requis sont remplis
            if declaration.description and declaration.lieu_incident:
                declaration.statut = 'cree'  # Prête pour validation
            
            declaration.save()
            
            # Log de l'action
            log_action(
                user=user,
                action='declaration_modifiee',
                description=f'Déclaration #{declaration.id} modifiée par admin',
                donnees_supplementaires={'declaration_id': declaration.id}
            )
            
            messages.success(request, 'Déclaration mise à jour avec succès.')
            return redirect('togo_admin:pending_declarations')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la modification: {str(e)}')
    
    context = {
        'declaration': declaration,
        'categories': CategorieObjet.objects.all()
    }
    
    return render(request, 'admin/edit_declaration.html', context)


# ============ FONCTIONS UTILITAIRES ============

def get_create_user_context():
    """Contexte pour la création d'utilisateurs"""
    return {
        'prefectures': Prefecture.objects.all().order_by('nom'),
        'regions': Region.objects.all().order_by('nom')
    }


def get_create_agent_context():
    """Contexte pour la création d'agents"""
    return {
        'prefectures': Prefecture.objects.all().order_by('nom')
    }


@admin_required
def edit_user(request, user_id):
    """Modifier un utilisateur existant"""
    target_user = get_object_or_404(Utilisateur, id=user_id)
    
    if request.method == 'POST':
        try:
            # Mettre à jour les informations de base
            target_user.last_name = request.POST.get('nom', target_user.last_name)
            target_user.first_name = request.POST.get('prenom', target_user.first_name)
            target_user.email = request.POST.get('email', target_user.email)
            target_user.telephone = request.POST.get('telephone', target_user.telephone)
            
            # Mettre à jour le mot de passe si fourni
            new_password = request.POST.get('password', '')
            if new_password:
                target_user.password = make_password(new_password)
            
            # Mettre à jour le statut si autorisé
            target_user.is_active = request.POST.get('is_active') == 'on'
            
            target_user.save()
            
            messages.success(request, f'Utilisateur {target_user.get_full_name()} mis à jour.')
            return redirect('togo_admin:users_list')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la modification: {str(e)}')
    
    context = {
        'user_to_edit': target_user,
        'prefectures': Prefecture.objects.all().order_by('nom'),
        'regions': Region.objects.all().order_by('nom')
    }
    
    return render(request, 'admin/edit_user.html', context)


@admin_required
def delete_user(request, user_id):
    """Supprimer un utilisateur (désactivation plutôt que suppression)"""
    target_user = get_object_or_404(Utilisateur, id=user_id)
    
    if request.method == 'POST':
        try:
            # Désactiver plutôt que supprimer pour garder l'historique
            target_user.is_active = False
            target_user.save()
            
            # Log de l'action
            log_action(
                user=request.user,
                action='utilisateur_supprime',
                description=f'Utilisateur {target_user.username} désactivé',
                donnees_supplementaires={'target_user_id': target_user.id}
            )
            
            messages.success(request, f'Utilisateur {target_user.get_full_name()} désactivé.')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la suppression: {str(e)}')
    
    return redirect('togo_admin:users_list')


@admin_required
def edit_agent(request, agent_id):
    """Modifier un agent - TEMPORAIREMENT DÉSACTIVÉ"""
    from django.http import HttpResponseNotFound
    return HttpResponseNotFound("Page d'édition d'agents temporairement indisponible")


@admin_required  
def delete_agent(request, agent_id):
    """Désactiver un agent - TEMPORAIREMENT DÉSACTIVÉ"""
    from django.http import HttpResponseNotFound
    return HttpResponseNotFound("Page de suppression d'agents temporairement indisponible")