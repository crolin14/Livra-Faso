from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class Rating(models.Model):
    """Évaluation d'un utilisateur par un autre"""
    RATING_CHOICES = [
        (1, '1 - Très mauvais'),
        (2, '2 - Mauvais'),
        (3, '3 - Moyen'),
        (4, '4 - Bon'),
        (5, '5 - Excellent'),
    ]
    
    rater = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ratings_given')
    rated_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ratings_received')
    rating = models.IntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Contexte de l'évaluation
    mission = models.ForeignKey('missions.Mission', on_delete=models.CASCADE, null=True, blank=True, related_name='ratings')
    
    class Meta:
        verbose_name = "Évaluation"
        verbose_name_plural = "Évaluations"
        unique_together = ['rater', 'rated_user', 'mission']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Évaluation de {self.rated_user.username} par {self.rater.username}: {self.rating}/5"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Mettre à jour la note moyenne de l'utilisateur évalué
        self.update_user_rating()
    
    def update_user_rating(self):
        """Mettre à jour la note moyenne de l'utilisateur évalué"""
        avg_rating = Rating.objects.filter(rated_user=self.rated_user).aggregate(
            avg=models.Avg('rating')
        )['avg'] or 0
        
        if self.rated_user.user_type == 'livreur':
            if hasattr(self.rated_user, 'livreur_profile'):
                self.rated_user.livreur_profile.rating = round(avg_rating, 2)
                self.rated_user.livreur_profile.save()
        elif self.rated_user.user_type == 'entreprise':
            if hasattr(self.rated_user, 'entreprise_profile'):
                self.rated_user.entreprise_profile.rating = round(avg_rating, 2)
                self.rated_user.entreprise_profile.save()

class RatingCategory(models.Model):
    """Catégories d'évaluation (ponctualité, service, etc.)"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Catégorie d'Évaluation"
        verbose_name_plural = "Catégories d'Évaluation"
    
    def __str__(self):
        return self.name

class CategoryRating(models.Model):
    """Évaluation par catégorie"""
    rating = models.ForeignKey(Rating, on_delete=models.CASCADE, related_name='category_ratings')
    category = models.ForeignKey(RatingCategory, on_delete=models.CASCADE)
    score = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    
    class Meta:
        verbose_name = "Évaluation par Catégorie"
        verbose_name_plural = "Évaluations par Catégorie"
        unique_together = ['rating', 'category']
    
    def __str__(self):
        return f"{self.category.name}: {self.score}/5"

class RatingResponse(models.Model):
    """Réponse à une évaluation"""
    rating = models.OneToOneField(Rating, on_delete=models.CASCADE, related_name='response')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Réponse à l'Évaluation"
        verbose_name_plural = "Réponses aux Évaluations"
    
    def __str__(self):
        return f"Réponse à l'évaluation #{self.rating.id}"
