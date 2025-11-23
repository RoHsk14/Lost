from django import forms
from .models import Signalement, Utilisateur, Region, Prefecture
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm


class SignalementForm(forms.ModelForm):
    objet = forms.CharField(
        label="Nom de l'objet perdu",
        max_length=100,
        help_text="Décrivez brièvement l'objet (ex: iPhone 13, portefeuille noir, clés de voiture)",
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
            'placeholder': 'Ex: iPhone 13 Pro bleu, portefeuille en cuir...'
        })
    )
    
    description_objet = forms.CharField(
        label="Description détaillée",
        required=False,
        help_text="Ajoutez des détails qui pourraient aider à identifier votre objet (couleur, marque, signes distinctifs...)",
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
            'placeholder': 'Couleur, marque, modèle, signes particuliers, contenu (pour un sac)...'
        })
    )
    
    categorie_objet = forms.ChoiceField(
        label="Catégorie de l'objet",
        choices=[
            ('', 'Sélectionnez une catégorie'),
            ('electronique', '📱 Électronique (téléphone, tablette, ordinateur...)'),
            ('accessoire', '👜 Accessoires (sac, portefeuille, bijoux...)'),
            ('cles', '🔑 Clés et porte-clés'),
            ('vetement', '👕 Vêtements et chaussures'),
            ('document', '📄 Documents (papiers, cartes, permis...)'),
            ('sport', '⚽ Articles de sport'),
            ('autre', '📦 Autre')
        ],
        widget=forms.Select(attrs={
            'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
        })
    )
    
    date_perte = forms.DateField(
        label="Date de la perte",
        help_text="Quand avez-vous perdu cet objet ? (approximativement)",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
        })
    )

    class Meta:
        model = Signalement
        fields = ['lieu', 'commentaire', 'photo', 'statut']
        labels = {
            'lieu': 'Lieu de la perte',
            'commentaire': 'Commentaires et circonstances',
            'photo': 'Photo de l\'objet (si vous en avez une)',
            'statut': 'Type de signalement'
        }
        help_texts = {
            'lieu': 'Où avez-vous perdu cet objet ? Soyez le plus précis possible.',
            'commentaire': 'Décrivez les circonstances de la perte, cela peut aider.',
            'photo': 'Une photo peut grandement aider à identifier votre objet.',
            'statut': 'Avez-vous perdu ou trouvé cet objet ?'
        }
        widgets = {
            'lieu': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'placeholder': 'Ex: Marché du Grand Lomé, Université de Lomé, Bus SOTRAM ligne 2...'
            }),
            'commentaire': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'placeholder': 'Décrivez les circonstances: heure, activité que vous faisiez, personnes présentes...'
            }),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg p-3 bg-gray-50 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
                'accept': 'image/*'
            }),
            'statut': forms.Select(attrs={
                'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
            }),
        }

    def save(self, commit=True):
        signalement = super().save(commit=False)
        
        # Créer ou récupérer l'objet
        from .models import Objet
        objet_nom = self.cleaned_data.get('objet')
        description = self.cleaned_data.get('description_objet', '')
        categorie = self.cleaned_data.get('categorie_objet', '')
        date_perte = self.cleaned_data.get('date_perte')
        
        objet, created = Objet.objects.get_or_create(
            nom=objet_nom,
            defaults={
                'description': description,
                'categorie': categorie,
                'date_trouve': date_perte,  # Utiliser comme date de référence
            }
        )
        
        # Si l'objet existe déjà, mettre à jour sa description si elle est vide
        if not created and not objet.description and description:
            objet.description = description
            objet.save()
            
        signalement.objet = objet
        
        if commit:
            signalement.save()
        return signalement


class AdminForm(UserCreationForm):
    region = forms.ModelChoiceField(queryset=Region.objects.all(), required=True)
    prefecture = forms.ModelChoiceField(queryset=Prefecture.objects.none(), required=True)

    class Meta:
        model = Utilisateur
        fields = ('username', 'email', 'telephone', 'role', 'region', 'prefecture')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'region' in self.data:
            try:
                region_id = int(self.data.get('region'))
                self.fields['prefecture'].queryset = Prefecture.objects.filter(region_id=region_id)
            except (ValueError, TypeError):
                pass
        else:
            self.fields['prefecture'].queryset = Prefecture.objects.none()


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
