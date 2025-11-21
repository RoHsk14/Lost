from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import (
    Utilisateur, Region, Prefecture, Localisation, Objet,
    Declaration, Reclamation, Notification
)


class UtilisateurModelTest(TestCase):
    """Tests pour le modèle Utilisateur."""
    
    def setUp(self):
        self.region = Region.objects.create(nom="Maritime")
        self.prefecture = Prefecture.objects.create(
            nom="Golfe",
            region=self.region
        )
    
    def test_create_user_citoyen(self):
        """Test création d'un utilisateur citoyen."""
        user = Utilisateur.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            nom="Dupont",
            prenom="Jean",
            telephone="+22890123456",
            role="citoyen"
        )
        self.assertEqual(user.role, "citoyen")
        self.assertFalse(user.can_validate_objects())
        self.assertFalse(user.can_access_admin())
    
    def test_create_user_agent(self):
        """Test création d'un agent."""
        agent = Utilisateur.objects.create_user(
            username="agent1",
            email="agent@example.com",
            password="testpass123",
            role="agent"
        )
        self.assertTrue(agent.can_validate_objects())
        self.assertFalse(agent.can_access_admin())
    
    def test_create_user_admin(self):
        """Test création d'un administrateur."""
        admin = Utilisateur.objects.create_user(
            username="admin1",
            email="admin@example.com",
            password="testpass123",
            role="admin"
        )
        self.assertTrue(admin.can_validate_objects())
        self.assertTrue(admin.can_access_admin())


class LocalisationModelTest(TestCase):
    """Tests pour le modèle Localisation."""
    
    def test_create_localisation(self):
        """Test création d'une localisation."""
        loc = Localisation.objects.create(
            region="Maritime",
            prefecture="Golfe",
            quartier="Bè",
            commissariat="Bè"
        )
        self.assertIn("Bè", str(loc))
        self.assertIn("Golfe", str(loc))
        self.assertIn("Maritime", str(loc))
    
    def test_localisation_with_gps(self):
        """Test localisation avec coordonnées GPS."""
        loc = Localisation.objects.create(
            region="Maritime",
            prefecture="Golfe",
            quartier="Bè",
            latitude=6.1375,
            longitude=1.2123
        )
        self.assertEqual(loc.latitude, 6.1375)
        self.assertEqual(loc.longitude, 1.2123)
    
    def test_localisation_invalid_coordinates(self):
        """Test validation des coordonnées GPS."""
        loc = Localisation(
            region="Maritime",
            prefecture="Golfe",
            quartier="Bè",
            latitude=100  # Invalid
        )
        with self.assertRaises(ValidationError):
            loc.full_clean()


class ObjetModelTest(TestCase):
    """Tests pour le modèle Objet."""
    
    def setUp(self):
        self.localisation = Localisation.objects.create(
            region="Maritime",
            prefecture="Golfe",
            quartier="Bè"
        )
        self.user = Utilisateur.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.agent = Utilisateur.objects.create_user(
            username="agent1",
            password="testpass123",
            role="agent"
        )
    
    def test_create_objet_perdu(self):
        """Test création d'un objet perdu."""
        objet = Objet.objects.create(
            typeObjet="TELEPHONE",
            nom="iPhone 13",
            description="iPhone 13 Pro Max bleu",
            couleur="Bleu",
            marque="Apple",
            lieuPerte=self.localisation,
            datePerte=timezone.now(),
            proprietaire=self.user,
            est_perdu=True
        )
        self.assertEqual(objet.etat, "CREE")
        self.assertTrue(objet.est_perdu)
        self.assertIn("Perdu", str(objet))
    
    def test_create_objet_trouve(self):
        """Test création d'un objet trouvé."""
        objet = Objet.objects.create(
            typeObjet="PORTEFEUILLE",
            nom="Portefeuille marron",
            description="Portefeuille en cuir",
            couleur="Marron",
            lieuPerte=self.localisation,
            datePerte=timezone.now(),
            est_perdu=False
        )
        self.assertFalse(objet.est_perdu)
        self.assertIn("Trouvé", str(objet))
    
    def test_objet_change_etat(self):
        """Test changement d'état d'un objet."""
        objet = Objet.objects.create(
            typeObjet="CLES",
            nom="Clés de voiture",
            description="Trousseau avec 3 clés",
            couleur="Argent",
            lieuPerte=self.localisation,
            datePerte=timezone.now(),
            est_perdu=True
        )
        
        # Test transition valide
        self.assertTrue(objet.change_etat("EN_VALIDATION", self.agent))
        self.assertEqual(objet.etat, "EN_VALIDATION")
        
        # Test transition invalide (EN_VALIDATION ne peut pas aller à RECLAME directement)
        with self.assertRaises(ValidationError):
            objet.change_etat("RECLAME")
    
    def test_objet_peut_etre_reclame(self):
        """Test si un objet peut être réclamé."""
        objet = Objet.objects.create(
            typeObjet="DOCUMENT",
            nom="Passeport",
            description="Passeport togolais",
            couleur="Vert",
            lieuPerte=self.localisation,
            datePerte=timezone.now(),
            est_perdu=False,
            etat="PUBLIE"
        )
        self.assertTrue(objet.peut_etre_reclame())


class DeclarationModelTest(TestCase):
    """Tests pour le modèle Declaration."""
    
    def setUp(self):
        self.localisation = Localisation.objects.create(
            region="Maritime",
            prefecture="Golfe",
            quartier="Bè"
        )
        self.user = Utilisateur.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.objet = Objet.objects.create(
            typeObjet="TELEPHONE",
            nom="Samsung Galaxy",
            description="Samsung Galaxy S21",
            couleur="Noir",
            lieuPerte=self.localisation,
            datePerte=timezone.now(),
            est_perdu=True
        )
    
    def test_create_declaration_perdu(self):
        """Test création d'une déclaration d'objet perdu."""
        declaration = Declaration.objects.create(
            utilisateur=self.user,
            objet=self.objet,
            type_declaration="PERDU"
        )
        self.assertEqual(declaration.statut, "SOUMIS")
        self.assertEqual(declaration.type_declaration, "PERDU")
        self.assertIn("Perdu", str(declaration))


class ReclamationModelTest(TestCase):
    """Tests pour le modèle Reclamation."""
    
    def setUp(self):
        self.localisation = Localisation.objects.create(
            region="Maritime",
            prefecture="Golfe",
            quartier="Bè"
        )
        self.user = Utilisateur.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.objet = Objet.objects.create(
            typeObjet="BIJOU",
            nom="Montre Rolex",
            description="Montre de luxe",
            couleur="Or",
            lieuPerte=self.localisation,
            datePerte=timezone.now(),
            est_perdu=False,
            etat="PUBLIE"
        )
    
    def test_create_reclamation(self):
        """Test création d'une réclamation."""
        reclamation = Reclamation.objects.create(
            utilisateur=self.user,
            objet=self.objet,
            description_justificative="C'est ma montre, j'ai la facture"
        )
        self.assertEqual(reclamation.statut, "EN_VERIFICATION")
        self.assertIn(self.user.username, str(reclamation))


class NotificationModelTest(TestCase):
    """Tests pour le modèle Notification."""
    
    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            username="testuser",
            password="testpass123"
        )
    
    def test_create_notification(self):
        """Test création d'une notification."""
        notif = Notification.objects.create(
            utilisateur=self.user,
            titre="Nouvelle réclamation",
            message="Un objet que vous avez déclaré a été réclamé.",
            type_notification="SYSTEME"
        )
        self.assertFalse(notif.lu)
        self.assertIsNone(notif.date_lecture)
    
    def test_marquer_comme_lu(self):
        """Test marquage d'une notification comme lue."""
        notif = Notification.objects.create(
            utilisateur=self.user,
            titre="Test",
            message="Message de test",
            type_notification="SYSTEME"
        )
        notif.marquer_comme_lu()
        self.assertTrue(notif.lu)
        self.assertIsNotNone(notif.date_lecture)
