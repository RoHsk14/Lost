from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Crée un compte administrateur initial si la table des utilisateurs est vide.
        # Ceci évite de bloquer l'accès en cas de base fraîche.
        try:
            from django.contrib.auth import get_user_model
            from django.db.utils import OperationalError, ProgrammingError
            User = get_user_model()

            # Protéger contre l'exécution quand la DB/migrations ne sont pas prêtes
            try:
                user_count = User.objects.count()
            except (OperationalError, ProgrammingError):
                return

            if user_count == 0:
                username = 'admin1'
                password = 'admin123'
                email = 'admin@example.com'
                if not User.objects.filter(username=username).exists():
                    # Utiliser create_user pour s'assurer des validations
                    u = User.objects.create_user(username=username, email=email, password=password)
                    u.is_staff = True
                    u.is_superuser = True
                    # Si le modèle possède le champ 'role', le définir sur 'admin'
                    if hasattr(u, 'role'):
                        try:
                            u.role = 'admin'
                        except Exception:
                            pass
                    u.save()
                    # Log minimal pour l'administrateur
                    import sys
                    print('Created initial admin account -> username: admin1 password: admin123', file=sys.stderr)
        except Exception:
            # Ne pas faire échouer l'application si l'initialisation échoue
            import sys
            print('Initial admin creation: skipped or failed', file=sys.stderr)
