"""
Vues utilisateurs sécurisées avec validation renforcée
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.core.paginator import Paginator
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from .models import User, LivreurProfile, EntrepriseProfile
from .forms import UserRegistrationForm, UserProfileForm, LivreurProfileForm, EntrepriseProfileForm
from location.utils import update_user_location

logger = logging.getLogger(__name__)

@csrf_protect
@require_http_methods(["GET", "POST"])
def register_view(request):
    """Vue d'inscription sécurisée avec validation renforcée"""
    try:
        if request.method == 'POST':
            with transaction.atomic():
                form = UserRegistrationForm(request.POST)
                if form.is_valid():
                    # Validation supplémentaire du mot de passe
                    password = form.cleaned_data.get('password1')
                    try:
                        validate_password(password)
                    except ValidationError as e:
                        for error in e.messages:
                            messages.error(request, error)
                        return render(request, 'users/register.html', {'form': form})
                    
                    # Validation de l'email
                    email = form.cleaned_data.get('email')
                    try:
                        validate_email(email)
                    except ValidationError:
                        messages.error(request, "Adresse email invalide.")
                        return render(request, 'users/register.html', {'form': form})
                    
                    # Vérification de l'unicité de l'email
                    if User.objects.filter(email=email).exists():
                        messages.error(request, "Cette adresse email est déjà utilisée.")
                        return render(request, 'users/register.html', {'form': form})
                    
                    user = form.save()
                    
                    # Authentification sécurisée
                    username = form.cleaned_data.get('username')
                    raw_password = form.cleaned_data.get('password1')
                    user = authenticate(username=username, password=raw_password)
                    
                    if user:
                        # Suppression de la connexion automatique après inscription
                        logger.info(f"Nouvel utilisateur inscrit: {user.id} ({user.username})")
                        messages.success(request, "Inscription réussie. Veuillez vous connecter.")
                        return redirect('login')
                    else:
                        logger.error(f"Échec d'authentification après inscription: {username}")
                        messages.error(request, "Erreur lors de la connexion automatique.")
                        return redirect('login')
                else:
                    logger.warning(f"Formulaire d'inscription invalide: {form.errors}")
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"{field}: {error}")
        else:
            form = UserRegistrationForm()
        
        return render(request, 'users/register.html', {'form': form})
        
    except Exception as e:
        logger.error(f"Erreur lors de l'inscription: {e}")
        messages.error(request, "Une erreur est survenue lors de l'inscription.")
        return render(request, 'users/register.html', {'form': UserRegistrationForm()})

@login_required
def profile_view(request):
    """Affichage du profil utilisateur avec contrôles de sécurité"""
    try:
        user = request.user
        context = {'user': user}
        
        # Récupération sécurisée des profils spécialisés
        if user.user_type == 'livreur':
            try:
                livreur_profile = user.livreurprofile
                context['livreur_profile'] = livreur_profile
            except LivreurProfile.DoesNotExist:
                logger.info(f"Profil livreur manquant pour l'utilisateur {user.id}")
                context['livreur_profile'] = None
                
        elif user.user_type == 'entreprise':
            try:
                entreprise_profile = user.entrepriseprofile
                context['entreprise_profile'] = entreprise_profile
            except EntrepriseProfile.DoesNotExist:
                logger.info(f"Profil entreprise manquant pour l'utilisateur {user.id}")
                context['entreprise_profile'] = None
        
        return render(request, 'users/profile.html', context)
        
    except Exception as e:
        logger.error(f"Erreur lors de l'affichage du profil: {e}")
        messages.error(request, "Erreur lors du chargement du profil.")
        return redirect('public:home')

@login_required
@csrf_protect
def edit_profile(request):
    """Édition du profil avec validation sécurisée"""
    try:
        user = request.user
        
        if request.method == 'POST':
            with transaction.atomic():
                user_form = UserProfileForm(request.POST, instance=user)
                profile_form = None
                
                # Formulaire spécialisé selon le type d'utilisateur
                if user.user_type == 'livreur':
                    try:
                        livreur_profile = user.livreurprofile
                    except LivreurProfile.DoesNotExist:
                        livreur_profile = LivreurProfile(user=user)
                    
                    profile_form = LivreurProfileForm(
                        request.POST, 
                        request.FILES, 
                        instance=livreur_profile
                    )
                    
                elif user.user_type == 'entreprise':
                    try:
                        entreprise_profile = user.entrepriseprofile
                    except EntrepriseProfile.DoesNotExist:
                        entreprise_profile = EntrepriseProfile(user=user)
                    
                    profile_form = EntrepriseProfileForm(
                        request.POST, 
                        request.FILES, 
                        instance=entreprise_profile
                    )
                
                # Validation des formulaires
                if user_form.is_valid() and (profile_form is None or profile_form.is_valid()):
                    # Validation de l'email si modifié
                    new_email = user_form.cleaned_data.get('email')
                    if new_email != user.email:
                        if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                            messages.error(request, "Cette adresse email est déjà utilisée.")
                            return render(request, 'users/edit_profile.html', {
                                'user_form': user_form,
                                'profile_form': profile_form
                            })
                        
                        try:
                            validate_email(new_email)
                        except ValidationError:
                            messages.error(request, "Adresse email invalide.")
                            return render(request, 'users/edit_profile.html', {
                                'user_form': user_form,
                                'profile_form': profile_form
                            })
                    
                    # Sauvegarde sécurisée
                    user_form.save()
                    if profile_form:
                        profile_form.save()
                    
                    logger.info(f"Profil mis à jour: utilisateur {user.id}")
                    messages.success(request, "Profil mis à jour avec succès!")
                    return redirect('users:profile')
                else:
                    # Affichage des erreurs
                    for field, errors in user_form.errors.items():
                        for error in errors:
                            messages.error(request, f"Utilisateur - {field}: {error}")
                    
                    if profile_form:
                        for field, errors in profile_form.errors.items():
                            for error in errors:
                                messages.error(request, f"Profil - {field}: {error}")
        else:
            user_form = UserProfileForm(instance=user)
            profile_form = None
            
            if user.user_type == 'livreur':
                try:
                    livreur_profile = user.livreurprofile
                except LivreurProfile.DoesNotExist:
                    livreur_profile = LivreurProfile(user=user)
                profile_form = LivreurProfileForm(instance=livreur_profile)
                
            elif user.user_type == 'entreprise':
                try:
                    entreprise_profile = user.entrepriseprofile
                except EntrepriseProfile.DoesNotExist:
                    entreprise_profile = EntrepriseProfile(user=user)
                profile_form = EntrepriseProfileForm(instance=entreprise_profile)
        
        context = {
            'user_form': user_form,
            'profile_form': profile_form,
        }
        
        return render(request, 'users/edit_profile.html', context)
        
    except Exception as e:
        logger.error(f"Erreur lors de l'édition du profil: {e}")
        messages.error(request, "Erreur lors de la modification du profil.")
        return redirect('users:profile')

@login_required
@csrf_protect
@require_http_methods(["POST"])
def simulate_location(request):
    """Simulation de localisation avec validation sécurisée"""
    try:
        if request.user.user_type != 'livreur':
            logger.warning(f"Tentative de simulation de localisation par non-livreur: {request.user.id}")
            return JsonResponse({
                'success': False, 
                'error': 'Seuls les livreurs peuvent simuler leur position'
            }, status=403)
        
        # Validation des coordonnées
        try:
            latitude = float(request.POST.get('latitude', 0))
            longitude = float(request.POST.get('longitude', 0))
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False, 
                'error': 'Coordonnées invalides'
            }, status=400)
        
        # Validation des limites géographiques (Burkina Faso approximatif)
        if not (9.0 <= latitude <= 15.5 and -6.0 <= longitude <= 3.0):
            logger.warning(f"Coordonnées suspectes: {latitude}, {longitude} par {request.user.id}")
            return JsonResponse({
                'success': False, 
                'error': 'Coordonnées en dehors de la zone de service'
            }, status=400)
        
        # Mise à jour sécurisée de la position
        location = update_user_location(request.user, latitude, longitude)
        
        if location:
            logger.info(f"Position simulée pour {request.user.id}: {latitude}, {longitude}")
            return JsonResponse({
                'success': True, 
                'message': 'Position mise à jour avec succès'
            })
        else:
            return JsonResponse({
                'success': False, 
                'error': 'Erreur lors de la mise à jour de la position'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Erreur lors de la simulation de localisation: {e}")
        return JsonResponse({
            'success': False, 
            'error': 'Erreur interne du serveur'
        }, status=500)

@login_required
def livreurs_list(request):
    """Liste des livreurs avec pagination et filtres sécurisés"""
    try:
        # Base queryset optimisée
        livreurs = User.objects.select_related('livreurprofile').filter(
            user_type='livreur',
            is_active=True
        )
        
        # Filtres sécurisés
        search = request.GET.get('search', '').strip()
        if search:
            if len(search) > 50:  # Limitation de la taille de recherche
                search = search[:50]
                messages.warning(request, "Terme de recherche tronqué.")
            
            livreurs = livreurs.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        # Filtre par disponibilité
        disponible = request.GET.get('disponible')
        if disponible == 'true':
            livreurs = livreurs.filter(livreurprofile__is_available=True)
        elif disponible == 'false':
            livreurs = livreurs.filter(livreurprofile__is_available=False)
        
        # Pagination sécurisée
        page_number = request.GET.get('page', 1)
        try:
            page_number = int(page_number)
            if page_number < 1:
                page_number = 1
        except ValueError:
            page_number = 1
        
        paginator = Paginator(livreurs, 12)  # 12 livreurs par page
        page_obj = paginator.get_page(page_number)
        
        context = {
            'livreurs': page_obj,
            'search': search,
            'disponible': disponible,
        }
        
        return render(request, 'users/livreurs_list.html', context)
        
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la liste des livreurs: {e}")
        messages.error(request, "Erreur lors du chargement des livreurs.")
        return render(request, 'users/livreurs_list.html', {'livreurs': []})

def custom_login_view(request):
    """Vue de connexion personnalisée avec sécurité renforcée"""
    try:
        if request.user.is_authenticated:
            return redirect('public:home')
        
        if request.method == 'POST':
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')
            
            # Validation basique
            if not username or not password:
                messages.error(request, "Nom d'utilisateur et mot de passe requis.")
                return render(request, 'registration/login.html')
            
            # Limitation de la taille des champs
            if len(username) > 150 or len(password) > 128:
                messages.error(request, "Nom d'utilisateur ou mot de passe trop long.")
                return render(request, 'registration/login.html')
            
            # Tentative d'authentification
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    logger.info(f"Connexion réussie: {user.id} ({user.username})")
                    
                    # Redirection sécurisée
                    next_url = request.GET.get('next')
                    if next_url and next_url.startswith('/'):
                        return redirect(next_url)
                    return redirect('public:home')
                else:
                    logger.warning(f"Tentative de connexion avec compte désactivé: {username}")
                    messages.error(request, "Votre compte a été désactivé.")
            else:
                logger.warning(f"Échec de connexion: {username}")
                messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
        
        return render(request, 'registration/login.html')
        
    except Exception as e:
        logger.error(f"Erreur lors de la connexion: {e}")
        messages.error(request, "Erreur lors de la connexion.")
        return render(request, 'registration/login.html')
