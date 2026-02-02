from django import forms
from .models import Payment

class PaymentForm(forms.ModelForm):
    """Formulaire pour le paiement"""
    class Meta:
        model = Payment
        fields = ['payment_method', 'phone_number', 'operator']
        widgets = {
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+226XXXXXXXX'}),
            'operator': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_method'].label = "Méthode de paiement"
        self.fields['phone_number'].label = "Numéro de téléphone"
        self.fields['operator'].label = "Opérateur"
        
        # Rendre les champs conditionnels
        self.fields['phone_number'].required = False
        self.fields['operator'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        phone_number = cleaned_data.get('phone_number')
        operator = cleaned_data.get('operator')
        
        if payment_method == 'mobile_money':
            if not phone_number:
                raise forms.ValidationError("Le numéro de téléphone est requis pour Mobile Money.")
            if not operator:
                raise forms.ValidationError("L'opérateur est requis pour Mobile Money.")
        
        return cleaned_data 