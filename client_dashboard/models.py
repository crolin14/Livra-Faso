from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
import json

class ClientProfile(models.Model):
    """Profil spécifique pour les clients"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='client_profile')
    preferred_addresses = models.JSONField(default=dict, help_text="Adresses favorites du client")
    default_payment_method = models.CharField(max_length=50, choices=[
        ('orange_money', 'Orange Money'),
        ('moov_money', 'Moov Money'),
        ('wave', 'Wave'),
        ('carte_bancaire', 'Carte Bancaire'),
        ('especes', 'Espèces'),
    ], default='orange_money')
    total_orders = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    loyalty_points = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    
    class Meta:
        verbose_name = "Profil Client"
        verbose_name_plural = "Profils Clients"
    
    def __str__(self):
        return f"Client: {self.user.username}"

class Transaction(models.Model):
    """Transactions et paiements des clients"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En traitement'),
        ('completed', 'Terminée'),
        ('failed', 'Échouée'),
        ('cancelled', 'Annulée'),
        ('refunded', 'Remboursée'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('orange_money', 'Orange Money'),
        ('moov_money', 'Moov Money'),
        ('wave', 'Wave'),
        ('carte_bancaire', 'Carte Bancaire'),
        ('especes', 'Espèces'),
    ]
    
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    mission = models.ForeignKey('missions.Mission', on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, unique=True)
    external_reference = models.CharField(max_length=200, blank=True)  # Référence du provider de paiement
    fees = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Transaction {self.transaction_id}: {self.amount} FCFA"
    
    @property
    def total_amount(self):
        return self.amount + self.fees

class ListeCourses(models.Model):
    """Listes de courses des clients"""
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listes_courses')
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    budget_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_favorite = models.BooleanField(default=False)
    is_template = models.BooleanField(default=False)  # Pour les listes réutilisables
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Liste de Courses"
        verbose_name_plural = "Listes de Courses"
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Liste: {self.nom} - {self.client.username}"
    
    @property
    def total_estimated_price(self):
        return sum(item.prix_estime or 0 for item in self.articles.all())
    
    @property
    def total_items(self):
        return self.articles.count()

class ArticleCourses(models.Model):
    """Articles dans une liste de courses"""
    liste = models.ForeignKey(ListeCourses, on_delete=models.CASCADE, related_name='articles')
    nom = models.CharField(max_length=200)
    quantite = models.CharField(max_length=50, default="1")  # Ex: "2 kg", "3 pièces"
    prix_estime = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)  # Coché par le livreur
    photo = models.ImageField(upload_to='courses_photos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Article de Courses"
        verbose_name_plural = "Articles de Courses"
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.nom} ({self.quantite}) - {self.liste.nom}"

class Portefeuille(models.Model):
    """Portefeuille virtuel du client"""
    client = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portefeuille')
    solde = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    solde_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Points de fidélité convertis
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Portefeuille"
        verbose_name_plural = "Portefeuilles"
    
    def __str__(self):
        return f"Portefeuille {self.client.username}: {self.solde} FCFA"
    
    @property
    def solde_total(self):
        return self.solde + self.solde_bonus

class MoyenPaiement(models.Model):
    """Moyens de paiement enregistrés par le client"""
    PAYMENT_TYPE_CHOICES = [
        ('orange_money', 'Orange Money'),
        ('moov_money', 'Moov Money'),
        ('wave', 'Wave'),
        ('carte_bancaire', 'Carte Bancaire'),
    ]
    
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='moyens_paiement')
    type_paiement = models.CharField(max_length=50, choices=PAYMENT_TYPE_CHOICES)
    nom_affiche = models.CharField(max_length=100)  # Ex: "Orange Money - 70123456"
    numero_masque = models.CharField(max_length=50)  # Ex: "****3456"
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Moyen de Paiement"
        verbose_name_plural = "Moyens de Paiement"
        ordering = ['-is_default', 'created_at']
    
    def __str__(self):
        return f"{self.nom_affiche} - {self.client.username}"

class AdresseFavorite(models.Model):
    """Adresses favorites du client"""
    TYPE_CHOICES = [
        ('domicile', 'Domicile'),
        ('travail', 'Travail'),
        ('autre', 'Autre'),
    ]
    
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='adresses_favorites')
    nom = models.CharField(max_length=100)
    type_adresse = models.CharField(max_length=20, choices=TYPE_CHOICES, default='autre')
    adresse_complete = models.TextField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    instructions = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Adresse Favorite"
        verbose_name_plural = "Adresses Favorites"
        ordering = ['-is_default', 'nom']
    
    def __str__(self):
        return f"{self.nom} - {self.client.username}"

class EstimationPrix(models.Model):
    """Estimations de prix pour les missions"""
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='estimations')
    adresse_depart = models.TextField()
    adresse_arrivee = models.TextField()
    type_colis = models.CharField(max_length=50)
    priorite = models.CharField(max_length=20)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    prix_estime = models.DecimalField(max_digits=10, decimal_places=2)
    delai_estime = models.PositiveIntegerField(help_text="Délai en minutes")
    created_at = models.DateTimeField(auto_now_add=True)
    is_converted = models.BooleanField(default=False)  # Convertie en vraie mission
    
    class Meta:
        verbose_name = "Estimation de Prix"
        verbose_name_plural = "Estimations de Prix"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Estimation {self.id}: {self.prix_estime} FCFA"


# ============================================
# MODULE "FAIRE MES COURSES" - VERSION 1.0
# ============================================

class MissionCourses(models.Model):
    """Mission de courses avec étapes multiples - Module Faire mes courses"""
    
    STATUS_CHOICES = [
        ('creee', 'Créée'),
        ('payee', 'Payée'),
        ('publiee', 'Publiée'),
        ('acceptee', 'Acceptée'),
        ('en_cours', 'En cours'),
        ('livree', 'Livrée'),
        ('cloturee', 'Clôturée'),
        ('annulee', 'Annulée'),
    ]
    
    DELAI_TYPE_CHOICES = [
        ('heure_limite', 'Heure limite'),
        ('duree_max', 'Durée maximum'),
    ]
    
    # Relations
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='missions_courses')
    livreur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='missions_courses_acceptees')
    candidats = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='missions_courses_postulees', blank=True)
    
    # Informations générales
    titre = models.CharField(max_length=200, help_text="Titre de la mission de courses")
    description = models.TextField(blank=True, help_text="Description générale de la mission")
    
    # Statut et progression
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='creee')
    etape_actuelle = models.PositiveIntegerField(default=1, help_text="Numéro de l'étape en cours")
    
    # Délai maximum (TRÈS IMPORTANT)
    delai_type = models.CharField(max_length=20, choices=DELAI_TYPE_CHOICES, default='duree_max')
    heure_limite = models.DateTimeField(null=True, blank=True, help_text="Heure limite si delai_type = 'heure_limite'")
    duree_max_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Durée max en minutes si delai_type = 'duree_max'")
    delai_debut = models.DateTimeField(null=True, blank=True, help_text="Moment où le délai commence (après acceptation)")
    
    # Calculs automatiques
    distance_totale_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Distance totale calculée")
    tarif_km = models.DecimalField(max_digits=8, decimal_places=2, default=500.00, help_text="Tarif par km en FCFA")
    frais_service = models.DecimalField(max_digits=8, decimal_places=2, default=1000.00, help_text="Frais de service fixes")
    surcharge_urgence = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Surcharge si délai court")
    
    # Prix
    prix_total = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], help_text="Prix total calculé")
    montant_courses = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Montant total des courses à acheter")
    
    # Paiement
    paiement_effectue = models.BooleanField(default=False)
    transaction_paiement = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='mission_courses')
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    date_publication = models.DateTimeField(null=True, blank=True)
    date_acceptation = models.DateTimeField(null=True, blank=True)
    date_livraison = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Mission de Courses"
        verbose_name_plural = "Missions de Courses"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Mission Courses #{self.id}: {self.titre}"
    
    @property
    def nombre_etapes(self):
        """Nombre total d'étapes de la mission"""
        return self.etapes.count()
    
    @property
    def est_en_retard(self):
        """Vérifie si la mission est en retard"""
        if not self.delai_debut:
            return False
        
        if self.delai_type == 'heure_limite' and self.heure_limite:
            return timezone.now() > self.heure_limite
        elif self.delai_type == 'duree_max_minutes' and self.duree_max_minutes:
            from django.utils import timezone
            from datetime import timedelta
            delai_fin = self.delai_debut + timedelta(minutes=self.duree_max_minutes)
            return timezone.now() > delai_fin
        
        return False
    
    def calculer_prix_total(self):
        """Calcule le prix total de la mission"""
        from datetime import timedelta
        
        # Prix de base = distance × tarif + frais service
        prix_base = (self.distance_totale_km or Decimal('0')) * self.tarif_km + self.frais_service
        
        # Surcharge urgence si délai court
        if self.delai_type == 'duree_max_minutes' and self.duree_max_minutes:
            if self.duree_max_minutes <= 60:  # Moins d'1h = très urgent
                surcharge = prix_base * Decimal('0.5')  # +50%
            elif self.duree_max_minutes <= 120:  # Moins de 2h = urgent
                surcharge = prix_base * Decimal('0.25')  # +25%
            else:
                surcharge = Decimal('0.00')
        else:
            surcharge = Decimal('0.00')
        
        self.surcharge_urgence = surcharge
        self.prix_total = prix_base + surcharge
        return self.prix_total


class EtapeMission(models.Model):
    """Étape d'une mission de courses (point de départ, lieu d'achat, livraison)"""
    
    TYPE_ETAPE_CHOICES = [
        ('depart', 'Point de départ'),
        ('achat', 'Lieu d\'achat'),
        ('depot', 'Dépôt intermédiaire'),
        ('livraison', 'Livraison finale'),
    ]
    
    mission = models.ForeignKey(MissionCourses, on_delete=models.CASCADE, related_name='etapes')
    numero_ordre = models.PositiveIntegerField(help_text="Ordre de l'étape (1, 2, 3...)")
    type_etape = models.CharField(max_length=20, choices=TYPE_ETAPE_CHOICES)
    
    # Localisation
    adresse = models.TextField(help_text="Adresse complète de l'étape")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    instructions = models.TextField(blank=True, help_text="Instructions spécifiques pour cette étape")
    
    # Action à effectuer
    action_requise = models.TextField(help_text="Action à effectuer à cette étape")
    montant_requis = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Montant d'argent requis (ex: pour récupérer ou acheter)")
    
    # Validation
    est_validee = models.BooleanField(default=False)
    date_validation = models.DateTimeField(null=True, blank=True)
    commentaire_validation = models.TextField(blank=True)
    
    # Dates
    date_debut = models.DateTimeField(null=True, blank=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Étape de Mission"
        verbose_name_plural = "Étapes de Mission"
        ordering = ['numero_ordre']
        unique_together = ['mission', 'numero_ordre']
    
    def __str__(self):
        return f"Étape {self.numero_ordre} - {self.get_type_etape_display()} - Mission #{self.mission.id}"


class ArticleCourseMission(models.Model):
    """Article à acheter dans une étape de mission"""
    
    etape = models.ForeignKey(EtapeMission, on_delete=models.CASCADE, related_name='articles')
    nom = models.CharField(max_length=200, help_text="Nom de l'article")
    quantite = models.CharField(max_length=50, default="1", help_text="Quantité (ex: '2 kg', '3 pièces')")
    
    # Prix
    prix_estime = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Prix estimé (facultatif)")
    prix_max_accepte = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Prix maximum accepté")
    prix_reel = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Prix réel payé (rempli par le livreur)")
    
    # Options
    substitution_autorisee = models.BooleanField(default=False, help_text="Substitution autorisée si article indisponible")
    commentaire = models.TextField(blank=True, help_text="Commentaire libre")
    
    # Validation
    est_achete = models.BooleanField(default=False)
    photo_produit = models.ImageField(upload_to='courses_photos/', null=True, blank=True)
    
    class Meta:
        verbose_name = "Article de Course"
        verbose_name_plural = "Articles de Course"
        ordering = ['nom']
    
    def __str__(self):
        return f"{self.nom} ({self.quantite}) - Étape {self.etape.numero_ordre}"


class ValidationEtape(models.Model):
    """Validation d'une étape avec preuves (photos, reçus)"""
    
    TYPE_PREUVE_CHOICES = [
        ('photo', 'Photo'),
        ('recu', 'Reçu'),
        ('signature', 'Signature'),
        ('confirmation', 'Confirmation'),
    ]
    
    etape = models.ForeignKey(EtapeMission, on_delete=models.CASCADE, related_name='validations')
    type_preuve = models.CharField(max_length=20, choices=TYPE_PREUVE_CHOICES)
    fichier = models.FileField(upload_to='validations_etapes/', null=True, blank=True)
    commentaire = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Validation d'Étape"
        verbose_name_plural = "Validations d'Étapes"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Validation {self.get_type_preuve_display()} - Étape {self.etape.numero_ordre}"
