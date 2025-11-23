from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import Signalement, Utilisateur, Region, Prefecture

User = get_user_model()

class AdminForm(UserCreationForm):
    region = forms.ModelChoiceField(queryset=Region.objects.all(), required=True)
    prefecture = forms.ModelChoiceField(queryset=Prefecture.objects.none(), required=True)

    class Meta:
        model = Utilisateur
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

class SignalementForm(forms.ModelForm):
    objet = forms.CharField(
        label="Nom de l'objet",
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
