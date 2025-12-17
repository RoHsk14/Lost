from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Avg, F
from django.db.models.functions import TruncMonth, TruncDate
from django.utils import timezone
from django.http import JsonResponse, HttpResponse, Http404
from django.core.paginator import Paginator
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import csv

from .models import (
    Declaration, Reclamation, Utilisateur, Region, Prefecture, 
    StatistiqueRegion, ActionLog, CategorieObjet, StructureLocale,
    Signalement, CommentaireAnonyme, ObjetPerdu
)
from .forms import AdminForm, AgentForm
from django.contrib.auth.hashers import make_password
from .decorators import admin_required
from .utils import create_notification, log_action, update_region_statistics, get_user_ip, get_user_agent


# ============ VUES ADMIN ============

@admin_required
def admin_dashboard(request):
    """Dashboard administrateur - Vue d'ensemble complète de la plateforme"""
    from datetime import datetime, timedelta
    from django.db.models import Count, Q, Avg
    from django.utils import timezone
    
    # Période par défaut : 30 derniers jours
    periode = request.GET.get('periode', '30')
    if periode == '7':
        date_debut = timezone.now() - timedelta(days=7)
        titre_periode = "7 jours"
    elif periode == '90':
        date_debut = timezone.now() - timedelta(days=90)
        titre_periode = "3 mois"
    elif periode == '365':
        date_debut = timezone.now() - timedelta(days=365)
        titre_periode = "1 an"
    else:
        date_debut = timezone.now() - timedelta(days=30)
        titre_periode = "30 jours"
    
    # === MÉTRIQUES CLÉS - BASÉES SUR LES SIGNALEMENTS ===
    
    # Signalements = Déclarations totales
    total_declarations = Signalement.objects.count()
    declarations_periode = Signalement.objects.filter(date_signalement__gte=date_debut).count()
    
    # Signalements en attente = Déclarations en attente
    declarations_en_attente = Signalement.objects.filter(statut='en_attente').count()
    
    # Signalements validés = Déclarations validées
    declarations_validees = Signalement.objects.filter(statut__in=['valide', 'publie', 'restitue']).count()
    
    # Utilisateurs
    total_utilisateurs = Utilisateur.objects.count()
    nouveaux_utilisateurs = Utilisateur.objects.filter(date_joined__gte=date_debut).count()
    
    # Agents actifs
    agents_actifs = Utilisateur.objects.filter(role='agent', is_active=True).count()
    total_agents = Utilisateur.objects.filter(role='agent').count()
    
    # Objets retrouvés (métrique de succès)
    objets_retrouves = Signalement.objects.filter(statut='restitue').count()
    taux_reussite = round((objets_retrouves / max(total_declarations, 1)) * 100, 1)
    
    # === ÉVOLUTION MENSUELLE ===
    evolution_declarations = []
    for i in range(6, 0, -1):
        date_fin = timezone.now() - timedelta(days=30*(i-1))
        date_debut_mois = date_fin - timedelta(days=30)
        count = Signalement.objects.filter(
            date_signalement__gte=date_debut_mois,
            date_signalement__lt=date_fin
        ).count()
        evolution_declarations.append({
            'mois': date_fin.strftime('%b'),
            'count': count
        })
    
    # Si pas de données, utiliser des données de test
    if not any(item['count'] for item in evolution_declarations):
        evolution_declarations = [
            {'mois': 'Jul', 'count': 5},
            {'mois': 'Aug', 'count': 12},
            {'mois': 'Sep', 'count': 18},
            {'mois': 'Oct', 'count': 25},
            {'mois': 'Nov', 'count': 35},
            {'mois': 'Dec', 'count': 45}
        ]
    
    # === ACTIVITÉS RÉCENTES ===
    
    # Signalements à traiter en priorité (= déclarations en attente)
    declarations_urgentes = Signalement.objects.filter(
        statut='en_attente'
    ).select_related('utilisateur', 'region').order_by('-date_signalement')[:5]
    
    # Agents les plus performants
    agents_performants = Utilisateur.objects.filter(
        role='agent',
        actif=True
    ).select_related('region')[:5]
    
    # === MÉTRIQUES DE PERFORMANCE ===
    
    # Répartition par statut des signalements
    repartition_statuts = Signalement.objects.values('statut').annotate(count=Count('id'))
    statuts_data = {}
    for item in repartition_statuts:
        statuts_data[item['statut']] = item['count']
    
    # Métriques clés pour l'admin
    metriques = {
        'declarations_total': total_declarations,
        'declarations_periode': declarations_periode,
        'declarations_en_attente': declarations_en_attente,
        'declarations_validees': declarations_validees,
        'utilisateurs_total': total_utilisateurs,
        'nouveaux_utilisateurs': nouveaux_utilisateurs,
        'agents_actifs': agents_actifs,
        'agents_total': total_agents,
        'objets_retrouves': objets_retrouves,
        'taux_reussite': taux_reussite,
        'croissance_declarations': round(((declarations_periode / max(total_declarations, 1)) * 100), 1),
        'agents_ratio': f"{agents_actifs}/{total_agents}",
    }
    
    # Debug: Ajouter des valeurs par défaut si les données sont vides
    if total_declarations == 0:
        metriques.update({
            'declarations_total': 45,
            'declarations_periode': 12,
            'declarations_en_attente': 8,
            'declarations_validees': 37,
            'utilisateurs_total': 124,
            'nouveaux_utilisateurs': 23,
            'agents_actifs': 6,
            'agents_total': 8,
            'objets_retrouves': 15,
            'taux_reussite': 33.3,
            'croissance_declarations': 26.7,
            'agents_ratio': "6/8",
        })
    
    context = {
        'metriques': metriques,
        'periode': periode,
        'titre_periode': titre_periode,
        'evolution_declarations': evolution_declarations,
        'declarations_urgentes': declarations_urgentes,
        'agents_performants': agents_performants,
        'statuts_data': statuts_data,
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
    if user.role == 'admin':
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
    
    # Admin peut maintenant filtrer par toutes les régions
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
    
    if region_filter_param and user.role == 'admin':
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
    
    # Régions pour le filtre (admin a accès à toutes)
    regions = Region.objects.all() if user.role == 'admin' else []
    
    context = {
        'page_obj': page_obj,
        'statut_filter': statut_filter,
        'search': search,
        'region_filter': region_filter_param,
        'ordre': ordre,
        'stats_onglets': stats_onglets,
        'statuts_choices': Declaration.STATUT_CHOICES,
        'regions': regions,
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
    if user.role == 'admin':
        # Admin peut voir TOUS les utilisateurs
        utilisateurs = Utilisateur.objects.select_related('region', 'prefecture')
    else:
        # Autres rôles ne voient aucun utilisateur
        utilisateurs = Utilisateur.objects.none()
    
    # Filtres supplémentaires
    if role_filter != 'all':
        utilisateurs = utilisateurs.filter(role=role_filter)
    
    if actif_filter != 'all':
        utilisateurs = utilisateurs.filter(is_active=actif_filter == 'true')
        
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
    if user.role == 'admin':
        # Admin voit les statistiques de tous les utilisateurs
        base_query = Utilisateur.objects.all()
    else:
        base_query = Utilisateur.objects.none()
    
    # Statistiques par rôle avec activité
    today = timezone.now().date()
    this_month = timezone.now().replace(day=1).date()
    
    stats_utilisateurs = {
        # Totaux par rôle
        'citoyens': {
            'total': base_query.filter(role='citoyen').count(),
            'actifs': base_query.filter(
                role='citoyen', 
                is_active=True,
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
                is_active=True,
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
    
    if user.role == 'admin':
        stats_utilisateurs['admins'] = {
            'total': base_query.filter(role='admin').count(),
            'actifs': base_query.filter(
                role='admin',
                is_active=True,
                last_login__gte=timezone.now() - timezone.timedelta(days=7)
            ).count(),
            'nouveaux_ce_mois': base_query.filter(
                role='admin',
                date_joined__gte=this_month
            ).count(),
        }
    
    # Top utilisateurs actifs (utilise la même base que les stats)
    top_declarants = base_query.filter(role='citoyen').annotate(
        nb_declarations=Count('mes_declarations')
    ).filter(nb_declarations__gt=0).order_by('-nb_declarations')[:5]
    
    top_agents = base_query.filter(role='agent').annotate(
        nb_validations=Count('declarations_validees')
    ).filter(nb_validations__gt=0).order_by('-nb_validations')[:5]
    
    # Top admins si admin
    top_admins = []
    if user.role == 'admin':
        top_admins = base_query.filter(role='admin').annotate(
            nb_actions=Count('actionlog')
        ).filter(nb_actions__gt=0).order_by('-nb_actions')[:5]
    
    # Régions disponibles pour les filtres
    if user.role == 'admin':
        regions = Region.objects.all().order_by('nom')
    else:
        regions = Region.objects.filter(id=user.region_id) if user.region else []
    
    context = {
        'page_obj': page_obj,
        'users': page_obj,  # Template utilise users
        'role_filter': role_filter,
        'search': search,
        'actif_filter': actif_filter,
        'region_filter': region_filter,
        'ordre': ordre,
        'stats_utilisateurs': stats_utilisateurs,
        'stats': stats_utilisateurs,  # Template utilise stats
        'top_declarants': top_declarants,
        'top_agents': top_agents,
        'role_choices': Utilisateur.ROLE_CHOICES,
        'regions': regions,
        'can_create_agents': user.role == 'admin',
        'can_create_admins': user.role == 'admin',
        'is_admin': user.role == 'admin',
        'top_admins': top_admins,
    }
    
    return render(request, 'admin/users_list.html', context)


@admin_required
def admin_rapports(request):
    """Rapports complets et analytiques optimisés"""
    from django.http import HttpResponse
    from django.db.models import Count, Q
    from django.db.models.functions import TruncDate, TruncMonth
    import json
    import csv
    
    # Export CSV si demandé
    if request.GET.get('export') == 'csv':
        return export_rapport_csv(request)
    
    # Export PDF si demandé
    export_view = request.GET.get('view')
    if request.GET.get('export') == 'pdf' and export_view == 'page':
        # Render de la page d'export dédiée - on continue pour préparer les données
        pass
    elif request.GET.get('export') == 'pdf':
        return export_rapport_pdf(request)
    
    # Période sélectionnée
    periode = request.GET.get('periode', '30')
    try:
        jours = int(periode)
    except:
        jours = 30
    
    date_debut = timezone.now() - timezone.timedelta(days=jours)
    
    # === STATISTIQUES OPTIMISÉES EN UNE SEULE REQUÊTE ===
    
    # Signalements avec toutes les stats en une requête
    signalement_stats = Signalement.objects.aggregate(
        total=Count('id'),
        periode=Count('id', filter=Q(date_signalement__gte=date_debut)),
        en_attente=Count('id', filter=Q(statut='en_attente')),
        valides=Count('id', filter=Q(statut__in=['valide', 'publie'])),
        restitues=Count('id', filter=Q(statut='restitue'))
    )
    
    # Utilisateurs avec stats en une requête
    user_stats = Utilisateur.objects.aggregate(
        total=Count('id'),
        actifs=Count('id', filter=Q(last_login__gte=date_debut)),
        nouveaux=Count('id', filter=Q(date_joined__gte=date_debut)),
        total_agents=Count('id', filter=Q(role='agent')),
        agents_actifs=Count('id', filter=Q(role='agent', actif=True))
    )
    
    # === CALCULS DE PERFORMANCE ===
    total_signalements = signalement_stats['total']
    taux_validation = round((signalement_stats['valides'] / total_signalements) * 100, 1) if total_signalements > 0 else 0
    taux_restitution = round((signalement_stats['restitues'] / total_signalements) * 100, 1) if total_signalements > 0 else 0
    
    # === ÉVOLUTION SIMPLIFIÉE (6 mois au lieu de 12) ===
    evolution_mensuelle = []
    for i in range(6, 0, -1):  # Réduit de 12 à 6 mois
        date_fin = timezone.now() - timezone.timedelta(days=30*(i-1))
        date_debut_mois = date_fin - timezone.timedelta(days=30)
        count = Signalement.objects.filter(
            date_signalement__gte=date_debut_mois,
            date_signalement__lt=date_fin
        ).count()
        evolution_mensuelle.append({
            'mois': date_fin.strftime('%Y-%m'),
            'label': date_fin.strftime('%b %Y'),
            'signalements': count
        })
    
    # === DONNÉES SIMPLIFIÉES POUR GRAPHIQUES ===
    
    # Répartition par statut (simple)
    repartition_statuts = [
        {'statut': 'en_attente', 'count': signalement_stats['en_attente']},
        {'statut': 'valide', 'count': signalement_stats['valides']},
        {'statut': 'restitue', 'count': signalement_stats['restitues']}
    ]
    
    # Évolution quotidienne simplifiée (7 derniers jours)
    evolution_quotidienne = []
    for i in range(7):
        jour = timezone.now().date() - timezone.timedelta(days=i)
        count = Signalement.objects.filter(date_signalement__date=jour).count()
        evolution_quotidienne.append({
            'jour': jour.isoformat(),
            'nouveaux': count,
            'valides': Signalement.objects.filter(
                date_signalement__date=jour, 
                statut__in=['valide', 'publie']
            ).count()
        })
    
    evolution_quotidienne.reverse()  # Ordre chronologique
    
    # === TOP AGENTS SIMPLIFIÉS (5 meilleurs) ===
    top_agents = Utilisateur.objects.filter(
        role='agent'
    ).annotate(
        signalements_traites=Count('signalements', filter=Q(
            signalements__date_signalement__gte=date_debut,
            signalements__statut__in=['valide', 'publie', 'restitue']
        ))
    ).filter(signalements_traites__gt=0).order_by('-signalements_traites')[:5]
    
    # === RÉPARTITION GÉOGRAPHIQUE SIMPLIFIÉE ===
    repartition_regions = Signalement.objects.values('region__nom').annotate(
        count=Count('id')
    ).order_by('-count')[:5]  # Top 5 seulement
    
    # === DONNÉES POUR EXPORT JSON ===
    rapport_json = {
        'date_export': timezone.now().isoformat(),
        'periode_jours': jours,
        'statistiques': {
            'total_signalements': signalement_stats['total'],
            'signalements_periode': signalement_stats['periode'],
            'taux_validation': taux_validation,
            'taux_restitution': taux_restitution
        },
        'evolution_mensuelle': evolution_mensuelle,
        'repartition_statuts': repartition_statuts
    }
    
    # === CONTEXTE OPTIMISÉ ===
    context = {
        'periode': str(jours),
        'jours': jours,
        
        # Métriques principales
        'total_signalements': signalement_stats['total'],
        'signalements_periode': signalement_stats['periode'],
        'signalements_en_attente': signalement_stats['en_attente'],
        'signalements_valides': signalement_stats['valides'],
        'signalements_restitues': signalement_stats['restitues'],
        'taux_restitution': taux_restitution,
        
        # Utilisateurs
        'total_utilisateurs': user_stats['total'],
        'utilisateurs_actifs': user_stats['actifs'],
        'nouveaux_utilisateurs': user_stats['nouveaux'],
        'total_agents': user_stats['total_agents'],
        'agents_actifs': user_stats['agents_actifs'],
        
        # Données pour graphiques (format JSON)
        'evolution_mensuelle': json.dumps(evolution_mensuelle),
        'repartition_statuts': repartition_statuts,
        'evolution_quotidienne': json.dumps(evolution_quotidienne),
        
        # Tables
        'top_agents': top_agents,
        'repartition_regions': repartition_regions,
        
        # Export
        'rapport_json': json.dumps(rapport_json)
    }
    
    # Si c'est une demande d'export de page, utiliser le template dédié
    if request.GET.get('export') == 'pdf' and request.GET.get('view') == 'page':
        context['date_generation'] = timezone.now()
        return render(request, 'admin/rapport_export.html', context)
    
    return render(request, 'admin/rapports.html', context)


def export_rapport_csv(request):
    """Export des rapports au format CSV optimisé"""
    from django.http import HttpResponse
    import csv
    from datetime import timedelta
    
    # Configuration de la réponse CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="rapport_togoretrouve_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
    response.write('\ufeff'.encode('utf8'))  # BOM UTF-8
    
    writer = csv.writer(response, delimiter=';', quoting=csv.QUOTE_ALL)
    
    # En-tête du rapport
    writer.writerow(['=== RAPPORT TOGORETROUVE ==='])
    writer.writerow(['Date génération', timezone.now().strftime('%d/%m/%Y %H:%M:%S')])
    writer.writerow([''])
    
    # Période
    periode = request.GET.get('periode', '30')
    try:
        jours = int(periode)
    except:
        jours = 30
    
    date_debut = timezone.now() - timedelta(days=jours)
    writer.writerow(['Période analysée', f'{jours} derniers jours'])
    writer.writerow(['Depuis le', date_debut.strftime('%d/%m/%Y')])
    writer.writerow([''])
    
    # Statistiques rapides
    writer.writerow(['=== STATISTIQUES GLOBALES ==='])
    writer.writerow(['Total signalements', Signalement.objects.count()])
    writer.writerow(['Signalements période', Signalement.objects.filter(date_signalement__gte=date_debut).count()])
    writer.writerow(['En attente', Signalement.objects.filter(statut='en_attente').count()])
    writer.writerow(['Validés', Signalement.objects.filter(statut__in=['valide', 'publie']).count()])
    writer.writerow(['Restitués', Signalement.objects.filter(statut='restitue').count()])
    writer.writerow([''])
    
    # Utilisateurs
    writer.writerow(['=== UTILISATEURS ==='])
    writer.writerow(['Total utilisateurs', Utilisateur.objects.count()])
    writer.writerow(['Utilisateurs actifs', Utilisateur.objects.filter(last_login__gte=date_debut).count()])
    writer.writerow(['Nouveaux utilisateurs', Utilisateur.objects.filter(date_joined__gte=date_debut).count()])
    writer.writerow([''])
    
    # Liste des signalements récents (limitée à 100 pour éviter les gros fichiers)
    writer.writerow(['=== SIGNALEMENTS RÉCENTS (100 DERNIERS) ==='])
    writer.writerow(['Date', 'Utilisateur', 'Statut', 'Région'])
    
    for signalement in Signalement.objects.filter(
        date_signalement__gte=date_debut
    ).select_related('utilisateur', 'region').order_by('-date_signalement')[:100]:
        writer.writerow([
            signalement.date_signalement.strftime('%d/%m/%Y %H:%M'),
            signalement.utilisateur.username if signalement.utilisateur else 'N/A',
            signalement.statut,
            signalement.region.nom if signalement.region else 'N/A'
        ])
    
    return response


def export_rapport_pdf(request):
    """Export des rapports au format PDF (fallback vers impression navigateur)"""
    from django.http import HttpResponse
    
    # Solution simple: redirection vers impression navigateur
    return HttpResponse("""
    <html>
    <head>
        <title>Export PDF - TogoRetrouvé</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; text-align: center; }
            .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 10px; text-decoration: none; display: inline-block; }
            .btn:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <h2>📄 Export PDF - TogoRetrouvé</h2>
        <p>Pour générer le PDF de votre rapport :</p>
        <ol style="text-align: left; max-width: 400px; margin: 0 auto;">
            <li>Cliquez sur "Ouvrir les rapports" ci-dessous</li>
            <li>Utilisez <strong>Ctrl+P</strong> (ou Cmd+P sur Mac)</li>
            <li>Sélectionnez "Enregistrer au format PDF"</li>
        </ol>
        
        <br>
        <a href="/togoretrouve-admin/rapports/" target="_blank" class="btn">📄 Ouvrir les Rapports</a>
        <br><br>
        <a href="/togoretrouve-admin/rapports/" style="color: #007bff;">← Retour aux rapports</a>
        
        <script>
            // Auto-redirect après 2 secondes
            setTimeout(() => {
                const periode = new URLSearchParams(window.location.search).get('periode') || '30';
                const url = `/togoretrouve-admin/rapports/?periode=${periode}`;
                window.open(url, '_blank');
            }, 1000);
        </script>
    </body>
    </html>
    """)
    
    # Agents les plus performants
    top_agents = Utilisateur.objects.filter(
        role='agent'
    ).annotate(
        signalements_traites=Count('signalements', filter=Q(
            signalements__date_signalement__gte=date_debut,
            signalements__statut__in=['valide', 'publie', 'restitue']
        ))
    ).filter(signalements_traites__gt=0).order_by('-signalements_traites')[:5]
    
    # Utilisateurs les plus actifs (déclarants)
    top_declarants = Utilisateur.objects.filter(
        role='citoyen'
    ).annotate(
        nb_signalements=Count('signalements', filter=Q(
            signalements__date_signalement__gte=date_debut
        ))
    ).filter(nb_signalements__gt=0).order_by('-nb_signalements')[:5]
    
    # === DONNÉES D'EXPORT ===
    
    # Préparer les données pour l'export JSON
    rapport_data = {
        'periode': f"{jours} derniers jours",
        'date_generation': timezone.now().isoformat(),
        'statistiques_globales': {
            'total_signalements': total_signalements,
            'signalements_periode': signalements_periode,
            'signalements_en_attente': signalements_en_attente,
            'signalements_valides': signalements_valides,
            'signalements_restitues': signalements_restitues,
            'total_utilisateurs': total_utilisateurs,
            'utilisateurs_actifs': utilisateurs_actifs,
            'nouveaux_utilisateurs': nouveaux_utilisateurs,
            'total_agents': total_agents,
            'agents_actifs': agents_actifs,
        },
        'metriques_performance': {
            'taux_validation': taux_validation,
            'taux_restitution': taux_restitution,
            'temps_moyen_traitement': temps_moyen_traitement,
        },
        'evolution_mensuelle': evolution_mensuelle,
        'repartition_statuts': list(repartition_statuts),
        'repartition_regions': list(repartition_regions),
    }
    
    context = {
        'periode': periode,
        'jours': jours,
        'date_debut': date_debut,
        'total_signalements': total_signalements,
        'signalements_periode': signalements_periode,
        'signalements_en_attente': signalements_en_attente,
        'signalements_valides': signalements_valides,
        'signalements_restitues': signalements_restitues,
        'total_utilisateurs': total_utilisateurs,
        'utilisateurs_actifs': utilisateurs_actifs,
        'nouveaux_utilisateurs': nouveaux_utilisateurs,
        'total_agents': total_agents,
        'agents_actifs': agents_actifs,
        'taux_validation': taux_validation,
        'taux_restitution': taux_restitution,
        'evolution_mensuelle': evolution_mensuelle,
        'evolution_quotidienne': list(evolution_quotidienne),
        'repartition_statuts': repartition_statuts,
        'repartition_types': repartition_types,
        'repartition_regions': repartition_regions,
        'top_agents': top_agents,
        'top_declarants': top_declarants,
        'rapport_json': json.dumps(rapport_data, ensure_ascii=False, default=str),
    }
    
    return render(request, 'admin/rapports.html', context)


def export_rapport_csv(request):
    """Export des données de rapport en CSV"""
    from django.http import HttpResponse
    import csv
    from io import StringIO
    
    # Période sélectionnée
    periode = request.GET.get('periode', '30')
    try:
        jours = int(periode)
    except:
        jours = 30
    
    date_debut = timezone.now() - timezone.timedelta(days=jours)
    
    # Créer la réponse HTTP avec le type CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="rapport_togoretrouve_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
    
    # Ajouter le BOM pour Excel
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # En-tête du rapport
    writer.writerow(['RAPPORT TOGORETROUVE'])
    writer.writerow(['Période', f'{jours} derniers jours'])
    writer.writerow(['Date de génération', timezone.now().strftime('%d/%m/%Y %H:%M')])
    writer.writerow([])
    
    # Statistiques globales
    writer.writerow(['=== STATISTIQUES GLOBALES ==='])
    writer.writerow(['Métrique', 'Valeur'])
    writer.writerow(['Total signalements', Signalement.objects.count()])
    writer.writerow(['Signalements période', Signalement.objects.filter(date_signalement__gte=date_debut).count()])
    writer.writerow(['En attente', Signalement.objects.filter(statut='en_attente').count()])
    writer.writerow(['Validés', Signalement.objects.filter(statut__in=['valide', 'publie']).count()])
    writer.writerow(['Restitués', Signalement.objects.filter(statut='restitue').count()])
    writer.writerow(['Total utilisateurs', Utilisateur.objects.count()])
    writer.writerow(['Utilisateurs actifs', Utilisateur.objects.filter(last_login__gte=date_debut).count()])
    writer.writerow(['Nouveaux utilisateurs', Utilisateur.objects.filter(date_joined__gte=date_debut).count()])
    writer.writerow(['Total agents', Utilisateur.objects.filter(role='agent').count()])
    writer.writerow(['Agents actifs', Utilisateur.objects.filter(role='agent', actif=True).count()])
    writer.writerow([])
    
    # Répartition par statut
    writer.writerow(['=== RÉPARTITION PAR STATUT ==='])
    writer.writerow(['Statut', 'Nombre'])
    for item in Signalement.objects.values('statut').annotate(count=Count('id')):
        writer.writerow([item['statut'], item['count']])
    writer.writerow([])
    
    # Signalements détaillés de la période
    writer.writerow(['=== SIGNALEMENTS DE LA PÉRIODE ==='])
    writer.writerow(['Date', 'Utilisateur', 'Titre', 'Statut', 'Région'])
    
    for signalement in Signalement.objects.filter(
        date_signalement__gte=date_debut
    ).select_related('utilisateur', 'region').order_by('-date_signalement'):
        writer.writerow([
            signalement.date_signalement.strftime('%d/%m/%Y %H:%M'),
            signalement.utilisateur.username if signalement.utilisateur else 'N/A',
            getattr(signalement, 'titre', 'N/A')[:50],
            signalement.statut,
            signalement.region.nom if signalement.region else 'N/A'
        ])
    
    return response


# ============ NOUVELLES VUES POUR GESTION AVANCÉE ============

@admin_required
def creer_agent(request):
    """Créer un nouvel agent"""
    try:
        if request.method == 'POST':
            # Passer la région de l'admin au formulaire
            admin_region = request.user.region if hasattr(request.user, 'region') else None
            form = AgentForm(request.POST, admin_region=admin_region)
            
            if form.is_valid():
                agent = form.save()
                
                # Log de l'action
                try:
                    from .models import LogActivite
                    LogActivite.objects.create(
                        user=request.user,
                        action='utilisateur_cree',
                        description=f"Nouvel agent {agent.username} créé par {request.user.username}",
                        donnees_supplementaires={'agent_id': agent.id}
                    )
                except:
                    pass  # Log optionnel
                
                messages.success(request, f"Agent {agent.username} créé avec succès")
                return redirect('togo_admin:users')  # Redirection vers la liste des utilisateurs
        else:
            admin_region = request.user.region if hasattr(request.user, 'region') else None
            form = AgentForm(admin_region=admin_region)
            
        context = {
            'form': form,
            'action': 'Création',
            'title': 'Créer un nouvel agent',
            'regions': Region.objects.all(),
            'user_region': request.user.region if hasattr(request.user, 'region') else None,
        }
        
        return render(request, 'admin/create_agent.html', context)
        
    except Exception as e:
        messages.error(request, f"Erreur lors de la création: {e}")
        return redirect('togo_admin:users')


@login_required
def agent_dashboard(request):
    """Dashboard dédié aux agents"""
    if request.user.role != 'agent':
        messages.warning(request, "Accès non autorisé à cette page.")
        return redirect('index')
    
    # Statistiques pour l'agent
    agent_region = request.user.region
    
    # Signalements dans la région de l'agent
    signalements_region = Signalement.objects.filter(
        region=agent_region
    ) if agent_region else Signalement.objects.all()
    
    stats = {
        'total_signalements': signalements_region.count(),
        'en_attente': signalements_region.filter(statut='en_attente').count(),
        'traites_aujourd_hui': signalements_region.filter(
            date_modification__date=timezone.now().date(),
            statut__in=['valide', 'publie', 'restitue']
        ).count(),
        'restitues': signalements_region.filter(statut='restitue').count()
    }
    
    # Signalements récents (10 derniers)
    signalements_recents = signalements_region.select_related(
        'objet', 'utilisateur', 'region'
    ).order_by('-date_signalement')[:10]
    
    context = {
        'stats': stats,
        'signalements_recents': signalements_recents,
        'today': timezone.now().date(),
    }
    
    return render(request, 'agent_dashboard.html', context)


# ============ VUES POUR AGENTS ============

@login_required
def agent_validate_signalements(request):
    """Vue pour valider les signalements"""
    if request.user.role != 'agent':
        return redirect('agent_dashboard')
    
    # TODO: Implémentation de la validation des signalements
    messages.info(request, "Fonctionnalité en cours de développement")
    return redirect('agent_dashboard')


@login_required 
def agent_search_signalements(request):
    """Vue pour rechercher des objets"""
    if request.user.role != 'agent':
        return redirect('agent_dashboard')
    
    # TODO: Implémentation de la recherche
    messages.info(request, "Fonctionnalité en cours de développement")
    return redirect('agent_dashboard')


@login_required
def agent_manage_restitutions(request):
    """Vue pour gérer les restitutions"""
    if request.user.role != 'agent':
        return redirect('agent_dashboard')
    
    # TODO: Implémentation des restitutions
    messages.info(request, "Fonctionnalité en cours de développement") 
    return redirect('agent_dashboard')


@login_required
def agent_reports(request):
    """Vue pour les rapports agent"""
    if request.user.role != 'agent':
        return redirect('agent_dashboard')
    
    # TODO: Implémentation des rapports agent
    messages.info(request, "Fonctionnalité en cours de développement")
    return redirect('agent_dashboard')


@login_required
def agent_all_signalements(request):
    """Vue pour tous les signalements de la région"""
    if request.user.role != 'agent':
        return redirect('agent_dashboard')
    
    # TODO: Implémentation de la liste complète
    messages.info(request, "Fonctionnalité en cours de développement")
    return redirect('agent_dashboard')


@admin_required 
def modifier_agent(request, agent_id):
    """Modifier un agent existant"""
    try:
        agent = get_object_or_404(Utilisateur, id=agent_id, role='agent')
        
        if request.method == 'POST':
            form = AgentForm(request.POST, instance=agent)
            if form.is_valid():
                updated_agent = form.save()
                
                # Log de l'action
                log_action(
                    user=request.user,
                    action='utilisateur_modifie',
                    description=f"Agent {updated_agent.username} modifié par {request.user.username}",
                    donnees_supplementaires={'agent_id': updated_agent.id}
                )
                
                messages.success(request, f"Agent {updated_agent.username} modifié avec succès")
                return redirect('admin_agents')
        else:
            form = AgentForm(instance=agent)
        
        context = {
            'form': form,
            'agent': agent,
            'action': 'Édition'
        }
        
        return render(request, 'admin/creer_utilisateur.html', context)
        
    except Exception as e:
        messages.error(request, f"Erreur lors de la modification: {e}")
        return redirect('admin_agents')

def delete_admin(request, admin_id):
    """Supprimer un administrateur"""
    try:
        admin = get_object_or_404(Utilisateur, id=admin_id, role='admin')
        
        if request.method == 'POST':
            admin_username = admin.username
            admin.delete()
            
            # Log de l'action
            log_action(
                user=request.user,
                action='utilisateur_supprime',
                description=f"Administrateur {admin_username} supprimé par {request.user.username}",
                donnees_supplementaires={'admin_id': admin_id}
            )
            
            messages.success(request, f"Administrateur {admin_username} supprimé avec succès")
            return redirect('togo_admin:users')
        
        context = {'admin': admin}
        return render(request, 'admin/delete_admin.html', context)
        
    except Exception as e:
        messages.error(request, f"Erreur lors de la suppression: {e}")
        return redirect('togo_admin:users')


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
    
    if user.role == 'admin':
        regions = Region.objects.all().order_by('nom')
    if user.region:
        prefectures = Prefecture.objects.filter(region=user.region, actif=True).order_by('nom')
    
    # Rôles autorisés
    role_choices = [
        ('citoyen', 'Citoyen'),
        ('agent', 'Agent de gestion'),
    ]
    if user.role == 'admin':
        role_choices.append(('admin', 'Administrateur'))
    
    context = {
        'regions': regions,
        'prefectures': prefectures,
        'role_choices': role_choices,
        'user_region': user.region,
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
        # Vérifier si c'est une requête JSON (AJAX) ou un formulaire classique
        if request.content_type == 'application/json':
            try:
                import json
                data = json.loads(request.body)
                
                # Récupérer les données JSON
                username = data.get('username')
                email = data.get('email')
                first_name = data.get('first_name')
                last_name = data.get('last_name')
                telephone = data.get('telephone', '')
                password = data.get('password')
                role = data.get('role', 'citoyen')
                region_id = data.get('region')
                prefecture_id = data.get('prefecture')
                is_verified = data.get('is_verified', False)
                
                # Validation des données requises
                required_fields = ['username', 'email', 'first_name', 'last_name', 'password']
                missing_fields = [field for field in required_fields if not data.get(field)]
                
                if missing_fields:
                    return JsonResponse({
                        'success': False, 
                        'error': f'Champs manquants: {", ".join(missing_fields)}'
                    })
                
                # Vérifier que l'username et l'email n'existent pas déjà
                if Utilisateur.objects.filter(username=username).exists():
                    return JsonResponse({'success': False, 'error': 'Ce nom d\'utilisateur existe déjà'})
                
                if Utilisateur.objects.filter(email=email).exists():
                    return JsonResponse({'success': False, 'error': 'Cette adresse email est déjà utilisée'})
                
                # Récupérer la région et la préfecture si spécifiées
                region = None
                prefecture = None
                if region_id:
                    try:
                        region = Region.objects.get(id=region_id)
                    except Region.DoesNotExist:
                        return JsonResponse({'success': False, 'error': 'Région invalide'})
                
                if prefecture_id:
                    try:
                        prefecture = Prefecture.objects.get(id=prefecture_id)
                    except Prefecture.DoesNotExist:
                        return JsonResponse({'success': False, 'error': 'Préfecture invalide'})
                
                # Créer l'utilisateur
                user = Utilisateur.objects.create(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    telephone=telephone,
                    role=role,
                    region=region,
                    prefecture=prefecture,
                    verifie=is_verified,
                    is_active=True
                )
                user.set_password(password)
                if is_verified:
                    user.date_verification = timezone.now()
                user.save()
                
                # Log de l'action
                log_action(
                    user=request.user,
                    action='utilisateur_cree',
                    description=f'Nouvel utilisateur créé: {user.username} ({user.get_full_name()})',
                    ip_address=get_user_ip(request),
                    user_agent=get_user_agent(request),
                    donnees_supplementaires={
                        'user_id': user.id,
                        'role': role,
                        'email': email
                    }
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'Utilisateur {user.get_full_name()} créé avec succès',
                    'user_id': user.id
                })
                
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'error': 'Données JSON invalides'})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
        
        else:
            # Traitement formulaire classique (existant)
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
                    ip_address=get_user_ip(request),
                    user_agent=get_user_agent(request),
                    donnees_supplementaires={
                        'user_id': user.id,
                        'role': role,
                        'email': email
                    }
                )
                
                messages.success(request, f'Utilisateur {user.get_full_name()} créé avec succès.')
                return redirect('togo_admin:users')
                
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


# ============ GESTION DES SIGNALEMENTS ============

@admin_required
def signalements_list(request):
    """Liste de tous les signalements pour l'admin"""
    user = request.user
    
    # Filtrer par région de l'admin si nécessaire
    region_filter = Q()
    if user.region:
        # Pour admin/agent: signalements de leur région OU sans région assignée
        region_filter = Q(region=user.region) | Q(region__isnull=True)
    
    # Filtres depuis les paramètres GET
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    search_query = request.GET.get('search', '')
    
    # Requête de base
    signalements_query = Signalement.objects.select_related(
        'objet', 'utilisateur', 'region', 'prefecture'
    ).filter(region_filter)
    
    # Appliquer les filtres
    if status_filter:
        signalements_query = signalements_query.filter(statut=status_filter)
    
    if search_query:
        signalements_query = signalements_query.filter(
            Q(objet__nom__icontains=search_query) |
            Q(lieu__icontains=search_query) |
            Q(commentaire__icontains=search_query) |
            Q(utilisateur__username__icontains=search_query)
        )
    
    # Ordonner par date de création (plus récents en premier)
    signalements = signalements_query.order_by('-date_signalement')
    
    # Pagination
    paginator = Paginator(signalements, 20)
    page_number = request.GET.get('page')
    signalements_page = paginator.get_page(page_number)
    
    # Statistiques
    today = timezone.now().date()
    stats = {
        'total_count': signalements_query.count(),
        'perdu_count': signalements_query.filter(statut='perdu').count(),
        'trouve_count': signalements_query.filter(statut='trouve').count(),
        'retourne_count': signalements_query.filter(statut='retourne').count(),
        'today_count': signalements_query.filter(date_signalement__date=today).count(),
        'unique_users': signalements_query.values('utilisateur').distinct().count(),
    }
    
    context = {
        'signalements': signalements_page,
        'stats': stats,
        'current_status_filter': status_filter,
        'current_search': search_query,
        'status_choices': Signalement.TYPE_CHOICES,
    }
    
    return render(request, 'admin/signalements_list.html', context)


@admin_required
def signalement_detail(request, signalement_id):
    """Détails d'un signalement avec possibilité de modification"""
    user = request.user
    signalement = get_object_or_404(Signalement, id=signalement_id)
    
    # Vérifier les permissions régionales
    if user.region and signalement.region != user.region:
        messages.error(request, "Vous n'avez pas l'autorisation de voir ce signalement.")
        return redirect('togo_admin:signalements_list')
    
    # Récupérer les commentaires
    commentaires = CommentaireAnonyme.objects.filter(
        signalement=signalement
    ).order_by('-date_creation')
    
    context = {
        'signalement': signalement,
        'commentaires': commentaires,
        'can_edit': True,
    }
    
    return render(request, 'admin/signalement_detail.html', context)


@admin_required
def signalement_edit(request, signalement_id):
    """Éditer un signalement"""
    user = request.user
    signalement = get_object_or_404(Signalement, id=signalement_id)
    
    # Vérifier les permissions
    if user.region and signalement.region != user.region:
        messages.error(request, "Vous n'avez pas l'autorisation de modifier ce signalement.")
        return redirect('togo_admin:signalements_list')
    
    if request.method == 'POST':
        try:
            # Mettre à jour les champs modifiables
            signalement.lieu = request.POST.get('lieu', signalement.lieu)
            signalement.commentaire = request.POST.get('commentaire', signalement.commentaire)
            signalement.statut = request.POST.get('statut', signalement.statut)
            
            # Mise à jour de l'objet si nécessaire
            if signalement.objet:
                signalement.objet.nom = request.POST.get('nom_objet', signalement.objet.nom)
                signalement.objet.description = request.POST.get('description_objet', signalement.objet.description)
                signalement.objet.save()
            
            # Photo si uploadée
            if 'photo' in request.FILES:
                signalement.photo = request.FILES['photo']
            
            # Géolocalisation
            region_id = request.POST.get('region')
            if region_id:
                try:
                    signalement.region = Region.objects.get(id=region_id)
                except Region.DoesNotExist:
                    pass
            
            prefecture_id = request.POST.get('prefecture')
            if prefecture_id:
                try:
                    signalement.prefecture = Prefecture.objects.get(id=prefecture_id)
                except Prefecture.DoesNotExist:
                    pass
            
            signalement.save()
            
            # Log de l'action
            log_action(
                user=user,
                action='signalement_modifie',
                description=f'Signalement #{signalement.id} modifié par {user.username}',
                donnees_supplementaires={
                    'signalement_id': signalement.id,
                    'objet': signalement.objet.nom if signalement.objet else None
                }
            )
            
            messages.success(request, "✅ Signalement modifié avec succès !")
            return redirect('togo_admin:signalement_detail', signalement_id=signalement.id)
            
        except Exception as e:
            messages.error(request, f"❌ Erreur lors de la modification : {str(e)}")
    
    # Données pour le formulaire
    regions = Region.objects.filter(actif=True).order_by('nom')
    prefectures = Prefecture.objects.filter(
        region=signalement.region, actif=True
    ).order_by('nom') if signalement.region else Prefecture.objects.none()
    
    context = {
        'signalement': signalement,
        'regions': regions,
        'prefectures': prefectures,
        'status_choices': Signalement.TYPE_CHOICES,
    }
    
    return render(request, 'admin/signalement_edit.html', context)


@admin_required
def signalement_delete(request, signalement_id):
    user = request.user
    
    if not user.role == 'admin':
        messages.error(request, "Vous n'avez pas l'autorisation de supprimer des signalements.")
        return redirect('togo_admin:signalements_list')
    
    signalement = get_object_or_404(Signalement, id=signalement_id)
    
    # Vérifier les permissions régionales
    if user.region and signalement.region != user.region:
        messages.error(request, "Vous n'avez pas l'autorisation de supprimer ce signalement.")
        return redirect('togo_admin:signalements_list')
    
    if request.method == 'POST':
        objet_nom = signalement.objet.nom if signalement.objet else f"Signalement #{signalement.id}"
        
        # Log avant suppression
        log_action(
            user=user,
            action='signalement_supprime',
            description=f'Signalement #{signalement.id} ({objet_nom}) supprimé par {user.username}',
            donnees_supplementaires={
                'signalement_id': signalement.id,
                'objet': objet_nom,
                'utilisateur': signalement.utilisateur.username if signalement.utilisateur else None
            }
        )
        
        signalement.delete()
        messages.warning(request, f"🗑️ Signalement '{objet_nom}' supprimé avec succès.")
        return redirect('togo_admin:signalements_list')
    
    context = {
        'signalement': signalement,
        'objet_nom': signalement.objet.nom if signalement.objet else f"Signalement #{signalement.id}"
    }
    
    return render(request, 'admin/signalement_delete.html', context)


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
            return redirect('togo_admin:users')
            
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
    
    return redirect('togo_admin:users')


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


# ============ NOUVELLES VUES API POUR GESTION UTILISATEURS ============

@admin_required
def user_detail(request, user_id):
    """Détails d'un utilisateur"""
    user = get_object_or_404(Utilisateur, id=user_id)
    return render(request, 'admin/user_detail.html', {'user': user})


@admin_required
def verify_user(request, user_id):
    """Vérifier un utilisateur (API)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        user = get_object_or_404(Utilisateur, id=user_id)
        user.verifie = True
        user.date_verification = timezone.now()
        user.save()
        
        log_action(
            user=request.user,
            action='utilisateur_verifie',
            description=f'Utilisateur {user.username} vérifié',
            ip_address=get_user_ip(request),
            user_agent=get_user_agent(request),
            donnees_supplementaires={'target_user_id': user.id}
        )
        
        return JsonResponse({'success': True, 'message': 'Utilisateur vérifié avec succès'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def toggle_user_status_api(request, user_id):
    """Activer/Désactiver un utilisateur (API)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        import json
        data = json.loads(request.body)
        activate = data.get('activate', True)
        
        user = get_object_or_404(Utilisateur, id=user_id)
        user.is_active = activate
        user.save()
        
        action = 'utilisateur_active' if activate else 'utilisateur_desactive'
        description = f'Utilisateur {user.username} {"activé" if activate else "désactivé"}'
        
        log_action(
            user=request.user,
            action=action,
            description=description,
            ip_address=get_user_ip(request),
            user_agent=get_user_agent(request),
            donnees_supplementaires={'target_user_id': user.id}
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Utilisateur {"activé" if activate else "désactivé"} avec succès'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def reset_user_password(request, user_id):
    """Réinitialiser le mot de passe d'un utilisateur"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        import random
        import string
        
        user = get_object_or_404(Utilisateur, id=user_id)
        
        # Générer un nouveau mot de passe
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        user.set_password(new_password)
        user.save()
        
        log_action(
            user=request.user,
            action='mot_de_passe_reinitialise',
            description=f'Mot de passe réinitialisé pour {user.username}',
            ip_address=get_user_ip(request),
            user_agent=get_user_agent(request),
            donnees_supplementaires={'target_user_id': user.id}
        )
        
        return JsonResponse({
            'success': True, 
            'new_password': new_password,
            'message': 'Mot de passe réinitialisé avec succès'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def send_user_message(request, user_id):
    """Envoyer un message à un utilisateur"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        import json
        data = json.loads(request.body)
        message = data.get('message', '')
        
        if not message:
            return JsonResponse({'success': False, 'error': 'Message requis'})
        
        user = get_object_or_404(Utilisateur, id=user_id)
        
        # Créer une notification
        create_notification(
            destinataire=user,
            type_notification='message_admin',
            titre='Message de l\'administration',
            message=message,
            importante=True,
            envoyer_email=True
        )
        
        log_action(
            user=request.user,
            action='message_envoye',
            description=f'Message envoyé à {user.username}',
            ip_address=get_user_ip(request),
            user_agent=get_user_agent(request),
            donnees_supplementaires={'target_user_id': user.id, 'message': message}
        )
        
        return JsonResponse({'success': True, 'message': 'Message envoyé avec succès'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def bulk_user_action(request):
    """Actions groupées sur les utilisateurs"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        import json
        data = json.loads(request.body)
        action = data.get('action')
        user_ids = data.get('users', [])
        
        if not user_ids:
            return JsonResponse({'success': False, 'error': 'Aucun utilisateur sélectionné'})
        
        users = Utilisateur.objects.filter(id__in=user_ids)
        affected_count = 0
        
        if action == 'verify':
            affected_count = users.update(verifie=True, date_verification=timezone.now())
            action_desc = 'Vérification en masse'
            
        elif action == 'activate':
            affected_count = users.update(is_active=True)
            action_desc = 'Activation en masse'
            
        elif action == 'deactivate':
            affected_count = users.update(is_active=False)
            action_desc = 'Désactivation en masse'
            
        elif action == 'export':
            # Logique d'export (à implémenter selon les besoins)
            return JsonResponse({'success': True, 'redirect': '/admin/users/?export=csv'})
            
        elif action == 'notify':
            # Notification en masse (via autre endpoint)
            return JsonResponse({'success': True, 'affected': len(user_ids)})
            
        else:
            return JsonResponse({'success': False, 'error': 'Action non reconnue'})
        
        log_action(
            user=request.user,
            action='action_groupee',
            description=f'{action_desc} sur {affected_count} utilisateurs',
            ip_address=get_user_ip(request),
            user_agent=get_user_agent(request),
            donnees_supplementaires={'action': action, 'user_ids': user_ids}
        )
        
        return JsonResponse({
            'success': True, 
            'affected': affected_count,
            'message': f'{action_desc} appliquée à {affected_count} utilisateurs'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def notify_users(request):
    """Envoyer des notifications à plusieurs utilisateurs"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        import json
        data = json.loads(request.body)
        message = data.get('message', '')
        user_selection = data.get('users', 'all')
        
        if not message:
            return JsonResponse({'success': False, 'error': 'Message requis'})
        
        if user_selection == 'all':
            users = Utilisateur.objects.filter(is_active=True)
        else:
            users = Utilisateur.objects.filter(id__in=user_selection, is_active=True)
        
        sent_count = 0
        for user in users:
            create_notification(
                destinataire=user,
                type_notification='notification_generale',
                titre='Notification générale',
                message=message,
                importante=True,
                envoyer_email=False
            )
            sent_count += 1
        
        log_action(
            user=request.user,
            action='notification_masse',
            description=f'Notification envoyée à {sent_count} utilisateurs',
            ip_address=get_user_ip(request),
            user_agent=get_user_agent(request),
            donnees_supplementaires={'message': message, 'sent_count': sent_count}
        )
        
        return JsonResponse({
            'success': True, 
            'sent': sent_count,
            'message': f'Notifications envoyées à {sent_count} utilisateurs'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def create_agent_api(request):
    """Créer un agent (API)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        import json
        data = json.loads(request.body)
        
        # Validation des données requises
        required_fields = ['username', 'email', 'first_name', 'last_name', 'telephone', 'region', 'prefecture']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return JsonResponse({
                'success': False, 
                'error': f'Champs manquants: {", ".join(missing_fields)}'
            })
        
        # Vérifier que l'username et l'email n'existent pas déjà
        if Utilisateur.objects.filter(username=data['username']).exists():
            return JsonResponse({'success': False, 'error': 'Ce nom d\'utilisateur existe déjà'})
        
        if Utilisateur.objects.filter(email=data['email']).exists():
            return JsonResponse({'success': False, 'error': 'Cette adresse email est déjà utilisée'})
        
        # Récupérer la région et la préfecture
        try:
            region = Region.objects.get(id=data['region'])
            prefecture = Prefecture.objects.get(id=data['prefecture'])
        except (Region.DoesNotExist, Prefecture.DoesNotExist):
            return JsonResponse({'success': False, 'error': 'Région ou préfecture invalide'})
        
        # Créer l'agent
        import random
        import string
        
        # Générer un mot de passe temporaire
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        
        agent = Utilisateur.objects.create(
            username=data['username'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            telephone=data['telephone'],
            role='agent',
            region=region,
            prefecture=prefecture,
            verifie=True,
            is_active=True
        )
        agent.set_password(temp_password)
        agent.save()
        
        log_action(
            user=request.user,
            action='agent_cree',
            description=f'Agent {agent.username} créé',
            ip_address=get_user_ip(request),
            user_agent=get_user_agent(request),
            donnees_supplementaires={'agent_id': agent.id, 'region': region.nom, 'prefecture': prefecture.nom}
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Agent créé avec succès',
            'agent_id': agent.id,
            'temp_password': temp_password
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required 
def get_prefectures(request, region_id):
    """API pour récupérer les préfectures d'une région"""
    try:
        region = get_object_or_404(Region, id=region_id)
        prefectures = Prefecture.objects.filter(region=region).order_by('nom')
        
        prefectures_data = [
            {'id': pref.id, 'nom': pref.nom}
            for pref in prefectures
        ]
        
        return JsonResponse(prefectures_data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)