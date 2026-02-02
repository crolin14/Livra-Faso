from django import forms
from .models import Rating, RatingCategory, CategoryRating

class RatingForm(forms.ModelForm):
    """Formulaire pour évaluer un utilisateur"""
    class Meta:
        model = Rating
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating'].label = "Note"
        self.fields['comment'].label = "Commentaire (optionnel)"
        
        # Personnaliser les choix de note
        self.fields['rating'].choices = [
            (5, '5 - Excellent'),
            (4, '4 - Bon'),
            (3, '3 - Moyen'),
            (2, '2 - Mauvais'),
            (1, '1 - Très mauvais'),
        ]

class CategoryRatingForm(forms.ModelForm):
    """Formulaire pour évaluer par catégorie"""
    class Meta:
        model = CategoryRating
        fields = ['category', 'score']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'score': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].label = "Catégorie"
        self.fields['score'].label = "Note"
        
        # Personnaliser les choix de note
        self.fields['score'].choices = [
            (5, '5 - Excellent'),
            (4, '4 - Bon'),
            (3, '3 - Moyen'),
            (2, '2 - Mauvais'),
            (1, '1 - Très mauvais'),
        ] 