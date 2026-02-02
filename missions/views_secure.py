"""
Vues sécurisées pour les missions avec validation renforcée
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from .models import Mission, MissionTracking, MissionDocument
from .forms import MissionForm, MissionStep1Form, MissionStep2Form, MissionStep3Form, MissionStep4Form
from chat.models import Conversation
from location.utils import calculate_mission_price, geocode_address, calculate_distance

logger = logging.getLogger(__name__)

FORMS = [
    ("step1", MissionStep1Form),
    ("step2", MissionStep2Form),
    ("step3", MissionStep3Form),
    ("step4", MissionStep4Form),
]

@login_required
@csrf_protect
@require_http_methods(["POST"])
def select_livreur(request, mission_id, livreur_id):
    """Permet à l'entreprise de sélectionner un livreur parmi les candidats"""
    try:
        with transaction.atomic():
            mission = get_object_or_404(Mission, id=mission_id)
            
            # Vérification des permissions
            if request.user != mission.client:
                logger.warning(f"Tentative non autorisée de sélection livreur par {request.user.id} pour mission {mission_id}")
                raise PermissionDenied("Vous n'avez pas l'autorisation de sélectionner un livreur pour cette mission.")
            
            # Validation du candidat
            candidat = mission.candidats.filter(id=livreur_id).first()
            if not candidat:
                messages.error(request, "Ce livreur n'a pas postulé à cette mission.")
                return redirect('missions:detail', mission_id=mission.id)
            
            # Vérification qu'aucun livreur n'est déjà sélectionné
            if mission.livreur:
                messages.info(request, "Un livreur a déjà été sélectionné.")
                return redirect('missions:detail', mission_id=mission.id)
            
            # Sélection du livreur
            mission.livreur = candidat
            mission.status = 'acceptee'
            mission.save()
            
            # Log de sécurité
            logger.info(f"Livreur {candidat.id} sélectionné pour mission {mission.id} par {request.user.id}")
            
            nom_livreur = candidat.get_full_name() if hasattr(candidat, 'get_full_name') and candidat.get_full_name() else candidat.username
            messages.success(request, f"Le livreur {nom_livreur} a été sélectionné.")
            return redirect('missions:detail', mission_id=mission.id)
            
    except PermissionDenied:
        messages.error(request, "Accès non autorisé.")
        return redirect('missions:list')
    except Exception as e:
        logger.error(f"Erreur lors de la sélection du livreur: {e}")
        messages.error(request, "Une erreur est survenue lors de la sélection.")
        return redirect('missions:detail', mission_id=mission_id)

@login_required
@csrf_protect
@require_http_methods(["POST"])
def postuler_mission(request, mission_id):
    """Permet à un livreur de postuler à une mission"""
    try:
        with transaction.atomic():
            logger.debug(f"postuler_mission appelée par {request.user.username}")
            mission = get_object_or_404(Mission, id=mission_id)
            user = request.user
            
            # Validation du type d'utilisateur
            if user.user_type != 'livreur':
                logger.warning(f"Tentative de candidature non-livreur par {user.id}")
                messages.error(request, 'Seuls les livreurs peuvent postuler à une mission.')
                return redirect('missions:detail', mission_id=mission.id)
            
            # Vérification de candidature existante
            if mission.candidats.filter(id=user.id).exists():
                messages.info(request, 'Vous avez déjà postulé à cette mission.')
                return redirect('missions:detail', mission_id=mission.id)
            
            # Vérification que la mission est disponible
            if mission.livreur:
                messages.error(request, 'Un livreur a déjà été sélectionné pour cette mission.')
                return redirect('missions:detail', mission_id=mission.id)
            
            if mission.status != 'en_attente':
                messages.error(request, 'Cette mission n\'est plus disponible.')
                return redirect('missions:detail', mission_id=mission.id)
            
            # Ajout de la candidature
            logger.debug(f"Mission {mission.id} - Candidats avant: {list(mission.candidats.all())}")
            mission.candidats.add(user)
            mission.save()
            logger.debug(f"Mission {mission.id} - Candidats après: {list(mission.candidats.all())}")
                
            # Log de sécurité
            logger.info(f"Candidature enregistrée: livreur {user.id} pour mission {mission.id}")
            
            messages.success(request, 'Votre candidature a été enregistrée.')
            return redirect('missions:detail', mission_id=mission.id)
            
    except Exception as e:
        logger.error(f"Erreur lors de la candidature: {e}")
        messages.error(request, "Une erreur est survenue lors de votre candidature.")
        return redirect('missions:detail', mission_id=mission_id)

@login_required
def missions_disponibles(request):
    """Liste des missions disponibles avec pagination et filtres - SEULEMENT POUR LES LIVREURS"""
    try:
        # Vérifier que l'utilisateur est un livreur
        if request.user.user_type != 'livreur':
            messages.error(request, "Seuls les livreurs peuvent voir les missions disponibles.")
            return redirect('public:dashboard')
        
        # Base queryset avec optimisation - seulement missions sans livreur assigné
        missions = Mission.objects.select_related('client').prefetch_related('candidats').filter(
            livreur__isnull=True, 
            status='en_attente'
        )
        
        # Vérifier si le livreur a déjà postulé à certaines missions
        user_has_applied = missions.filter(candidats=request.user).values_list('id', flat=True)
        
        # Filtres de recherche sécurisés (seulement sur titre et zones générales, pas d'adresses complètes)
        search = request.GET.get('search', '').strip()
        if search:
            # Validation de la recherche pour éviter les injections
            if len(search) > 100:
                messages.warning(request, "Terme de recherche trop long.")
                search = search[:100]
            
            missions = missions.filter(
                Q(title__icontains=search)
            )
        
        # Filtre par prix
        prix_min = request.GET.get('prix_min')
        prix_max = request.GET.get('prix_max')
        
        if prix_min:
            try:
                prix_min = float(prix_min)
                missions = missions.filter(price__gte=prix_min)
            except ValueError:
                messages.warning(request, "Prix minimum invalide.")
        
        if prix_max:
            try:
                prix_max = float(prix_max)
                missions = missions.filter(price__lte=prix_max)
            except ValueError:
                messages.warning(request, "Prix maximum invalide.")
        
        # Pagination sécurisée
        page_number = request.GET.get('page', 1)
        try:
            page_number = int(page_number)
            if page_number < 1:
                page_number = 1
        except ValueError:
            page_number = 1
        
        paginator = Paginator(missions, 10)  # 10 missions par page
        page_obj = paginator.get_page(page_number)
        
        context = {
            'missions': page_obj,
            'search': search,
            'prix_min': prix_min,
            'prix_max': prix_max,
            'user_has_applied': set(user_has_applied),
            'show_limited_info': True,  # Flag pour indiquer qu'on montre des infos limitées
        }
        
        return render(request, 'missions/missions_disponibles.html', context)
        
    except Exception as e:
        logger.error(f"Erreur lors du chargement des missions disponibles: {e}")
        messages.error(request, "Erreur lors du chargement des missions.")
        return render(request, 'missions/missions_disponibles.html', {'missions': []})

@login_required
def mission_list(request):
    """Liste des missions de l'utilisateur avec sécurité renforcée - CHAQUE UTILISATEUR VOIT SEULEMENT SES MISSIONS"""
    try:
        user = request.user
        
        # Requêtes optimisées selon le type d'utilisateur - FILTRAGE STRICT
        if user.user_type == 'entreprise':
            # Entreprises : seulement leurs missions créées
            missions = Mission.objects.select_related('livreur').prefetch_related('candidats').filter(
                client=user
            ).order_by('-created_at')
        elif user.user_type == 'livreur':
            # Livreurs : seulement les missions où ils sont assignés OU candidats
            missions = Mission.objects.select_related('client').filter(
                Q(livreur=user) | Q(candidats=user)
            ).distinct().order_by('-created_at')
        elif user.user_type == 'client':
            # Clients : seulement leurs missions créées
            missions = Mission.objects.select_related('livreur').prefetch_related('candidats').filter(
                client=user
            ).order_by('-created_at')
        else:
            logger.warning(f"Type d'utilisateur non reconnu: {user.user_type}")
            missions = Mission.objects.none()
        
        # Filtres sécurisés
        status_filter = request.GET.get('status')
        if status_filter and status_filter in dict(Mission.STATUS_CHOICES):
            missions = missions.filter(status=status_filter)
        
        # Pagination
        page_number = request.GET.get('page', 1)
        try:
            page_number = int(page_number)
            if page_number < 1:
                page_number = 1
        except ValueError:
            page_number = 1
        
        paginator = Paginator(missions, 15)
        page_obj = paginator.get_page(page_number)
        
        # Statistiques pour l'utilisateur
        stats = {
            'total': missions.count(),
            'en_attente': missions.filter(status='en_attente').count(),
            'en_cours': missions.filter(status='en_cours').count(),
            'terminees': missions.filter(status='terminee').count(),
        }
        
        context = {
            'missions': page_obj,
            'stats': stats,
            'status_choices': Mission.STATUS_CHOICES,
            'current_status': status_filter,
        }
        
        return render(request, 'missions/mission_list.html', context)
        
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la liste des missions: {e}")
        messages.error(request, "Erreur lors du chargement de vos missions.")
        return render(request, 'missions/mission_list.html', {'missions': []})

@login_required
def mission_detail(request, mission_id):
    """Détail d'une mission avec contrôles de sécurité"""
    try:
        mission = get_object_or_404(
            Mission.objects.select_related('client', 'livreur').prefetch_related('candidats'),
            id=mission_id
        )
        
        user = request.user
        
        # Contrôle d'accès selon le type d'utilisateur
        is_client = (user == mission.client)
        is_assigned_livreur = (user == mission.livreur)
        is_candidate = mission.candidats.filter(id=user.id).exists()
        
        # Les entreprises voient toujours leurs missions
        # Les livreurs voient TOUTES les infos seulement s'ils sont assignés ou candidats retenus
        if user.user_type == 'entreprise':
            if not is_client:
                logger.warning(f"Tentative d'accès non autorisé à la mission {mission_id} par entreprise {user.id}")
                raise PermissionDenied("Vous n'avez accès qu'à vos propres missions.")
            show_full_info = True
        elif user.user_type == 'livreur':
            if is_assigned_livreur:
                # Livreur assigné : voit toutes les infos
                show_full_info = True
            elif is_candidate:
                # Livreur candidat : voit toutes les infos seulement s'il est retenu
                # Pour l'instant, on considère qu'un candidat peut voir les infos
                # (vous pouvez ajuster selon votre logique métier)
                show_full_info = True
            else:
                # Livreur non assigné et non candidat : pas d'accès aux détails
                logger.warning(f"Tentative d'accès non autorisé à la mission {mission_id} par livreur {user.id}")
                raise PermissionDenied("Vous devez postuler à cette mission pour voir les détails.")
        else:
            raise PermissionDenied("Type d'utilisateur non autorisé.")
        
        # Données contextuelles sécurisées
        context = {
            'mission': mission,
            'show_full_info': show_full_info,
            'is_client': is_client,
            'is_assigned_livreur': is_assigned_livreur,
            'is_candidate': is_candidate,
            'can_edit': is_client and mission.status == 'en_attente',
            'can_apply': (
                user.user_type == 'livreur' and 
                not mission.livreur and 
                not is_candidate and
                mission.status == 'en_attente'
            ),
            'can_select_livreur': (
                is_client and 
                not mission.livreur and 
                mission.candidats.exists()
            ),
        }
        
        return render(request, 'missions/mission_detail.html', context)
        
    except PermissionDenied:
        messages.error(request, "Accès non autorisé à cette mission.")
        return redirect('missions:list')
    except Exception as e:
        logger.error(f"Erreur lors du chargement du détail de la mission: {e}")
        messages.error(request, "Erreur lors du chargement de la mission.")
        return redirect('missions:list')

@login_required
@csrf_protect
def create_mission(request):
    """Création de mission sécurisée avec validation renforcée"""
    if request.user.user_type != 'entreprise':
        logger.warning(f"Tentative de création de mission par non-entreprise: {request.user.id}")
        messages.error(request, "Seules les entreprises peuvent créer des missions.")
        return redirect('public:dashboard')
    
    try:
        if request.method == 'POST':
            with transaction.atomic():
                form = MissionForm(request.POST, request.FILES)
                if form.is_valid():
                    mission = form.save(commit=False)
                    mission.client = request.user

                    # Logique robuste pour le prix : toujours garantir qu'il y a un prix valide
                    prix = form.cleaned_data.get('price')
                    prix_estime = form.cleaned_data.get('estimated_price')
                    
                    # Priorité : price explicite > estimated_price > erreur
                    if prix and prix > 0:
                        mission.price = prix
                    elif prix_estime and prix_estime > 0:
                        mission.price = prix_estime
                    else:
                        messages.error(request, "Le prix de la mission est obligatoire. Veuillez renseigner un prix estimé ou un prix.")
                        return render(request, 'missions/create_mission.html', {'form': form})
                    
                    # Validation supplémentaire
                    if mission.price <= 0:
                        messages.error(request, "Le prix doit être supérieur à zéro.")
                        return render(request, 'missions/create_mission.html', {'form': form})
                    
                    # Géocodage sécurisé
                    pickup_coords = geocode_address(mission.pickup_address)
                    delivery_coords = geocode_address(mission.delivery_address)
                    
                    if pickup_coords:
                        mission.pickup_latitude = pickup_coords['latitude']
                        mission.pickup_longitude = pickup_coords['longitude']
                    
                    if delivery_coords:
                        mission.delivery_latitude = delivery_coords['latitude']
                        mission.delivery_longitude = delivery_coords['longitude']
                    
                    mission.save()
                    
                    logger.info(f"Mission créée: {mission.id} par {request.user.id}")
                    messages.success(request, "Mission créée avec succès!")
                    return redirect('missions:detail', mission_id=mission.id)
                else:
                    logger.warning(f"Formulaire de mission invalide: {form.errors}")
        else:
            form = MissionForm()
        
        return render(request, 'missions/create_mission.html', {'form': form})
        
    except Exception as e:
        logger.error(f"Erreur lors de la création de mission: {e}")
        messages.error(request, "Erreur lors de la création de la mission.")
        return redirect('public:dashboard')
