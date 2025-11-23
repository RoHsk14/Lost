#!/usr/bin/env python3
"""
Script de suppression des utilisateurs pour Lost & Found
⚠️ ATTENTION: Ce script supprime des données définitivement !
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lostfound.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from core.models import Utilisateur

User = get_user_model()

def supprimer_tous_utilisateurs():
    """Supprime tous les utilisateurs (sauf superusers par sécurité)"""
    print("🗑️ Suppression des utilisateurs...")
    print("=" * 50)
    
    # Compter les utilisateurs
    total_users = User.objects.count()
    superusers = User.objects.filter(is_superuser=True).count()
    regular_users = User.objects.filter(is_superuser=False).count()
    
    print(f"📊 État actuel:")
    print(f"   Total utilisateurs: {total_users}")
    print(f"   Superutilisateurs: {superusers}")
    print(f"   Utilisateurs normaux: {regular_users}")
    
    if total_users == 0:
        print("✅ Aucun utilisateur à supprimer")
        return
    
    # Confirmation
    response = input(f"\n⚠️  Voulez-vous supprimer {regular_users} utilisateurs normaux ? (oui/non): ")
    
    if response.lower() not in ['oui', 'yes', 'o', 'y']:
        print("❌ Suppression annulée")
        return
    
    try:
        # Supprimer tous les utilisateurs sauf les superusers
        deleted_count, details = User.objects.filter(is_superuser=False).delete()
        
        print(f"✅ Suppression réussie!")
        print(f"   {deleted_count} utilisateurs supprimés")
        print(f"   Détails: {details}")
        
        # Vérification
        remaining_users = User.objects.count()
        print(f"   Utilisateurs restants: {remaining_users} (superusers protégés)")
        
    except Exception as e:
        print(f"❌ Erreur lors de la suppression: {e}")

def supprimer_utilisateurs_par_role():
    """Supprime les utilisateurs selon leur rôle"""
    print("\n🎯 Suppression par rôle:")
    
    # Compter par rôle
    citoyens = User.objects.filter(role='citoyen').count()
    admins = User.objects.filter(role='admin').count()
    agents = User.objects.filter(role='agent').count()
    
    print(f"   Citoyens: {citoyens}")
    print(f"   Admins: {admins}")
    print(f"   Agents: {agents}")
    
    role_choice = input("\nQuel rôle supprimer ? (citoyen/admin/agent/tous): ")
    
    if role_choice == 'tous':
        supprimer_tous_utilisateurs()
        return
    elif role_choice in ['citoyen', 'admin', 'agent']:
        users_to_delete = User.objects.filter(role=role_choice, is_superuser=False)
        count = users_to_delete.count()
        
        if count == 0:
            print(f"✅ Aucun utilisateur avec le rôle '{role_choice}'")
            return
        
        confirm = input(f"Supprimer {count} utilisateurs '{role_choice}' ? (oui/non): ")
        if confirm.lower() in ['oui', 'yes', 'o', 'y']:
            deleted_count, details = users_to_delete.delete()
            print(f"✅ {deleted_count} utilisateurs '{role_choice}' supprimés")
        else:
            print("❌ Suppression annulée")
    else:
        print("❌ Rôle invalide")

def reset_base_donnees():
    """Reset complet de la base de données"""
    print("\n💥 RESET COMPLET DE LA BASE DE DONNÉES")
    print("⚠️  ATTENTION: Ceci supprime TOUTES les données !")
    
    confirm = input("Êtes-vous ABSOLUMENT sûr ? Tapez 'SUPPRIMER TOUT': ")
    
    if confirm == 'SUPPRIMER TOUT':
        try:
            # Supprimer tous les utilisateurs
            User.objects.all().delete()
            
            # Supprimer les autres données
            from core.models import Signalement, Objet, ObjetPerdu
            Signalement.objects.all().delete()
            Objet.objects.all().delete()
            ObjetPerdu.objects.all().delete()
            
            print("✅ Base de données complètement vidée !")
            print("💡 Pensez à créer un nouveau superutilisateur :")
            print("   python manage.py createsuperuser")
            
        except Exception as e:
            print(f"❌ Erreur lors du reset: {e}")
    else:
        print("❌ Reset annulé")

def menu_principal():
    """Menu principal de suppression"""
    print("🗑️ GESTION DES UTILISATEURS - Lost & Found")
    print("=" * 50)
    print("1. Supprimer tous les utilisateurs normaux")
    print("2. Supprimer par rôle (citoyen/admin/agent)")
    print("3. Reset complet de la base de données")
    print("4. Afficher les statistiques")
    print("5. Quitter")
    
    choice = input("\nVotre choix (1-5): ")
    
    if choice == '1':
        supprimer_tous_utilisateurs()
    elif choice == '2':
        supprimer_utilisateurs_par_role()
    elif choice == '3':
        reset_base_donnees()
    elif choice == '4':
        afficher_statistiques()
    elif choice == '5':
        print("👋 Au revoir !")
        return
    else:
        print("❌ Choix invalide")
    
    input("\nAppuyez sur Entrée pour continuer...")
    menu_principal()

def afficher_statistiques():
    """Affiche les statistiques des utilisateurs"""
    print("\n📊 STATISTIQUES DES UTILISATEURS")
    print("=" * 40)
    
    total = User.objects.count()
    superusers = User.objects.filter(is_superuser=True).count()
    actifs = User.objects.filter(is_active=True).count()
    
    print(f"Total utilisateurs: {total}")
    print(f"Superutilisateurs: {superusers}")
    print(f"Utilisateurs actifs: {actifs}")
    
    # Par rôle
    print(f"\nPar rôle:")
    for role_code, role_name in User.ROLE_CHOICES:
        count = User.objects.filter(role=role_code).count()
        print(f"   {role_name}: {count}")
    
    # Signalements par utilisateur
    from core.models import Signalement
    signalements = Signalement.objects.count()
    print(f"\nSignalements total: {signalements}")

if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\n👋 Arrêt du programme")
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
