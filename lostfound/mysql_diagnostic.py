#!/usr/bin/env python3
"""
Script de diagnostic MySQL pour Lost & Found
Teste la connexion MySQL et identifie les problèmes
"""
import sys
import os

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lostfound.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import django
    django.setup()
except Exception as e:
    print(f"❌ Erreur lors du setup Django: {e}")
    sys.exit(1)

def test_mysql_connection():
    """Test de connexion MySQL étape par étape"""
    print("🔍 Diagnostic MySQL pour Lost & Found")
    print("=" * 50)
    
    # 1. Test de l'import mysqlclient
    try:
        import MySQLdb
        print("✅ mysqlclient installé correctement")
    except ImportError as e:
        print(f"❌ mysqlclient non installé: {e}")
        return False
    
    # 2. Test de connexion MySQL basique
    try:
        import mysql.connector
        print("✅ mysql-connector disponible")
    except ImportError:
        print("⚠️ mysql-connector non disponible, utilisation de mysqlclient")
    
    # 3. Test de connexion avec les paramètres Django
    from django.conf import settings
    
    db_config = settings.DATABASES['default']
    print(f"\n📋 Configuration actuelle:")
    print(f"   Engine: {db_config.get('ENGINE', 'Non défini')}")
    print(f"   Database: {db_config.get('NAME', 'Non défini')}")
    print(f"   User: {db_config.get('USER', 'Non défini')}")
    print(f"   Host: {db_config.get('HOST', 'Non défini')}")
    print(f"   Port: {db_config.get('PORT', 'Non défini')}")
    
    # Si SQLite, on arrête là
    if 'sqlite' in db_config.get('ENGINE', ''):
        print("✅ Configuration SQLite détectée - fonctionne correctement")
        return True
    
    # 4. Test de connexion MySQL
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✅ Connexion MySQL réussie - Version: {version[0]}")
            return True
    except Exception as e:
        print(f"❌ Erreur de connexion MySQL: {e}")
        
        # Suggestions de correction
        print(f"\n🔧 Suggestions de correction:")
        error_msg = str(e).lower()
        
        if "access denied" in error_msg:
            print("   - Vérifiez le mot de passe MySQL dans settings.py")
            print("   - Vérifiez que l'utilisateur 'root' existe")
        elif "unknown database" in error_msg:
            print("   - Créez la base de données: CREATE DATABASE lostfound_db;")
        elif "can't connect" in error_msg:
            print("   - Démarrez le service MySQL")
            print("   - Vérifiez que MySQL écoute sur le port 3306")
        else:
            print(f"   - Erreur: {e}")
        
        return False

def test_mysql_service():
    """Test du service MySQL"""
    print(f"\n🔍 Test du service MySQL:")
    
    # Test de connexion réseau
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('localhost', 3306))
        sock.close()
        
        if result == 0:
            print("✅ MySQL écoute sur le port 3306")
            return True
        else:
            print("❌ MySQL n'écoute pas sur le port 3306")
            return False
    except Exception as e:
        print(f"❌ Erreur de test réseau: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Démarrage du diagnostic...")
    
    mysql_service_ok = test_mysql_service()
    mysql_connection_ok = test_mysql_connection()
    
    print(f"\n📊 Résultats:")
    print(f"   Service MySQL: {'✅' if mysql_service_ok else '❌'}")
    print(f"   Connexion Django: {'✅' if mysql_connection_ok else '❌'}")
    
    if mysql_service_ok and mysql_connection_ok:
        print(f"\n🎉 MySQL fonctionne parfaitement !")
    elif not mysql_service_ok:
        print(f"\n⚠️  Démarrez d'abord le service MySQL")
    else:
        print(f"\n⚠️  Vérifiez la configuration dans settings.py")
