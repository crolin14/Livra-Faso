from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model, login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from .forms import UserRegistrationForm, UserProfileForm, LivreurProfileForm, EntrepriseProfileForm
from .models import LivreurProfile, EntrepriseProfile
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

@csrf_protect
@never_cache
def login_view(request):
    """Vue de connexion personnalisée avec redirection selon le rôle"""
    if request.user.is_authenticated:
        return redirect('public:dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                logger.info(f"Connexion réussie pour l'utilisateur: {user.username} (type: {user.user_type})")
                
                # Redirection selon le type d'utilisateur
                if user.user_type == 'client':
                    messages.success(request, f'Bienvenue {user.get_full_name() or user.username} !')
                    return redirect('public:dashboard')
                elif user.user_type == 'livreur':
                    messages.success(request, f'Bienvenue {user.get_full_name() or user.username} !')
                    return redirect('public:dashboard')
                elif user.user_type == 'entreprise':
                    messages.success(request, f'Bienvenue {user.get_full_name() or user.username} !')
                    return redirect('public:dashboard')
                elif user.user_type == 'admin' or user.is_superuser:
                    messages.success(request, f'Bienvenue Administrateur {user.get_full_name() or user.username} !')
                    return redirect('public:admin_dashboard')
                else:
                    messages.success(request, f'Bienvenue {user.get_full_name() or user.username} !')
                    return redirect('public:dashboard')
            else:
                messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})

@never_cache
def logout_view(request):
    """Vue de déconnexion personnalisée avec nettoyage complet"""
    if request.user.is_authenticated:
        username = request.user.username
        logger.info(f"Déconnexion de l'utilisateur: {username}")
        
        # Déconnexion propre
        logout(request)
        
        # Nettoyage explicite de la session
        request.session.flush()
        
        # Message de confirmation
        messages.success(request, 'Vous avez été déconnecté avec succès.')
    
    return redirect('public:home')

@login_required
def dashboard_redirect(request):
    """Redirect to appropriate dashboard based on user type"""
    user = request.user
    
    if user.user_type == 'client':
        return render(request, 'dashboards/client_dashboard.html', {
            'title': 'Dashboard Client',
            'user': user,
        })
    elif user.user_type == 'livreur':
        return render(request, 'dashboards/livreur_dashboard.html', {
            'title': 'Dashboard Livreur',
            'user': user,
        })
    elif user.user_type == 'entreprise':
        return render(request, 'dashboards/entreprise_dashboard.html', {
            'title': 'Dashboard Entreprise',
            'user': user,
        })
    elif user.user_type == 'admin' or user.is_superuser:
        return render(request, 'dashboards/admin_dashboard.html', {
            'title': 'Dashboard Admin',
            'user': user,
        })
    else:
        messages.error(request, 'Type d\'utilisateur non reconnu')
        return redirect('users:profile')

@login_required
def profile(request):
    """Afficher le profil utilisateur"""
    user = request.user
    
    context = {
        'title': 'Mon Profil',
        'user': user,
    }
    
    # Ajouter les informations spécifiques selon le type d'utilisateur
    if user.user_type == 'livreur':
        context['livreur_profile'] = getattr(user, 'livreur_profile', None)
    elif user.user_type == 'entreprise':
        context['entreprise_profile'] = getattr(user, 'entreprise_profile', None)
    
    return render(request, 'users/profile.html', context)

@login_required
def edit_profile(request):
    """Modifier le profil utilisateur"""
    user = request.user
    
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=user)
        
        # Formulaires spécifiques selon le type d'utilisateur
        if user.user_type == 'livreur':
            profile_form = LivreurProfileForm(request.POST, instance=getattr(user, 'livreur_profile', None))
        elif user.user_type == 'entreprise':
            profile_form = EntrepriseProfileForm(request.POST, instance=getattr(user, 'entreprise_profile', None))
        else:
            profile_form = None
        
        if user_form.is_valid() and (profile_form is None or profile_form.is_valid()):
            user_form.save()
            if profile_form:
                profile_form.save()
            
            messages.success(request, 'Profil mis à jour avec succès !')
            return redirect('users:profile')
    else:
        user_form = UserProfileForm(instance=user)
        
        if user.user_type == 'livreur':
            profile_form = LivreurProfileForm(instance=getattr(user, 'livreur_profile', None))
        elif user.user_type == 'entreprise':
            profile_form = EntrepriseProfileForm(instance=getattr(user, 'entreprise_profile', None))
        else:
            profile_form = None
    
    context = {
        'title': 'Modifier mon profil',
        'user_form': user_form,
        'profile_form': profile_form,
        'user_type': user.user_type,
    }
    
    return render(request, 'users/edit_profile.html', context)

@login_required
def simulate_location(request):
    if request.user.user_type != 'livreur':
        messages.error(request, "Seuls les livreurs peuvent simuler leur position.")
        return redirect('users:profile')

    if request.method == 'POST':
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        if latitude:
            request.user.latitude = latitude.replace(',', '.')
        if longitude:
            request.user.longitude = longitude.replace(',', '.')
            
        request.user.save()
        messages.success(request, f"Position mise à jour : {latitude}, {longitude}")
        return redirect('users:simulate_location')

    return render(request, 'users/simulate_location.html')

@login_required
def livreur_list(request):
    if request.user.user_type != 'entreprise':
        messages.error(request, "Vous n'avez pas l'autorisation d'accéder à cette page.")
        return redirect('public:home')

    livreurs = User.objects.filter(user_type='livreur').order_by('username')

    context = {
        'title': 'Livreurs Partenaires',
        'livreurs': livreurs,
    }
    return render(request, 'users/livreur_list.html', context)

# Vue login_view dupliquée supprimée - utiliser celle du début du fichier

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log pour debug
            logger.info(f"Utilisateur créé: {user.username}, Type: {user.user_type}")
            messages.success(request, f"Inscription réussie en tant que {user.get_user_type_display()}. Veuillez vous connecter.")
            return redirect('users:login')
        else:
            # Afficher les erreurs spécifiques
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            messages.error(request, "Erreur lors de l'inscription. Veuillez corriger les erreurs ci-dessous.")
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register_modern.html', {'form': form})
