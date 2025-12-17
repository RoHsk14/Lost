from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Supprime tous les utilisateurs de la base de données'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Supprime TOUS les utilisateurs (y compris superusers)',
        )
        parser.add_argument(
            '--role',
            type=str,
            help='Supprime les utilisateurs d\'un rôle spécifique (citoyen/admin/agent)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force la suppression sans demander de confirmation',
        )

    def handle(self, *args, **options):
        self.stdout.write("🗑️ Suppression des utilisateurs - Lost & Found")
        self.stdout.write("=" * 50)

        # Statistiques initiales
        total_users = User.objects.count()
        self.stdout.write(f"📊 Utilisateurs actuels: {total_users}")

        if total_users == 0:
            self.stdout.write(self.style.SUCCESS("✅ Aucun utilisateur à supprimer"))
            return

        # Déterminer quels utilisateurs supprimer
        if options['all']:
            users_to_delete = User.objects.all()
            message = "TOUS les utilisateurs (y compris superusers)"
        elif options['role']:
            role = options['role'].lower()
            if role not in ['citoyen', 'admin', 'agent']:
                self.stdout.write(
                    self.style.ERROR("❌ Rôle invalide. Utilisez: citoyen, admin, ou agent")
                )
                return
            users_to_delete = User.objects.filter(role=role)
            message = f"les utilisateurs avec le rôle '{role}'"
        else:
            users_to_delete = User.objects.filter(is_superuser=False)
            message = "tous les utilisateurs normaux (superusers protégés)"

        count_to_delete = users_to_delete.count()

        if count_to_delete == 0:
            self.stdout.write(self.style.SUCCESS("✅ Aucun utilisateur correspondant à supprimer"))
            return

        self.stdout.write(f"🎯 Suppression de {message}")
        self.stdout.write(f"📈 {count_to_delete} utilisateur(s) à supprimer")

        # Demander confirmation si --force n'est pas utilisé
        if not options['force']:
            confirm = input(f"\n⚠️  Êtes-vous sûr de vouloir supprimer {count_to_delete} utilisateur(s) ? (oui/non): ")
            if confirm.lower() not in ['oui', 'yes', 'o', 'y']:
                self.stdout.write(self.style.WARNING("❌ Suppression annulée"))
                return

        try:
            # Effectuer la suppression
            deleted_count, details = users_to_delete.delete()
            
            self.stdout.write(
                self.style.SUCCESS(f"✅ Suppression réussie!")
            )
            self.stdout.write(f"   {deleted_count} utilisateur(s) supprimé(s)")
            
            # Afficher les détails si demandé
            if self.verbosity >= 2:
                self.stdout.write(f"   Détails: {details}")

            # Statistiques finales
            remaining_users = User.objects.count()
            self.stdout.write(f"📊 Utilisateurs restants: {remaining_users}")
            
            if remaining_users > 0 and not options['all']:
                superusers = User.objects.filter(is_superuser=True).count()
                self.stdout.write(f"   (dont {superusers} superutilisateur(s) protégé(s))")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Erreur lors de la suppression: {e}")
            )
