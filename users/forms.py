from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import User, LivreurProfile, EntrepriseProfile
from location.models import Geofence
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class UserRegistrationForm(UserCreationForm):
    """Formulaire d'inscription utilisateur"""
    user_type = forms.ChoiceField(
        choices=User.USER_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'sr-only'}),
        label="Type de compte",
        required=True
    )
    phone_number = forms.CharField(
        max_length=17,
        required=False,
        help_text="Format: +226XXXXXXXX"
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'user_type', 'phone_number', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personnalisation des labels
        self.fields['username'].label = "Nom d'utilisateur"
        self.fields['email'].label = "Adresse email"
        self.fields['first_name'].label = "Prénom"
        self.fields['last_name'].label = "Nom"
        self.fields['phone_number'].label = "Numéro de téléphone"
        self.fields['password1'].label = "Mot de passe"
        self.fields['password2'].label = "Confirmation du mot de passe"
        
        # Ajout des classes CSS pour les champs avec styles modernes
        form_input_classes = 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all duration-200 bg-white/50 backdrop-blur-sm placeholder-gray-400'
        
        self.fields['username'].widget.attrs.update({
            'class': form_input_classes,
            'placeholder': 'Votre nom d\'utilisateur'
        })
        self.fields['email'].widget.attrs.update({
            'class': form_input_classes,
            'placeholder': 'votre.email@exemple.com'
        })
        self.fields['first_name'].widget.attrs.update({
            'class': form_input_classes,
            'placeholder': 'Votre prénom'
        })
        self.fields['last_name'].widget.attrs.update({
            'class': form_input_classes,
            'placeholder': 'Votre nom'
        })
        self.fields['phone_number'].widget.attrs.update({
            'class': form_input_classes,
            'placeholder': '+226XXXXXXXX'
        })
        self.fields['password1'].widget.attrs.update({
            'class': form_input_classes,
            'placeholder': 'Votre mot de passe',
            'id': 'password1'
        })
        self.fields['password2'].widget.attrs.update({
            'class': form_input_classes,
            'placeholder': 'Confirmez votre mot de passe',
            'id': 'password2'
        })
        
        # Personnalisation des help_text
        self.fields['username'].help_text = "150 caractères maximum. Lettres, chiffres et @/./+/-/_ uniquement."
        self.fields['email'].help_text = "Votre adresse email sera utilisée pour les notifications."
        self.fields['phone_number'].help_text = "Format: +226XXXXXXXX"
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user_type = self.cleaned_data.get('user_type')
        
        # Debug: vérifier que le type d'utilisateur est bien récupéré
        logger.info(f"Type d'utilisateur sélectionné: {user_type}")
        
        if not user_type:
            raise ValueError("Le type d'utilisateur doit être sélectionné")
        
        user.user_type = user_type
        user.phone_number = self.cleaned_data.get('phone_number', '')
        
        if commit:
            user.save()
            logger.info(f"Utilisateur sauvegardé avec le type: {user.user_type}")
            
            # Créer le profil spécifique selon le type d'utilisateur
            if user.user_type == 'livreur':
                LivreurProfile.objects.create(user=user)
                logger.info("Profil livreur créé")
            elif user.user_type == 'entreprise':
                EntrepriseProfile.objects.create(user=user)
                logger.info("Profil entreprise créé")
            # Les types 'client' et 'admin' n'ont pas de profil spécifique
        
        return user

class LivreurProfileForm(forms.ModelForm):
    """Formulaire pour le profil livreur"""
    service_zones = forms.ModelMultipleChoiceField(
        queryset=Geofence.objects.filter(geofence_type='service_zone'),
        widget=forms.CheckboxSelectMultiple,
        label="Zones de service",
        required=False
    )

    class Meta:
        model = LivreurProfile
        fields = [
            'vehicle_type', 'vehicle_plate', 'license_number', 
            'experience_years', 'current_location', 'is_available', 'service_zones'
        ]
        widgets = {
            'vehicle_type': forms.Select(attrs={'class': 'form-control'}),
            'vehicle_plate': forms.TextInput(attrs={'class': 'form-control'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control'}),
            'current_location': forms.TextInput(attrs={'class': 'form-control'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personnalisation des labels
        self.fields['vehicle_type'].label = "Type de véhicule"
        self.fields['vehicle_plate'].label = "Plaque d'immatriculation"
        self.fields['license_number'].label = "Numéro de permis"
        self.fields['experience_years'].label = "Années d'expérience"
        self.fields['current_location'].label = "Localisation actuelle"
        self.fields['is_available'].label = "Disponible pour les missions"

class EntrepriseProfileForm(forms.ModelForm):
    """Formulaire pour le profil entreprise"""
    class Meta:
        model = EntrepriseProfile
        fields = [
            'company_name', 'business_type', 'address', 
            'tax_id', 'business_license'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_type': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control'}),
            'business_license': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personnalisation des labels
        self.fields['company_name'].label = "Nom de l'entreprise"
        self.fields['business_type'].label = "Type d'activité"
        self.fields['address'].label = "Adresse"
        self.fields['tax_id'].label = "Numéro fiscal"
        self.fields['business_license'].label = "Numéro de licence commerciale"

class UserProfileForm(forms.ModelForm):
    """Formulaire pour les informations de base de l'utilisateur"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personnalisation des labels
        self.fields['first_name'].label = "Prénom"
        self.fields['last_name'].label = "Nom"
        self.fields['email'].label = "Adresse email"
        self.fields['phone_number'].label = "Numéro de téléphone" 