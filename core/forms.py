from django import forms
from .models import Signalement, Utilisateur, Region, Prefecture, CommentaireAnonyme, StructureLocale, Declaration
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.hashers import make_password


class DeclarationForm(forms.ModelForm):
    TYPE_CHOICES = [
        ('perdu', 'Objet perdu'),
        ('trouve', 'Objet trouvé'),
    ]
    
    type_declaration = forms.ChoiceField(
        label="Type de déclaration",
        choices=TYPE_CHOICES,
        initial='perdu',
        widget=forms.RadioSelect(attrs={
            'class': 'text-blue-600 focus:ring-blue-500'
        })
    )
    
    nom_objet = forms.CharField(
        label="Nom de l'objet perdu",
        max_length=200,
        help_text="Décrivez brièvement l'objet (ex: iPhone 13, portefeuille noir, clés de voiture)",
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
            'placeholder': 'Ex: iPhone 13 Pro bleu, portefeuille en cuir...'
        })
    )
    
    description = forms.CharField(
        label="Description détaillée",
        required=False,
        help_text="Ajoutez des détails qui pourraient aider à identifier votre objet (couleur, marque, signes distinctifs...)",
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
            'placeholder': 'Couleur, marque, modèle, signes particuliers, contenu (pour un sac)...'
        })
    )
    
    date_incident = forms.DateField(
        label="Date de perte",
        help_text="Quand avez-vous perdu cet objet?",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
        })
    )
    
    lieu_precis = forms.CharField(
        label="Lieu précis de perte",
        max_length=300,
        help_text="Décrivez le lieu exact où vous avez perdu l'objet",
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
            'placeholder': 'Ex: Marché de Kpalimé, Station-service Total Route de Lomé...'
        })
    )
    
    commentaire_declarant = forms.CharField(
        label="Commentaires supplémentaires",
        required=False,
        help_text="Toute information supplémentaire qui pourrait être utile",
        widget=forms.Textarea(attrs={
            'rows': 2,
            'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
            'placeholder': 'Circonstances de la perte, récompense offerte, etc.'
        })
    )
    
    region = forms.ModelChoiceField(
        queryset=Region.objects.all(),
        label="Région",
        required=False,
        empty_label="Sélectionnez une région",
        widget=forms.Select(attrs={
            'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
        })
    )
    
    prefecture = forms.ModelChoiceField(
        queryset=Prefecture.objects.none(),
        label="Préfecture", 
        required=False,
        empty_label="Choisissez une région d'abord",
        widget=forms.Select(attrs={
            'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
        })
    )
    
    structure_locale = forms.ModelChoiceField(
        queryset=StructureLocale.objects.none(),
        label="Structure locale",
        required=False,
        empty_label="Choisissez une préfecture d'abord",
        widget=forms.Select(attrs={
            'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
        })
    )
    
    photo_principale = forms.ImageField(
        label="Photo de l'objet",
        required=False,
        help_text="Une photo aide à identifier votre objet (formats acceptés: JPG, PNG, GIF - max 5MB)",
        widget=forms.ClearableFileInput(attrs={
            'class': 'hidden',
            'accept': 'image/*'
        })
    )
    
    # Champs de géolocalisation (remplis par JavaScript)
    latitude = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_latitude'})
    )
    longitude = forms.DecimalField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_longitude'})
    )

    class Meta:
        model = Declaration
        fields = ['type_declaration', 'nom_objet', 'description', 'date_incident', 'lieu_precis', 
                 'region', 'prefecture', 'structure_locale', 
                 'commentaire_declarant', 'photo_principale', 'latitude', 'longitude']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tous les champs sont requis sauf commentaire_declarant, photo_principale et champs de localisation
        for field_name, field in self.fields.items():
            if field_name not in ['commentaire_declarant', 'photo_principale', 'region', 'prefecture', 'structure_locale', 'latitude', 'longitude']:
                field.required = True
                
        # Initialiser les queryset pour les champs liés
        if 'region' in self.data:
            try:
                region_id = int(self.data.get('region'))
                self.fields['prefecture'].queryset = Prefecture.objects.filter(region_id=region_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            if self.instance.region:
                self.fields['prefecture'].queryset = self.instance.region.prefecture_set.all()
                
        if 'prefecture' in self.data:
            try:
                prefecture_id = int(self.data.get('prefecture'))
                self.fields['structure_locale'].queryset = StructureLocale.objects.filter(prefecture_id=prefecture_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            if self.instance.prefecture:
                self.fields['structure_locale'].queryset = self.instance.prefecture.structurelocale_set.all()


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


class CommentaireAnonymeForm(forms.ModelForm):
    """Formulaire pour les commentaires anonymes sur les signalements"""
    
    pseudo = forms.CharField(
        label="Votre pseudo (optionnel)",
        max_length=50,
        required=False,
        help_text="Vous pouvez rester anonyme ou indiquer un pseudo",
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-colors',
            'placeholder': 'Anonyme, Jean, Témoin123...'
        })
    )
    
    contenu = forms.CharField(
        label="Votre commentaire",
        help_text="Partagez des informations utiles : lieu où vous l'avez vu, détails supplémentaires, conseils...",
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-colors',
            'placeholder': 'Ex: "Je pense avoir vu cet objet près du marché ce matin..." ou "J\'ai des informations qui pourraient aider..."'
        })
    )
    
    email = forms.CharField(
        label="Contact (optionnel)",
        max_length=100,
        required=False,
        help_text="Email ou téléphone pour être contacté si nécessaire (ne sera pas affiché publiquement)",
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-colors',
            'placeholder': 'votre.email@exemple.com ou 22890123456'
        })
    )
    
    class Meta:
        model = CommentaireAnonyme
        fields = ['pseudo', 'contenu', 'email']
        
    def clean_contenu(self):
        contenu = self.cleaned_data.get('contenu')
        if len(contenu.strip()) < 10:
            raise forms.ValidationError("Le commentaire doit contenir au moins 10 caractères.")
        return contenu


class AgentForm(forms.ModelForm):
    """Formulaire pour créer ou modifier un agent"""
    
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe sécurisé'
        }),
        help_text="Le mot de passe doit contenir au moins 8 caractères"
    )
    
    confirm_password = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Répétez le mot de passe'
        })
    )
    
    class Meta:
        model = Utilisateur
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'telephone', 'region', 'prefecture', 'structure_locale'
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom d\'utilisateur unique'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@exemple.com'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prénom'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de famille'
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: +228 90 12 34 56'
            }),
            'region': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_region'
            }),
            'prefecture': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_prefecture'
            }),
            'structure_locale': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_structure_locale'
            })
        }
        labels = {
            'username': 'Nom d\'utilisateur',
            'email': 'Email professionnel',
            'first_name': 'Prénom',
            'last_name': 'Nom de famille',
            'telephone': 'Téléphone professionnel',
            'region': 'Région d\'affectation',
            'prefecture': 'Préfecture',
            'structure_locale': 'Structure locale'
        }
    
    def __init__(self, *args, **kwargs):
        admin_region = kwargs.pop('admin_region', None)
        super().__init__(*args, **kwargs)
        
        # Si un admin crée l'agent, limiter à sa région
        if admin_region:
            self.fields['region'].queryset = Region.objects.filter(id=admin_region.id)
            self.fields['prefecture'].queryset = Prefecture.objects.filter(region=admin_region)
        
        # Gestion dynamique des préfectures et structures
        if 'region' in self.data:
            try:
                region_id = int(self.data.get('region'))
                self.fields['prefecture'].queryset = Prefecture.objects.filter(region_id=region_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.region:
            self.fields['prefecture'].queryset = Prefecture.objects.filter(region=self.instance.region)
        else:
            self.fields['prefecture'].queryset = Prefecture.objects.none()
            
        if 'prefecture' in self.data:
            try:
                prefecture_id = int(self.data.get('prefecture'))
                self.fields['structure_locale'].queryset = StructureLocale.objects.filter(prefecture_id=prefecture_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.prefecture:
            self.fields['structure_locale'].queryset = StructureLocale.objects.filter(prefecture=self.instance.prefecture)
        else:
            self.fields['structure_locale'].queryset = StructureLocale.objects.none()
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if Utilisateur.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur existe déjà.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if Utilisateur.objects.filter(email=email).exists():
            raise forms.ValidationError("Cet email est déjà utilisé.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("Les mots de passe ne correspondent pas.")
            if len(password) < 8:
                raise forms.ValidationError("Le mot de passe doit contenir au moins 8 caractères.")
        
        return cleaned_data
    
    def save(self, commit=True):
        agent = super().save(commit=False)
        agent.role = 'agent'
        agent.actif = True
        agent.verifie = True
        
        # Hash du mot de passe
        if self.cleaned_data.get('password'):
            agent.password = make_password(self.cleaned_data['password'])
        
        if commit:
            agent.save()
        return agent


class DeclarationForm(forms.ModelForm):
    """Formulaire pour créer/éditer une déclaration"""
    
    class Meta:
        from .models import Declaration
        model = Declaration
        fields = [
            'type_declaration', 'nom_objet', 'description', 'categorie',
            'lieu_precis', 'date_incident', 'commentaire_declarant'
        ]
        widgets = {
            'type_declaration': forms.Select(attrs={'class': 'form-control'}),
            'nom_objet': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'lieu_precis': forms.TextInput(attrs={'class': 'form-control'}),
            'date_incident': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'commentaire_declarant': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ReclamationForm(forms.ModelForm):
    """Formulaire pour créer/gérer une réclamation"""
    
    class Meta:
        from .models import Reclamation
        model = Reclamation
        fields = [
            'justification', 'telephone_contact', 'email_contact', 'commentaire_reclamant'
        ]
        widgets = {
            'justification': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'telephone_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'email_contact': forms.EmailInput(attrs={'class': 'form-control'}),
            'commentaire_reclamant': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class PieceJustificativeValidationForm(forms.Form):
    """Formulaire pour valider des pièces justificatives"""
    
    ACTION_CHOICES = [
        ('valider', 'Valider'),
        ('rejeter', 'Rejeter'),
    ]
    
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.RadioSelect)
    commentaire = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Commentaire optionnel...'
        })
    )


# ===== FORMULAIRES POUR LA MESSAGERIE TEMPS RÉEL =====

class MessageChatForm(forms.Form):
    """Formulaire simple pour envoyer un message de chat"""
    contenu = forms.CharField(
        max_length=2000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Tapez votre message...'
        })
    )


class FileUploadForm(forms.Form):
    """Formulaire pour upload de fichiers dans le chat"""
    fichier = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,.pdf,.doc,.docx,.txt,.zip,.rar'
        })
    )

