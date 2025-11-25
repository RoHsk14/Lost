@echo off
echo 🚀 DÉMARRAGE DU SERVEUR TOGORETROUVÉ
echo ===================================

cd /d "c:\Users\MR\Desktop\Stage 2\Lost\lostfound"

echo ✅ Vérification de Django...
python manage.py check
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Erreurs détectées dans Django
    pause
    exit /b 1
)

echo ✅ Django OK - Démarrage du serveur...
echo.
echo 🌐 Interface Admin: http://127.0.0.1:8000/togoretrouve-admin/
echo 👤 Login: admin
echo 🔑 Mot de passe: admin123
echo.
echo 📋 URLs disponibles:
echo    • Dashboard: /togoretrouve-admin/
echo    • Utilisateurs: /togoretrouve-admin/users/
echo    • Agents: /togoretrouve-admin/agents/
echo    • Déclarations: /togoretrouve-admin/declarations/
echo    • Rapports: /togoretrouve-admin/reports/
echo    • Statistiques: /togoretrouve-admin/statistics/
echo    • Régions: /togoretrouve-admin/regions/
echo    • Paramètres: /togoretrouve-admin/settings/
echo.
echo 🚀 Serveur en cours de démarrage...

python manage.py runserver