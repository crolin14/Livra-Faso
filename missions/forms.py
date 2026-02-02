from django import forms
from .models import Mission, MissionDocument

class MissionStep1Form(forms.ModelForm):
    class Meta:
        model = Mission
        fields = ['pickup_address', 'delivery_address']
        widgets = {
            'pickup_address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors duration-200 resize-none',
                'rows': 3,
                'placeholder': 'Adresse complète de ramassage...'
            }),
            'delivery_address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors duration-200 resize-none',
                'rows': 3,
                'placeholder': 'Adresse complète de livraison...'
            }),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pickup_address'].label = "Adresse de ramassage"
        self.fields['delivery_address'].label = "Adresse de livraison"

class MissionStep2Form(forms.ModelForm):
    class Meta:
        model = Mission
        fields = ['title', 'description', 'package_type', 'package_weight', 'package_dimensions', 'is_fragile', 'requires_signature']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors duration-200',
                'placeholder': 'Ex: Livraison de documents urgents'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors duration-200 resize-none',
                'rows': 4,
                'placeholder': 'Décrivez le contenu et les instructions spéciales...'
            }),
            'package_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors duration-200 bg-white'
            }),
            'package_weight': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors duration-200',
                'placeholder': '0.5',
                'step': '0.1',
                'min': '0'
            }),
            'package_dimensions': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors duration-200',
                'placeholder': 'Ex: 30x20x10 cm'
            }),
            'is_fragile': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-primary-600 border-gray-300 rounded focus:ring-primary-500 focus:ring-2'
            }),
            'requires_signature': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-primary-600 border-gray-300 rounded focus:ring-primary-500 focus:ring-2'
            }),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].label = "Titre de la mission"
        self.fields['description'].label = "Description"
        self.fields['package_type'].label = "Type de colis"
        self.fields['package_weight'].label = "Poids du colis (kg)"
        self.fields['package_dimensions'].label = "Dimensions du colis"
        self.fields['is_fragile'].label = "Colis fragile"
        self.fields['requires_signature'].label = "Signature requise"

class MissionStep3Form(forms.ModelForm):
    class Meta:
        model = Mission
        fields = ['priority', 'estimated_delivery_time']
        widgets = {
            'priority': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors duration-200 bg-white'
            }),
            'estimated_delivery_time': forms.DateTimeInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors duration-200',
                'type': 'datetime-local'
            }),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['priority'].label = "Priorité"
        self.fields['estimated_delivery_time'].label = "Heure de livraison estimée"

class MissionStep4Form(forms.ModelForm):
    class Meta:
        model = Mission
        fields = ['price']
        widgets = {
            'price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors duration-200',
                'placeholder': '5000',
                'min': '0',
                'step': '100'
            }),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['price'].label = "Prix (FCFA)"

class MissionForm(forms.ModelForm):
    """Formulaire pour créer/modifier une mission"""
    class Meta:
        model = Mission
        fields = [
            'title', 'description', 'priority', 'pickup_address', 
            'delivery_address', 'pickup_instructions', 'delivery_instructions',
            'package_type', 'package_weight', 'package_dimensions', 'is_fragile', 
            'requires_signature', 'price', 'estimated_delivery_time', 'estimated_price'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'pickup_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'delivery_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'pickup_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'delivery_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'package_type': forms.Select(attrs={'class': 'form-control'}),
            'package_weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'package_dimensions': forms.TextInput(attrs={'class': 'form-control'}),
            'is_fragile': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_signature': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'estimated_delivery_time': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personnalisation des labels
        self.fields['title'].label = "Titre de la mission"
        self.fields['description'].label = "Description"
        self.fields['priority'].label = "Priorité"
        self.fields['pickup_address'].label = "Adresse de ramassage"
        self.fields['delivery_address'].label = "Adresse de livraison"
        self.fields['pickup_instructions'].label = "Instructions de ramassage"
        self.fields['delivery_instructions'].label = "Instructions de livraison"
        self.fields['package_type'].label = "Type de colis"
        self.fields['package_weight'].label = "Poids du colis (kg)"
        self.fields['package_dimensions'].label = "Dimensions du colis"
        self.fields['is_fragile'].label = "Colis fragile"
        self.fields['requires_signature'].label = "Signature requise"
        self.fields['price'].label = "Prix (FCFA)"
        self.fields['estimated_delivery_time'].label = "Heure de livraison estimée"

class MissionStatusForm(forms.Form):
    """Formulaire pour mettre à jour le statut d'une mission"""
    status = forms.ChoiceField(
        choices=Mission.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Nouveau statut"
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label="Description (optionnel)"
    )

class MissionDocumentForm(forms.ModelForm):
    """Formulaire pour ajouter des documents à une mission"""
    class Meta:
        model = MissionDocument
        fields = ['document_type', 'file', 'description']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['document_type'].label = "Type de document"
        self.fields['file'].label = "Fichier"
        self.fields['description'].label = "Description" 