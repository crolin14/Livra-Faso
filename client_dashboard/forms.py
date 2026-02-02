from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from django.forms import inlineformset_factory
from django.utils import timezone
from datetime import timedelta
from .models import (
    ClientProfile, ListeCourses, ArticleCourses, 
    MoyenPaiement, AdresseFavorite,
    MissionCourses, EtapeMission, ArticleCourseMission, ValidationEtape
)


class ClientProfileForm(forms.ModelForm):
    class Meta:
        model = ClientProfile
        fields = ['default_payment_method']
        widgets = {
            'default_payment_method': forms.Select(attrs={
                'class': 'form-select'
            })
        }


class ListeCoursesForm(forms.ModelForm):
    class Meta:
        model = ListeCourses
        fields = ['nom', 'description', 'budget_max', 'is_favorite', 'is_template']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: Courses du weekend'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Description optionnelle de votre liste'
            }),
            'budget_max': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Budget maximum en FCFA',
                'min': '0',
                'step': '100'
            }),
            'is_favorite': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'is_template': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['budget_max'].validators = [MinValueValidator(0)]


class ArticleCoursesForm(forms.ModelForm):
    class Meta:
        model = ArticleCourses
        fields = ['nom', 'quantite', 'prix_estime', 'photo', 'notes']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: Riz parfumé 5kg'
            }),
            'quantite': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: 2 kg, 3 pièces'
            }),
            'prix_estime': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Prix estimé en FCFA',
                'min': '0',
                'step': '25'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'form-file-input',
                'accept': 'image/*'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Notes spéciales pour le livreur'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['prix_estime'].validators = [MinValueValidator(0)]
    
    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            # Vérifier la taille du fichier (max 5MB)
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError("L'image ne doit pas dépasser 5MB")
            
            # Vérifier le type de fichier
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if photo.content_type not in allowed_types:
                raise forms.ValidationError("Format d'image non supporté. Utilisez JPG, PNG, GIF ou WebP")
        
        return photo


class MoyenPaiementForm(forms.ModelForm):
    class Meta:
        model = MoyenPaiement
        fields = ['type_paiement', 'nom_affiche', 'numero_masque', 'is_default']
        widgets = {
            'type_paiement': forms.Select(attrs={
                'class': 'form-select'
            }),
            'nom_affiche': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: Mon Orange Money'
            }),
            'numero_masque': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Numéro masqué (ex: ****3456)'
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            })
        }
    
    def clean_numero_masque(self):
        numero = self.cleaned_data.get('numero_masque')
        type_paiement = self.cleaned_data.get('type_paiement')
        
        if type_paiement in ['orange_money', 'moov_money', 'wave']:
            # Validation basique du numéro masqué
            if not numero or len(numero) < 4:
                raise forms.ValidationError("Numéro masqué invalide")
        
        return numero


class AdresseFavoriteForm(forms.ModelForm):
    class Meta:
        model = AdresseFavorite
        fields = ['nom', 'adresse_complete', 'type_adresse', 'latitude', 'longitude']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: Maison, Bureau, Chez maman'
            }),
            'adresse': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Adresse complète avec points de repère'
            }),
            'type_adresse': forms.Select(attrs={
                'class': 'form-select'
            }),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput()
        }


class RechercheArticleForm(forms.Form):
    """Formulaire de recherche d'articles dans les listes"""
    query = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Rechercher un article...',
            'autocomplete': 'off'
        })
    )
    
    prix_min = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Prix min'
        })
    )
    
    prix_max = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Prix max'
        })
    )
    
    est_trouve = forms.ChoiceField(
        choices=[
            ('', 'Tous les articles'),
            ('true', 'Articles trouvés'),
            ('false', 'Articles non trouvés')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


class ImportListeForm(forms.Form):
    """Formulaire pour importer une liste depuis un fichier CSV"""
    fichier_csv = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-file-input',
            'accept': '.csv'
        }),
        help_text="Format CSV: nom,description,quantite,prix_estime"
    )
    
    def clean_fichier_csv(self):
        fichier = self.cleaned_data.get('fichier_csv')
        if fichier:
            if not fichier.name.endswith('.csv'):
                raise forms.ValidationError("Seuls les fichiers CSV sont acceptés")
            
            if fichier.size > 1024 * 1024:  # 1MB max
                raise forms.ValidationError("Le fichier ne doit pas dépasser 1MB")
        
        return fichier


class PartageListeForm(forms.Form):
    """Formulaire pour partager une liste de courses"""
    email_destinataire = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'email@exemple.com'
        })
    )
    
    message_personnel = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 3,
            'placeholder': 'Message personnel (optionnel)'
        })
    )
    
    inclure_prix = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        }),
        label="Inclure les prix estimés"
    )


class FiltreTransactionForm(forms.Form):
    """Formulaire de filtrage des transactions"""
    TYPE_CHOICES = [
        ('', 'Tous les types'),
        ('recharge', 'Recharges'),
        ('paiement', 'Paiements'),
        ('remboursement', 'Remboursements'),
        ('bonus', 'Bonus')
    ]
    
    STATUT_CHOICES = [
        ('', 'Tous les statuts'),
        ('en_attente', 'En attente'),
        ('reussie', 'Réussies'),
        ('echouee', 'Échouées'),
        ('annulee', 'Annulées')
    ]
    
    type_transaction = forms.ChoiceField(
        choices=TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    statut = forms.ChoiceField(
        choices=STATUT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_debut = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        })
    )
    
    date_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        })
    )
    
    montant_min = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Montant min'
        })
    )
    
    montant_max = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Montant max'
        })
    )


# ============================================
# FORMULAIRES MODULE "FAIRE MES COURSES"
# ============================================

class MissionCoursesForm(forms.ModelForm):
    """Formulaire pour créer une mission de courses"""
    
    class Meta:
        model = MissionCourses
        fields = ['titre', 'description', 'delai_type', 'heure_limite', 'duree_max_minutes']
        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: Courses du weekend'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Description de votre mission de courses'
            }),
            'delai_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'heure_limite': forms.DateTimeInput(attrs={
                'class': 'form-input',
                'type': 'datetime-local'
            }),
            'duree_max_minutes': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Durée en minutes (ex: 120 pour 2h)',
                'min': '30',
                'step': '15'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        delai_type = cleaned_data.get('delai_type')
        heure_limite = cleaned_data.get('heure_limite')
        duree_max_minutes = cleaned_data.get('duree_max_minutes')
        
        if delai_type == 'heure_limite':
            if not heure_limite:
                raise forms.ValidationError("Vous devez spécifier une heure limite")
            if heure_limite <= timezone.now():
                raise forms.ValidationError("L'heure limite doit être dans le futur")
        elif delai_type == 'duree_max_minutes':
            if not duree_max_minutes or duree_max_minutes < 30:
                raise forms.ValidationError("La durée minimum est de 30 minutes")
        
        return cleaned_data


class EtapeMissionForm(forms.ModelForm):
    """Formulaire pour créer une étape de mission"""
    
    class Meta:
        model = EtapeMission
        fields = ['numero_ordre', 'type_etape', 'adresse', 'instructions', 'action_requise', 'montant_requis']
        widgets = {
            'numero_ordre': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'readonly': True
            }),
            'type_etape': forms.Select(attrs={
                'class': 'form-select'
            }),
            'adresse': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Adresse complète avec points de repère'
            }),
            'instructions': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Instructions spécifiques pour cette étape'
            }),
            'action_requise': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Ex: Récupérer 15 000 FCFA, Acheter les produits frais'
            }),
            'montant_requis': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Montant en FCFA (si applicable)',
                'min': '0',
                'step': '100'
            }),
        }


class ArticleCourseMissionForm(forms.ModelForm):
    """Formulaire pour ajouter un article à une étape"""
    
    class Meta:
        model = ArticleCourseMission
        fields = ['nom', 'quantite', 'prix_estime', 'prix_max_accepte', 'substitution_autorisee', 'commentaire']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: Tomates'
            }),
            'quantite': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ex: 2 kg, 3 pièces'
            }),
            'prix_estime': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Prix estimé (facultatif)',
                'min': '0',
                'step': '50'
            }),
            'prix_max_accepte': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Prix maximum accepté',
                'min': '0',
                'step': '50'
            }),
            'substitution_autorisee': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'commentaire': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Commentaire libre (marque, qualité, etc.)'
            }),
        }


# Formset pour gérer plusieurs articles en une fois
ArticleCourseMissionFormSet = inlineformset_factory(
    EtapeMission,
    ArticleCourseMission,
    form=ArticleCourseMissionForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False
)


class CalculPrixForm(forms.Form):
    """Formulaire pour calculer le prix d'une mission"""
    adresses = forms.CharField(
        widget=forms.HiddenInput(),
        help_text="Liste JSON des adresses"
    )
    duree_max_minutes = forms.IntegerField(
        required=False,
        min_value=30,
        widget=forms.HiddenInput()
    )
    heure_limite = forms.DateTimeField(
        required=False,
        widget=forms.HiddenInput()
    )
