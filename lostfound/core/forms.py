from django import forms
from .models import Signalement
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Utilisateur
from django.shortcuts import redirect
from django.contrib import messages
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()

# class AdminForm(forms.ModelForm):
#     password = forms.CharField(widget=forms.PasswordInput, required=False, help_text="Laisser vide pour mot de passe par défaut.")

#     class Meta:
#         model = User
#         fields = ['username', 'email', 'zone', 'password']

from django.contrib.auth.forms import UserCreationForm
from core.models import Utilisateur, Region, Prefecture

# class AdminCreationForm(UserCreationForm):
class AdminForm(UserCreationForm):
    region = forms.ModelChoiceField(queryset=Region.objects.all(), required=True)
    prefecture = forms.ModelChoiceField(queryset=Prefecture.objects.none(), required=True)

    class Meta:
        model = Utilisateur
        # Seuls les champs existants dans le modèle
        fields = ('username', 'email', 'telephone', 'role', 'region', 'prefecture')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Dynamique : remplir les préfectures selon la région
        if 'region' in self.data:
            try:
                region_id = int(self.data.get('region'))
                self.fields['prefecture'].queryset = Prefecture.objects.filter(region_id=region_id)
            except (ValueError, TypeError):
                pass
        else:
            self.fields['prefecture'].queryset = Prefecture.objects.none()
def role_required(roles):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Veuillez vous connecter.")
                return redirect('login')
            if request.user.role not in roles:
                messages.error(request, "Accès refusé.")
                return redirect('index')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator



# class SignalementForm(forms.ModelForm):
#     objet = forms.CharField(label="Nom de l’objet", max_length=100)

#     class Meta:
#         model = Signalement
#         fields = ['objet', 'lieu', 'commentaire', 'photo', 'statut']
#         widgets = {
#             'objet': forms.TextInput(attrs={
#                 'class': 'w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none'
#             }),
#             'lieu': forms.TextInput(attrs={
#                 'class': 'w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none'
#             }),
#             'commentaire': forms.Textarea(attrs={
#                 'rows': 4,
#                 'class': 'w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none'
#             }),
#             'photo': forms.ClearableFileInput(attrs={
#                 'class': 'w-full border border-gray-300 rounded-lg p-2 bg-gray-50'
#             }),
#             'statut': forms.Select(attrs={
#                 'class': 'w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none'
#             }),
#         }


class SignalementForm(forms.ModelForm):
    objet = forms.CharField(
        label="Nom de l’objet",
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none'
        })
    )

    class Meta:
        model = Signalement
        # on exclut 'objet' ici pour éviter le conflit avec le ForeignKey
        fields = ['lieu', 'commentaire', 'photo', 'statut']
        widgets = {
            'lieu': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none'
            }),
            'commentaire': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none'
            }),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg p-2 bg-gray-50'
            }),
            'statut': forms.Select(attrs={
                'class': 'w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none'
            }),
        }
        

class InscriptionForm(UserCreationForm):
    telephone = forms.CharField(required=False)
    role = forms.ChoiceField(choices=Utilisateur.ROLE_CHOICES)

    class Meta:
        model = Utilisateur
        fields = ['username', 'email', 'telephone', 'role', 'password1', 'password2']


class ConnexionForm(AuthenticationForm):
    username = forms.CharField(label="Nom d'utilisateur")
    password = forms.CharField(widget=forms.PasswordInput)

    
class SearchForm(forms.Form):
    nom = forms.CharField(required=False, label="Qu'avez-vous perdu ?")
    lieu = forms.CharField(required=False)
    date_perte = forms.DateField(required=False, widget=forms.DateInput(attrs={'type':'date'}))


# ============================================================================
# Formulaires pour les nouveaux modèles
# ============================================================================
from .models import Localisation, Objet, Declaration, Reclamation


class LocalisationForm(forms.ModelForm):
    """Formulaire pour créer/modifier une localisation."""
    class Meta:
        model = Localisation
        fields = ['region', 'prefecture', 'quartier', 'commissariat', 'latitude', 'longitude']
        widgets = {
            'region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Maritime'}),
            'prefecture': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Golfe'}),
            'quartier': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Bè'}),
            'commissariat': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optionnel'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'Ex: 6.1375'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': 'Ex: 1.2123'}),
        }


class ObjetForm(forms.ModelForm):
    """Formulaire pour déclarer un objet perdu ou trouvé."""
    class Meta:
        model = Objet
        fields = [
            'typeObjet', 'nom', 'description', 'couleur', 'marque', 'photo',
            'lieuPerte', 'datePerte', 'est_perdu'
        ]
        widgets = {
            'typeObjet': forms.Select(attrs={'class': 'form-control'}),
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: iPhone 13 Pro'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Décrivez l\'objet en détail...'}),
            'couleur': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Bleu'}),
            'marque': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Apple'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'lieuPerte': forms.Select(attrs={'class': 'form-control'}),
            'datePerte': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'est_perdu': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'est_perdu': 'Objet perdu (cochez si perdu, décochez si trouvé)',
        }


class ObjetQuickForm(forms.ModelForm):
    """Formulaire rapide pour déclarer un objet (sans localisation obligatoire)."""
    class Meta:
        model = Objet
        fields = ['typeObjet', 'nom', 'description', 'couleur', 'photo', 'est_perdu']
        widgets = {
            'typeObjet': forms.Select(attrs={'class': 'form-control'}),
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'couleur': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'est_perdu': forms.Select(choices=[(True, 'Perdu'), (False, 'Trouvé')], attrs={'class': 'form-control'}),
        }


class DeclarationForm(forms.ModelForm):
    """Formulaire pour créer une déclaration."""
    class Meta:
        model = Declaration
        fields = ['type_declaration']
        widgets = {
            'type_declaration': forms.Select(attrs={'class': 'form-control'}),
        }


class ReclamationForm(forms.ModelForm):
    """Formulaire pour réclamer un objet trouvé."""
    class Meta:
        model = Reclamation
        fields = ['justificatif', 'description_justificative']
        widgets = {
            'justificatif': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,application/pdf'}),
            'description_justificative': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Expliquez pourquoi cet objet vous appartient. Fournissez le maximum de détails...'
            }),
        }
        labels = {
            'justificatif': 'Document justificatif (photo, facture, etc.)',
            'description_justificative': 'Description justificative',
        }


class ValidationDeclarationForm(forms.ModelForm):
    """Formulaire pour qu'un agent valide/rejette une déclaration."""
    class Meta:
        model = Declaration
        fields = ['statut', 'commentaire_agent']
        widgets = {
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'commentaire_agent': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ValidationReclamationForm(forms.ModelForm):
    """Formulaire pour qu'un agent valide/rejette une réclamation."""
    class Meta:
        model = Reclamation
        fields = ['statut', 'commentaire_verification']
        widgets = {
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'commentaire_verification': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ObjetSearchForm(forms.Form):
    """Formulaire de recherche avancée pour les objets."""
    typeObjet = forms.ChoiceField(
        choices=[('', 'Tous les types')] + list(Objet.TYPE_OBJET_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    nom = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom de l\'objet'})
    )
    couleur = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Couleur'})
    )
    est_perdu = forms.ChoiceField(
        choices=[('', 'Tous'), ('True', 'Perdus'), ('False', 'Trouvés')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    etat = forms.ChoiceField(
        choices=[('', 'Tous les états')] + list(Objet.ETAT_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )