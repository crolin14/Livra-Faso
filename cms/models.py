from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.text import slugify
import uuid
import json

User = get_user_model()

class CMSPage(models.Model):
    """Modèle pour les pages CMS avec versioning"""
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('published', 'Publié'),
        ('archived', 'Archivé'),
    ]
    
    TEMPLATE_CHOICES = [
        ('default', 'Template par défaut'),
        ('landing', 'Page d\'atterrissage'),
        ('blog', 'Article de blog'),
        ('service', 'Page de service'),
        ('contact', 'Page de contact'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    title = models.CharField(max_length=200)
    meta_title = models.CharField(max_length=60, blank=True, help_text="Titre SEO (60 caractères max)")
    meta_description = models.CharField(max_length=160, blank=True, help_text="Description SEO (160 caractères max)")
    meta_keywords = models.TextField(blank=True, help_text="Mots-clés séparés par des virgules")
    
    # Contenu structuré en JSON
    content = models.JSONField(default=dict, help_text="Contenu structuré en blocs")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    version = models.PositiveIntegerField(default=1)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    template = models.CharField(max_length=100, choices=TEMPLATE_CHOICES, default='default')
    language = models.CharField(max_length=5, default='fr', db_index=True)
    
    # Métadonnées de publication
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Audit
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_pages')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='updated_pages')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Page CMS'
        verbose_name_plural = 'Pages CMS'
        indexes = [
            models.Index(fields=['status', 'language']),
            models.Index(fields=['slug', 'language']),
        ]

    def __str__(self):
        return f"{self.title} ({self.language})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        
        # Auto-increment version si le contenu change
        if self.pk and self.content:
            old_page = CMSPage.objects.get(pk=self.pk)
            if old_page.content != self.content:
                self.version += 1
        
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """URL de la page"""
        return f"/{self.language}/{self.slug}/"

    def create_version(self, user=None):
        """Créer une version de sauvegarde"""
        CMSPageVersion.objects.create(
            page=self,
            version=self.version,
            content=self.content,
            title=self.title,
            meta_data={
                'meta_title': self.meta_title,
                'meta_description': self.meta_description,
                'meta_keywords': self.meta_keywords,
                'template': self.template,
            },
            created_by=user
        )

    def revert_to_version(self, version_number, user=None):
        """Revenir à une version précédente"""
        try:
            version = self.versions.get(version=version_number)
            self.content = version.content
            self.title = version.title
            
            # Restaurer les métadonnées
            meta_data = version.meta_data or {}
            self.meta_title = meta_data.get('meta_title', '')
            self.meta_description = meta_data.get('meta_description', '')
            self.meta_keywords = meta_data.get('meta_keywords', '')
            self.template = meta_data.get('template', 'default')
            
            self.version += 1
            self.updated_by = user
            self.save()
            
            return True
        except CMSPageVersion.DoesNotExist:
            return False

    def get_blocks(self):
        """Récupérer les blocs de contenu"""
        return self.content.get('blocks', [])

    def add_block(self, block_data, position=None):
        """Ajouter un bloc de contenu"""
        if 'blocks' not in self.content:
            self.content['blocks'] = []
        
        if position is None:
            self.content['blocks'].append(block_data)
        else:
            self.content['blocks'].insert(position, block_data)
        
        self.save()

    def remove_block(self, block_id):
        """Supprimer un bloc par son ID"""
        if 'blocks' in self.content:
            self.content['blocks'] = [
                block for block in self.content['blocks'] 
                if block.get('id') != block_id
            ]
            self.save()

    def update_block(self, block_id, block_data):
        """Mettre à jour un bloc"""
        if 'blocks' in self.content:
            for i, block in enumerate(self.content['blocks']):
                if block.get('id') == block_id:
                    self.content['blocks'][i] = block_data
                    self.save()
                    return True
        return False

class CMSPageVersion(models.Model):
    """Versions des pages CMS"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(CMSPage, on_delete=models.CASCADE, related_name='versions')
    version = models.PositiveIntegerField()
    content = models.JSONField()
    title = models.CharField(max_length=200)
    meta_data = models.JSONField(default=dict)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['page', 'version']
        ordering = ['-version']
        verbose_name = 'Version de page'
        verbose_name_plural = 'Versions de pages'

    def __str__(self):
        return f"{self.page.title} v{self.version}"

class CMSBlock(models.Model):
    """Blocs de contenu réutilisables"""
    BLOCK_TYPES = [
        ('text', 'Texte'),
        ('image', 'Image'),
        ('video', 'Vidéo'),
        ('gallery', 'Galerie'),
        ('hero', 'Section héro'),
        ('cta', 'Call-to-Action'),
        ('testimonial', 'Témoignage'),
        ('faq', 'FAQ'),
        ('form', 'Formulaire'),
        ('map', 'Carte'),
        ('social', 'Réseaux sociaux'),
        ('custom', 'Personnalisé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=50, choices=BLOCK_TYPES)
    content = models.JSONField(help_text="Configuration et données du bloc")
    is_global = models.BooleanField(default=False, help_text="Bloc réutilisable globalement")
    category = models.CharField(max_length=50, blank=True, help_text="Catégorie pour l'organisation")
    
    # Métadonnées
    description = models.TextField(blank=True)
    preview_image = models.ImageField(upload_to='cms/block_previews/', blank=True)
    
    # Audit
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Bloc CMS'
        verbose_name_plural = 'Blocs CMS'

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    def get_schema(self):
        """Schéma de configuration du bloc selon son type"""
        schemas = {
            'text': {
                'content': {'type': 'string', 'required': True},
                'style': {'type': 'object', 'properties': {
                    'fontSize': {'type': 'string'},
                    'color': {'type': 'string'},
                    'alignment': {'type': 'string', 'enum': ['left', 'center', 'right']}
                }}
            },
            'image': {
                'src': {'type': 'string', 'required': True},
                'alt': {'type': 'string', 'required': True},
                'caption': {'type': 'string'},
                'link': {'type': 'string'},
                'style': {'type': 'object', 'properties': {
                    'width': {'type': 'string'},
                    'height': {'type': 'string'},
                    'objectFit': {'type': 'string', 'enum': ['cover', 'contain', 'fill']}
                }}
            },
            'hero': {
                'title': {'type': 'string', 'required': True},
                'subtitle': {'type': 'string'},
                'backgroundImage': {'type': 'string'},
                'cta': {'type': 'object', 'properties': {
                    'text': {'type': 'string'},
                    'url': {'type': 'string'},
                    'style': {'type': 'string', 'enum': ['primary', 'secondary', 'outline']}
                }}
            },
            'cta': {
                'title': {'type': 'string', 'required': True},
                'description': {'type': 'string'},
                'buttonText': {'type': 'string', 'required': True},
                'buttonUrl': {'type': 'string', 'required': True},
                'style': {'type': 'string', 'enum': ['primary', 'secondary', 'success', 'warning']}
            }
        }
        return schemas.get(self.type, {})

class CMSMedia(models.Model):
    """Bibliothèque de médias"""
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Vidéo'),
        ('audio', 'Audio'),
        ('document', 'Document'),
        ('other', 'Autre'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField(help_text="Taille en octets")
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES)
    
    # Chemin de stockage
    file = models.FileField(upload_to='cms/media/%Y/%m/')
    
    # Métadonnées
    alt_text = models.CharField(max_length=255, blank=True, help_text="Texte alternatif pour l'accessibilité")
    caption = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, help_text="Métadonnées EXIF, dimensions, etc.")
    
    # Organisation
    folder = models.CharField(max_length=100, blank=True, help_text="Dossier virtuel")
    tags = models.CharField(max_length=500, blank=True, help_text="Tags séparés par des virgules")
    
    # Audit
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Média CMS'
        verbose_name_plural = 'Médias CMS'

    def __str__(self):
        return self.original_name

    def get_file_size_display(self):
        """Taille du fichier formatée"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def get_dimensions(self):
        """Dimensions pour les images"""
        if self.media_type == 'image' and 'dimensions' in self.metadata:
            dims = self.metadata['dimensions']
            return f"{dims['width']}x{dims['height']}"
        return None

class CMSMenu(models.Model):
    """Menus de navigation"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=50, help_text="Emplacement du menu (header, footer, sidebar)")
    language = models.CharField(max_length=5, default='fr')
    is_active = models.BooleanField(default=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['location', 'name']
        verbose_name = 'Menu CMS'
        verbose_name_plural = 'Menus CMS'

    def __str__(self):
        return f"{self.name} ({self.location})"

class CMSMenuItem(models.Model):
    """Éléments de menu"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menu = models.ForeignKey(CMSMenu, on_delete=models.CASCADE, related_name='items')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    
    title = models.CharField(max_length=100)
    url = models.CharField(max_length=500, blank=True)
    page = models.ForeignKey(CMSPage, null=True, blank=True, on_delete=models.CASCADE)
    
    # Configuration
    target = models.CharField(max_length=20, default='_self', choices=[
        ('_self', 'Même fenêtre'),
        ('_blank', 'Nouvelle fenêtre'),
    ])
    css_class = models.CharField(max_length=100, blank=True)
    icon = models.CharField(max_length=50, blank=True)
    
    # Ordre d'affichage
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'Élément de menu'
        verbose_name_plural = 'Éléments de menu'

    def __str__(self):
        return self.title

    def get_url(self):
        """URL finale de l'élément"""
        if self.page:
            return self.page.get_absolute_url()
        return self.url or '#'

class CMSRedirect(models.Model):
    """Redirections d'URLs"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    old_path = models.CharField(max_length=500, unique=True, db_index=True)
    new_path = models.CharField(max_length=500)
    status_code = models.PositiveIntegerField(default=301, choices=[
        (301, '301 - Redirection permanente'),
        (302, '302 - Redirection temporaire'),
    ])
    is_active = models.BooleanField(default=True)
    
    # Statistiques
    hit_count = models.PositiveIntegerField(default=0)
    last_hit = models.DateTimeField(null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Redirection'
        verbose_name_plural = 'Redirections'

    def __str__(self):
        return f"{self.old_path} → {self.new_path}"
