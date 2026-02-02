from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from rbac.permissions import admin_required, require_permission
import json
import uuid
from .models import CMSPage, CMSPageVersion, CMSBlock, CMSMedia, CMSMenu, CMSMenuItem
from users.models import User


@admin_required
def cms_dashboard(request):
    """Dashboard principal du CMS"""
    # Statistiques
    stats = {
        'total_pages': CMSPage.objects.count(),
        'published_pages': CMSPage.objects.filter(status='published').count(),
        'draft_pages': CMSPage.objects.filter(status='draft').count(),
        'total_blocks': CMSBlock.objects.count(),
        'total_media': CMSMedia.objects.count(),
    }
    
    # Pages récentes
    recent_pages = CMSPage.objects.select_related('created_by', 'updated_by').order_by('-updated_at')[:10]
    
    # Blocs populaires
    popular_blocks = CMSBlock.objects.filter(is_global=True).order_by('-created_at')[:8]
    
    context = {
        'title': 'CMS Dashboard',
        'stats': stats,
        'recent_pages': recent_pages,
        'popular_blocks': popular_blocks,
    }
    
    return render(request, 'cms/dashboard.html', context)


@admin_required
def pages_list(request):
    """Liste des pages CMS"""
    pages = CMSPage.objects.select_related('created_by', 'updated_by').order_by('-updated_at')
    
    # Filtres
    status_filter = request.GET.get('status')
    language_filter = request.GET.get('language', 'fr')
    search = request.GET.get('search')
    
    if status_filter:
        pages = pages.filter(status=status_filter)
    
    if language_filter:
        pages = pages.filter(language=language_filter)
    
    if search:
        pages = pages.filter(
            Q(title__icontains=search) | 
            Q(slug__icontains=search) |
            Q(meta_description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(pages, 20)
    page_number = request.GET.get('page')
    pages_page = paginator.get_page(page_number)
    
    context = {
        'title': 'Pages CMS',
        'pages': pages_page,
        'status_filter': status_filter,
        'language_filter': language_filter,
        'search': search,
    }
    
    return render(request, 'cms/pages_list.html', context)


@admin_required
def page_editor(request, page_id=None):
    """Éditeur de page avec drag & drop"""
    page = None
    if page_id:
        page = get_object_or_404(CMSPage, id=page_id)
    
    # Blocs disponibles
    available_blocks = CMSBlock.objects.filter(is_global=True).order_by('category', 'name')
    
    # Versions de la page
    versions = []
    if page:
        versions = page.versions.order_by('-version')[:10]
    
    context = {
        'title': f'Éditeur - {page.title}' if page else 'Nouvelle page',
        'page': page,
        'available_blocks': available_blocks,
        'versions': versions,
        'block_categories': CMSBlock.objects.values_list('category', flat=True).distinct(),
    }
    
    return render(request, 'cms/page_editor.html', context)


@require_http_methods(["POST"])
@admin_required
def save_page(request):
    """Sauvegarder une page CMS"""
    try:
        data = json.loads(request.body)
        page_id = data.get('page_id')
        
        if page_id:
            page = get_object_or_404(CMSPage, id=page_id)
            # Créer une version avant modification
            page.create_version(request.user)
        else:
            page = CMSPage()
            page.created_by = request.user
        
        # Mettre à jour les données
        page.title = data.get('title', '')
        page.slug = data.get('slug', '')
        page.meta_title = data.get('meta_title', '')
        page.meta_description = data.get('meta_description', '')
        page.meta_keywords = data.get('meta_keywords', '')
        page.content = data.get('content', {})
        page.status = data.get('status', 'draft')
        page.template = data.get('template', 'default')
        page.language = data.get('language', 'fr')
        page.updated_by = request.user
        
        if data.get('status') == 'published' and not page.published_at:
            page.published_at = timezone.now()
        
        page.save()
        
        return JsonResponse({
            'success': True,
            'page_id': str(page.id),
            'version': page.version,
            'message': 'Page sauvegardée avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["POST"])
@admin_required
def duplicate_page(request, page_id):
    """Dupliquer une page"""
    try:
        original_page = get_object_or_404(CMSPage, id=page_id)
        
        # Créer une copie
        new_page = CMSPage(
            title=f"{original_page.title} (Copie)",
            slug=f"{original_page.slug}-copy",
            meta_title=original_page.meta_title,
            meta_description=original_page.meta_description,
            meta_keywords=original_page.meta_keywords,
            content=original_page.content.copy(),
            template=original_page.template,
            language=original_page.language,
            status='draft',
            created_by=request.user,
            updated_by=request.user
        )
        new_page.save()
        
        return JsonResponse({
            'success': True,
            'page_id': str(new_page.id),
            'message': 'Page dupliquée avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["POST"])
@admin_required
def delete_page(request, page_id):
    """Supprimer une page"""
    try:
        page = get_object_or_404(CMSPage, id=page_id)
        page_title = page.title
        page.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Page "{page_title}" supprimée avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["POST"])
@admin_required
def revert_page_version(request, page_id, version_number):
    """Revenir à une version précédente"""
    try:
        page = get_object_or_404(CMSPage, id=page_id)
        
        if page.revert_to_version(version_number, request.user):
            return JsonResponse({
                'success': True,
                'message': f'Page restaurée à la version {version_number}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Version introuvable'
            }, status=404)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@admin_required
def blocks_library(request):
    """Bibliothèque de blocs"""
    blocks = CMSBlock.objects.order_by('category', 'name')
    
    # Filtres
    category_filter = request.GET.get('category')
    type_filter = request.GET.get('type')
    search = request.GET.get('search')
    
    if category_filter:
        blocks = blocks.filter(category=category_filter)
    
    if type_filter:
        blocks = blocks.filter(type=type_filter)
    
    if search:
        blocks = blocks.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(blocks, 24)
    page_number = request.GET.get('page')
    blocks_page = paginator.get_page(page_number)
    
    # Catégories et types disponibles
    categories = CMSBlock.objects.values_list('category', flat=True).distinct()
    block_types = CMSBlock.BLOCK_TYPES
    
    context = {
        'title': 'Bibliothèque de blocs',
        'blocks': blocks_page,
        'categories': categories,
        'block_types': block_types,
        'category_filter': category_filter,
        'type_filter': type_filter,
        'search': search,
    }
    
    return render(request, 'cms/blocks_library.html', context)


@require_http_methods(["POST"])
@admin_required
def create_block(request):
    """Créer un nouveau bloc"""
    try:
        data = json.loads(request.body)
        
        block = CMSBlock(
            name=data.get('name', ''),
            type=data.get('type', 'text'),
            content=data.get('content', {}),
            category=data.get('category', ''),
            description=data.get('description', ''),
            is_global=data.get('is_global', False),
            created_by=request.user
        )
        block.save()
        
        return JsonResponse({
            'success': True,
            'block_id': str(block.id),
            'message': 'Bloc créé avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@admin_required
def media_library(request):
    """Bibliothèque de médias"""
    media = CMSMedia.objects.order_by('-created_at')
    
    # Filtres
    media_type_filter = request.GET.get('type')
    folder_filter = request.GET.get('folder')
    search = request.GET.get('search')
    
    if media_type_filter:
        media = media.filter(media_type=media_type_filter)
    
    if folder_filter:
        media = media.filter(folder=folder_filter)
    
    if search:
        media = media.filter(
            Q(original_name__icontains=search) |
            Q(alt_text__icontains=search) |
            Q(tags__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(media, 30)
    page_number = request.GET.get('page')
    media_page = paginator.get_page(page_number)
    
    # Dossiers et types disponibles
    folders = CMSMedia.objects.values_list('folder', flat=True).distinct()
    media_types = CMSMedia.MEDIA_TYPES
    
    context = {
        'title': 'Bibliothèque de médias',
        'media': media_page,
        'folders': folders,
        'media_types': media_types,
        'media_type_filter': media_type_filter,
        'folder_filter': folder_filter,
        'search': search,
    }
    
    return render(request, 'cms/media_library.html', context)


@require_http_methods(["POST"])
@admin_required
@csrf_exempt
def upload_media(request):
    """Upload de média"""
    try:
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return JsonResponse({'success': False, 'error': 'Aucun fichier fourni'})
        
        # Déterminer le type de média
        mime_type = uploaded_file.content_type
        media_type = 'other'
        
        if mime_type.startswith('image/'):
            media_type = 'image'
        elif mime_type.startswith('video/'):
            media_type = 'video'
        elif mime_type.startswith('audio/'):
            media_type = 'audio'
        elif mime_type in ['application/pdf', 'application/msword', 'text/plain']:
            media_type = 'document'
        
        # Créer l'objet média
        media = CMSMedia(
            filename=uploaded_file.name,
            original_name=uploaded_file.name,
            mime_type=mime_type,
            file_size=uploaded_file.size,
            media_type=media_type,
            file=uploaded_file,
            folder=request.POST.get('folder', ''),
            alt_text=request.POST.get('alt_text', ''),
            caption=request.POST.get('caption', ''),
            tags=request.POST.get('tags', ''),
            uploaded_by=request.user
        )
        media.save()
        
        return JsonResponse({
            'success': True,
            'media_id': str(media.id),
            'url': media.file.url,
            'message': 'Fichier uploadé avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@admin_required
def get_page_data(request, page_id):
    """Récupérer les données d'une page pour l'éditeur"""
    try:
        page = get_object_or_404(CMSPage, id=page_id)
        
        data = {
            'id': str(page.id),
            'title': page.title,
            'slug': page.slug,
            'meta_title': page.meta_title,
            'meta_description': page.meta_description,
            'meta_keywords': page.meta_keywords,
            'content': page.content,
            'status': page.status,
            'template': page.template,
            'language': page.language,
            'version': page.version,
            'created_at': page.created_at.isoformat(),
            'updated_at': page.updated_at.isoformat(),
        }
        
        return JsonResponse({
            'success': True,
            'page': data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@admin_required
def get_block_data(request, block_id):
    """Récupérer les données d'un bloc"""
    try:
        block = get_object_or_404(CMSBlock, id=block_id)
        
        data = {
            'id': str(block.id),
            'name': block.name,
            'type': block.type,
            'content': block.content,
            'category': block.category,
            'description': block.description,
            'schema': block.get_schema(),
        }
        
        return JsonResponse({
            'success': True,
            'block': data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
