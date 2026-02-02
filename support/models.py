from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()


class SupportCategory(models.Model):
    """
    Catégories de tickets de support
    """
    name = models.CharField(max_length=100, verbose_name="Nom de la catégorie")
    description = models.TextField(blank=True, verbose_name="Description")
    color = models.CharField(max_length=7, default="#3b82f6", verbose_name="Couleur (hex)")
    icon = models.CharField(max_length=50, default="help-circle", verbose_name="Icône")
    
    # Configuration
    is_active = models.BooleanField(default=True, verbose_name="Active")
    auto_assign_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Assignation automatique",
        limit_choices_to={'user_roles__role__codename__in': ['support_agent', 'admin', 'manager']}
    )
    
    # SLA (Service Level Agreement)
    response_time_hours = models.PositiveIntegerField(
        default=24, verbose_name="Temps de réponse (heures)"
    )
    resolution_time_hours = models.PositiveIntegerField(
        default=72, verbose_name="Temps de résolution (heures)"
    )
    
    # Ordre d'affichage
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Catégorie de support"
        verbose_name_plural = "Catégories de support"
    
    def __str__(self):
        return self.name


class SupportTicket(models.Model):
    """
    Ticket de support principal
    """
    PRIORITY_CHOICES = [
        ('low', 'Faible'),
        ('medium', 'Moyen'),
        ('high', 'Élevé'),
        ('urgent', 'Urgent'),
        ('critical', 'Critique'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Ouvert'),
        ('in_progress', 'En cours'),
        ('waiting_customer', 'En attente client'),
        ('waiting_internal', 'En attente interne'),
        ('resolved', 'Résolu'),
        ('closed', 'Fermé'),
        ('cancelled', 'Annulé'),
    ]
    
    SOURCE_CHOICES = [
        ('web', 'Site web'),
        ('mobile', 'Application mobile'),
        ('email', 'Email'),
        ('phone', 'Téléphone'),
        ('chat', 'Chat en direct'),
        ('admin', 'Interface admin'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(max_length=20, unique=True, verbose_name="Numéro de ticket")
    
    # Informations de base
    title = models.CharField(max_length=200, verbose_name="Titre")
    description = models.TextField(verbose_name="Description")
    category = models.ForeignKey(
        SupportCategory, on_delete=models.CASCADE,
        verbose_name="Catégorie"
    )
    
    # Utilisateur
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='support_tickets',
        verbose_name="Utilisateur"
    )
    user_email = models.EmailField(verbose_name="Email de contact")
    user_phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    
    # Classification
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default='medium',
        verbose_name="Priorité"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='open',
        verbose_name="Statut"
    )
    source = models.CharField(
        max_length=10, choices=SOURCE_CHOICES, default='web',
        verbose_name="Source"
    )
    
    # Assignation
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_tickets',
        verbose_name="Assigné à",
        limit_choices_to={'user_roles__role__codename__in': ['support_agent', 'admin', 'manager']}
    )
    assigned_at = models.DateTimeField(null=True, blank=True, verbose_name="Assigné le")
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tickets_assigned_by_me',
        verbose_name="Assigné par"
    )
    
    # Objets liés
    related_mission = models.ForeignKey(
        'missions.Mission', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Mission liée"
    )
    related_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tickets_about_me',
        verbose_name="Utilisateur concerné"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Mis à jour le")
    
    # Résolution
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Résolu le")
    resolved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tickets_resolved_by_me',
        verbose_name="Résolu par"
    )
    resolution_notes = models.TextField(blank=True, verbose_name="Notes de résolution")
    
    # Fermeture
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="Fermé le")
    closed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tickets_closed_by_me',
        verbose_name="Fermé par"
    )
    
    # SLA et métriques
    first_response_at = models.DateTimeField(null=True, blank=True, verbose_name="Première réponse le")
    sla_response_due = models.DateTimeField(null=True, blank=True, verbose_name="SLA réponse dû le")
    sla_resolution_due = models.DateTimeField(null=True, blank=True, verbose_name="SLA résolution dû le")
    
    # Satisfaction client
    satisfaction_rating = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Note de satisfaction (1-5)"
    )
    satisfaction_comment = models.TextField(blank=True, verbose_name="Commentaire satisfaction")
    satisfaction_submitted_at = models.DateTimeField(null=True, blank=True)
    
    # Flags
    is_escalated = models.BooleanField(default=False, verbose_name="Escaladé")
    is_internal = models.BooleanField(default=False, verbose_name="Ticket interne")
    requires_followup = models.BooleanField(default=False, verbose_name="Nécessite un suivi")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority', 'created_at']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['category', 'status']),
        ]
        verbose_name = "Ticket de support"
        verbose_name_plural = "Tickets de support"
    
    def __str__(self):
        return f"#{self.ticket_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = self.generate_ticket_number()
        
        # Auto-assignation selon la catégorie
        if not self.assigned_to and self.category.auto_assign_to:
            self.assigned_to = self.category.auto_assign_to
            self.assigned_at = timezone.now()
        
        # Calculer les SLA
        if not self.sla_response_due:
            self.sla_response_due = self.created_at + timezone.timedelta(
                hours=self.category.response_time_hours
            )
        
        if not self.sla_resolution_due:
            self.sla_resolution_due = self.created_at + timezone.timedelta(
                hours=self.category.resolution_time_hours
            )
        
        super().save(*args, **kwargs)
    
    @classmethod
    def generate_ticket_number(cls):
        """Génère un numéro de ticket unique"""
        import random
        import string
        
        while True:
            number = f"TK{timezone.now().strftime('%Y%m')}" + ''.join(
                random.choices(string.digits, k=4)
            )
            if not cls.objects.filter(ticket_number=number).exists():
                return number
    
    def is_overdue_response(self):
        """Vérifie si le ticket est en retard pour la première réponse"""
        if self.first_response_at:
            return False
        return timezone.now() > self.sla_response_due
    
    def is_overdue_resolution(self):
        """Vérifie si le ticket est en retard pour la résolution"""
        if self.resolved_at:
            return False
        return timezone.now() > self.sla_resolution_due
    
    def get_response_time(self):
        """Calcule le temps de première réponse"""
        if not self.first_response_at:
            return None
        return self.first_response_at - self.created_at
    
    def get_resolution_time(self):
        """Calcule le temps de résolution"""
        if not self.resolved_at:
            return None
        return self.resolved_at - self.created_at


class TicketMessage(models.Model):
    """
    Messages dans un ticket de support
    """
    MESSAGE_TYPES = [
        ('user', 'Message utilisateur'),
        ('agent', 'Réponse agent'),
        ('system', 'Message système'),
        ('internal', 'Note interne'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        SupportTicket, on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Ticket"
    )
    
    # Auteur
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        verbose_name="Auteur"
    )
    author_name = models.CharField(max_length=100, verbose_name="Nom de l'auteur")
    author_email = models.EmailField(verbose_name="Email de l'auteur")
    
    # Contenu
    message_type = models.CharField(
        max_length=10, choices=MESSAGE_TYPES,
        verbose_name="Type de message"
    )
    content = models.TextField(verbose_name="Contenu")
    is_html = models.BooleanField(default=False, verbose_name="Contenu HTML")
    
    # Métadonnées
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Créé le")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adresse IP")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    
    # Flags
    is_first_response = models.BooleanField(default=False, verbose_name="Première réponse")
    is_public = models.BooleanField(default=True, verbose_name="Visible par l'utilisateur")
    
    class Meta:
        ordering = ['created_at']
        verbose_name = "Message de ticket"
        verbose_name_plural = "Messages de ticket"
    
    def __str__(self):
        return f"{self.ticket.ticket_number} - {self.author_name} ({self.created_at})"
    
    def save(self, *args, **kwargs):
        # Marquer comme première réponse si c'est le cas
        if (self.message_type == 'agent' and 
            not self.ticket.first_response_at and 
            not self.ticket.messages.filter(message_type='agent').exists()):
            self.is_first_response = True
            self.ticket.first_response_at = self.created_at
            self.ticket.save(update_fields=['first_response_at'])
        
        super().save(*args, **kwargs)


class TicketAttachment(models.Model):
    """
    Pièces jointes des tickets
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        SupportTicket, on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name="Ticket"
    )
    message = models.ForeignKey(
        TicketMessage, on_delete=models.CASCADE, null=True, blank=True,
        related_name='attachments',
        verbose_name="Message"
    )
    
    # Fichier
    file = models.FileField(upload_to='support/attachments/%Y/%m/', verbose_name="Fichier")
    original_filename = models.CharField(max_length=255, verbose_name="Nom original")
    file_size = models.PositiveIntegerField(verbose_name="Taille (bytes)")
    content_type = models.CharField(max_length=100, verbose_name="Type MIME")
    
    # Métadonnées
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Uploadé par")
    uploaded_at = models.DateTimeField(default=timezone.now, verbose_name="Uploadé le")
    
    # Sécurité
    is_safe = models.BooleanField(default=True, verbose_name="Fichier sûr")
    scan_result = models.TextField(blank=True, verbose_name="Résultat scan antivirus")
    
    class Meta:
        ordering = ['uploaded_at']
        verbose_name = "Pièce jointe"
        verbose_name_plural = "Pièces jointes"
    
    def __str__(self):
        return f"{self.ticket.ticket_number} - {self.original_filename}"


class TicketTemplate(models.Model):
    """
    Modèles de réponses pour les tickets
    """
    TEMPLATE_TYPES = [
        ('response', 'Réponse standard'),
        ('resolution', 'Résolution'),
        ('followup', 'Suivi'),
        ('escalation', 'Escalade'),
        ('closure', 'Fermeture'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Nom du modèle")
    description = models.TextField(blank=True, verbose_name="Description")
    template_type = models.CharField(
        max_length=20, choices=TEMPLATE_TYPES,
        verbose_name="Type de modèle"
    )
    
    # Contenu
    subject_template = models.CharField(max_length=200, verbose_name="Modèle de sujet")
    content_template = models.TextField(verbose_name="Modèle de contenu")
    
    # Configuration
    category = models.ForeignKey(
        SupportCategory, on_delete=models.CASCADE, null=True, blank=True,
        verbose_name="Catégorie spécifique"
    )
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    # Métadonnées
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Créé par")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Créé le")
    usage_count = models.PositiveIntegerField(default=0, verbose_name="Nombre d'utilisations")
    
    class Meta:
        ordering = ['template_type', 'name']
        verbose_name = "Modèle de ticket"
        verbose_name_plural = "Modèles de ticket"
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class SupportKnowledgeBase(models.Model):
    """
    Base de connaissances pour le support
    """
    ARTICLE_TYPES = [
        ('faq', 'FAQ'),
        ('tutorial', 'Tutoriel'),
        ('troubleshooting', 'Dépannage'),
        ('policy', 'Politique'),
        ('announcement', 'Annonce'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Titre")
    slug = models.SlugField(unique=True, verbose_name="Slug")
    content = models.TextField(verbose_name="Contenu")
    excerpt = models.TextField(blank=True, verbose_name="Extrait")
    
    # Classification
    article_type = models.CharField(
        max_length=20, choices=ARTICLE_TYPES,
        verbose_name="Type d'article"
    )
    categories = models.ManyToManyField(
        SupportCategory, blank=True,
        verbose_name="Catégories"
    )
    tags = models.CharField(max_length=500, blank=True, verbose_name="Tags (séparés par des virgules)")
    
    # Visibilité
    is_published = models.BooleanField(default=False, verbose_name="Publié")
    is_public = models.BooleanField(default=True, verbose_name="Public")
    
    # Métadonnées
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Auteur")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Mis à jour le")
    
    # Statistiques
    view_count = models.PositiveIntegerField(default=0, verbose_name="Nombre de vues")
    helpful_votes = models.PositiveIntegerField(default=0, verbose_name="Votes utiles")
    total_votes = models.PositiveIntegerField(default=0, verbose_name="Total des votes")
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = "Article de base de connaissances"
        verbose_name_plural = "Articles de base de connaissances"
    
    def __str__(self):
        return self.title
    
    def get_helpfulness_ratio(self):
        """Calcule le ratio d'utilité"""
        if self.total_votes == 0:
            return 0
        return (self.helpful_votes / self.total_votes) * 100


class SupportMetrics(models.Model):
    """
    Métriques de support par jour
    """
    date = models.DateField(unique=True, verbose_name="Date")
    
    # Tickets
    tickets_created = models.PositiveIntegerField(default=0, verbose_name="Tickets créés")
    tickets_resolved = models.PositiveIntegerField(default=0, verbose_name="Tickets résolus")
    tickets_closed = models.PositiveIntegerField(default=0, verbose_name="Tickets fermés")
    
    # Temps de réponse
    avg_first_response_time = models.DurationField(null=True, blank=True, verbose_name="Temps moyen première réponse")
    avg_resolution_time = models.DurationField(null=True, blank=True, verbose_name="Temps moyen résolution")
    
    # SLA
    sla_response_met = models.PositiveIntegerField(default=0, verbose_name="SLA réponse respecté")
    sla_resolution_met = models.PositiveIntegerField(default=0, verbose_name="SLA résolution respecté")
    
    # Satisfaction
    avg_satisfaction_rating = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True,
        verbose_name="Note moyenne satisfaction"
    )
    satisfaction_responses = models.PositiveIntegerField(default=0, verbose_name="Réponses satisfaction")
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-date']
        verbose_name = "Métriques de support"
        verbose_name_plural = "Métriques de support"
    
    def __str__(self):
        return f"Métriques {self.date}"
