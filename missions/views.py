from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import Mission, MissionTracking, MissionDocument
from .forms import MissionForm, MissionStep1Form, MissionStep2Form, MissionStep3Form, MissionStep4Form
from chat.models import Conversation
from location.utils import calculate_mission_price, geocode_address, calculate_distance

FORMS = [
    ("step1", MissionStep1Form),
    ("step2", MissionStep2Form),
    ("step3", MissionStep3Form),
    ("step4", MissionStep4Form),
]

@login_required
def select_livreur(request, mission_id, livreur_id):
    """Permet à l"entreprise de sélectionner un livreur parmi les candidats"""
    mission = get_object_or_404(Mission, id=mission_id)
    user = request.user
    if user != mission.client:
        messages.error(request, "Vous n'avez pas l'autorisation de sélectionner un livreur pour cette mission.")
        return redirect('missions:detail', mission_id=mission.id)
    candidat = mission.candidats.filter(id=livreur_id).first()
    if not candidat:
        messages.error(request, "Ce livreur n'a pas postulé à cette mission.")
        return redirect('missions:detail', mission_id=mission.id)
    if mission.livreur:
        messages.info(request, "Un livreur a déjà été sélectionné.")
        return redirect('missions:detail', mission_id=mission.id)
    mission.livreur = candidat
    mission.status = 'acceptee'
    mission.save()
    nom_livreur = candidat.get_full_name() if hasattr(candidat, 'get_full_name') and candidat.get_full_name() else candidat.username
    messages.success(request, f"Le livreur {nom_livreur} a été sélectionné.")
    return redirect('missions:detail', mission_id=mission.id)

@login_required
def postuler_mission(request, mission_id):
    """Permet à un livreur de postuler à une mission"""
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"postuler_mission appelée par {request.user.username}")
    mission = get_object_or_404(Mission, id=mission_id)
    user = request.user
    if request.method != 'POST':
        messages.error(request, 'Méthode non autorisée. Merci d’utiliser le formulaire prévu.')
        return redirect('missions:detail', mission_id=mission.id)
    if user.user_type != 'livreur':
        messages.error(request, 'Seuls les livreurs peuvent postuler à une mission.')
        return redirect('missions:detail', mission_id=mission.id)
    if mission.candidats.filter(id=user.id).exists():
        messages.info(request, 'Vous avez déjà postulé à cette mission.')
        return redirect('missions:detail', mission_id=mission.id)
    if mission.livreur:
        messages.error(request, 'Un livreur a déjà été sélectionné pour cette mission.')
        return redirect('missions:detail', mission_id=mission.id)
    logger.debug(f"Mission {mission.id} - Candidats avant: {list(mission.candidats.all())}")
    mission.candidats.add(user)
    mission.save()
    logger.debug(f"Mission {mission.id} - Candidats après: {list(mission.candidats.all())}")
    messages.success(request, 'Votre candidature a été enregistrée.')
    return redirect('missions:detail', mission_id=mission.id)

@login_required
def missions_disponibles(request):
    """Liste des missions disponibles - SEULEMENT POUR LES LIVREURS avec informations limitées"""
    # Vérifier que l'utilisateur est un livreur
    if request.user.user_type != 'livreur':
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, "Seuls les livreurs peuvent voir les missions disponibles.")
        return redirect('public:dashboard')
    
    missions = Mission.objects.filter(livreur__isnull=True, status='en_attente')
    
    # Vérifier si le livreur a déjà postulé
    user_has_applied = missions.filter(candidats=request.user).values_list('id', flat=True)
    
    return render(request, 'missions/missions_disponibles_modern.html', {
        'missions': missions,
        'user_has_applied': set(user_has_applied),
        'show_limited_info': True,  # Flag pour indiquer qu'on montre des infos limitées
    })

@login_required
def mission_list(request):
    """Liste des missions"""
    missions = Mission.objects.all().order_by('-id')
    context = {
        'title': 'Missions',
        'missions': missions,
    }
    return render(request, 'missions/mission_list.html', context)

@login_required
def create_mission(request):
    if request.user.user_type != 'entreprise':
        messages.error(request, 'Seules les entreprises peuvent créer des missions.')
        return redirect('missions:list')

    current_step = request.POST.get('current_step', 'step1')
    
    if request.method == 'POST':
        mission_data = request.session.get('mission_data', {})
        FormClass = dict(FORMS)[current_step]
        form = FormClass(request.POST, initial=mission_data)

        if form.is_valid():
            # Conversion des Decimal en float et des datetime/date en isoformat pour la session
            from decimal import Decimal
            import datetime
            cleaned = {}
            for k, v in form.cleaned_data.items():
                if isinstance(v, Decimal):
                    cleaned[k] = float(v)
                elif isinstance(v, (datetime.datetime, datetime.date)):
                    # Always store as isoformat string for session serialization
                    cleaned[k] = v.isoformat()
                else:
                    cleaned[k] = v
            mission_data.update(cleaned)
            request.session['mission_data'] = mission_data

            next_step_index = [name for name, _ in FORMS].index(current_step) + 1
            if next_step_index < len(FORMS):
                next_step_name = FORMS[next_step_index][0]
                return render(request, 'missions/create_mission_modern.html', {
                    'form': FORMS[next_step_index][1](initial=mission_data),
                    'current_step': next_step_name,
                    'step_index': next_step_index + 1,
                    'total_steps': len(FORMS),
                })
            else:
                pickup_coords = geocode_address(mission_data['pickup_address'])
                delivery_coords = geocode_address(mission_data['delivery_address'])

                if pickup_coords and delivery_coords:
                    distance = calculate_distance(
                        pickup_coords[0], pickup_coords[1],
                        delivery_coords[0], delivery_coords[1]
                    )
                    # Calculate price using the proper function signature
                    calculated_price = calculate_mission_price(
                        mission_data['pickup_address'],
                        mission_data['delivery_address'],
                        mission_data.get('package_type', 'standard'),
                        float(mission_data.get('package_weight', 1.0)),
                        mission_data.get('priority', 'normale')
                    )
                    mission_data['price'] = str(calculated_price)
                else:
                    messages.error(request, "Impossible de calculer la distance. Veuillez vérifier les adresses.")
                    return render(request, 'missions/create_mission_modern.html', {
                        'form': form,
                        'current_step': current_step,
                        'step_index': len(FORMS),
                        'total_steps': len(FORMS),
                    })

                # Nettoyer toutes les clés non attendues pour éviter toute erreur de type Mission() got unexpected keyword arguments
                allowed_fields = {f.name for f in Mission._meta.get_fields() if f.concrete and not f.many_to_many and not f.one_to_many}
                cleaned_mission_data = {k: v for k, v in mission_data.items() if k in allowed_fields}
                
                # Logique robuste pour le prix : toujours garantir qu'il y a un prix valide
                prix = cleaned_mission_data.get('price')
                prix_estime = cleaned_mission_data.get('estimated_price')
                
                if prix and prix > 0:
                    cleaned_mission_data['price'] = prix
                elif prix_estime and prix_estime > 0:
                    cleaned_mission_data['price'] = prix_estime
                else:
                    messages.error(request, "Le prix de la mission est obligatoire. Veuillez renseigner un prix estimé ou un prix.")
                    return render(request, 'missions/create_mission_modern.html', {
                        'form': FORMS[-1][1](),
                        'current_step': FORMS[-1][0],
                        'step_index': len(FORMS),
                        'total_steps': len(FORMS),
                    })
                
                mission = Mission(**cleaned_mission_data)
                mission.client = request.user
                mission.save()

                Conversation.objects.create(id=mission.id)

                MissionTracking.objects.create(
                    mission=mission,
                    status='Créée',
                    description='Mission créée par le client'
                )

                messages.success(request, 'Mission créée avec succès !')
                del request.session['mission_data']
                return redirect('missions:detail', mission_id=mission.id)
        else:
            return render(request, 'missions/create_mission_modern.html', {
                'form': form,
                'current_step': current_step,
                'step_index': [name for name, _ in FORMS].index(current_step) + 1,
                'total_steps': len(FORMS),
            })
    else:
        request.session['mission_data'] = {}
        form = FORMS[0][1]()
        return render(request, 'missions/create_mission_modern.html', {
            'form': form,
            'current_step': FORMS[0][0],
            'step_index': 1,
            'total_steps': len(FORMS),
        })

@login_required
def mission_detail(request, mission_id):
    """Détails d'une mission avec contrôles de sécurité"""
    mission = get_object_or_404(Mission, id=mission_id)
    
    user = request.user
    
    # Contrôle d'accès selon le type d'utilisateur
    is_client = (user == mission.client)
    is_assigned_livreur = (user == mission.livreur)
    is_candidate = mission.candidats.filter(id=user.id).exists()
    
    # Les entreprises voient toujours leurs missions
    # Les livreurs voient TOUTES les infos seulement s'ils sont assignés ou candidats retenus
    if user.user_type == 'entreprise' or user.user_type == 'client':
        if not is_client:
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, "Vous n'avez accès qu'à vos propres missions.")
            return redirect('missions:list')
        show_full_info = True
        show_sensitive_info = True
    elif user.user_type == 'livreur':
        if is_assigned_livreur:
            # Livreur assigné : voit toutes les infos
            show_full_info = True
            show_sensitive_info = True
        elif is_candidate:
            # Livreur candidat : voit toutes les infos seulement s'il est retenu
            show_full_info = True
            show_sensitive_info = True
        else:
            # Livreur non assigné et non candidat : pas d'accès aux détails
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, "Vous devez postuler à cette mission pour voir les détails.")
            return redirect('missions:disponibles')
    else:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, "Type d'utilisateur non autorisé.")
        return redirect('public:dashboard')

    # Vérifier si le livreur connecté a déjà postulé
    a_deja_postule = False
    if user.user_type == 'livreur':
        a_deja_postule = is_candidate

    context = {
        'title': f'Mission #{mission.id}',
        'mission': mission,
        'tracking_events': mission.tracking_events.all(),
        'documents': mission.documents.all(),
        'a_deja_postule': a_deja_postule,
        'show_sensitive_info': show_sensitive_info,
        'show_full_info': show_full_info,
        'is_client': is_client,
        'is_assigned_livreur': is_assigned_livreur,
        'is_candidate': is_candidate,
    }
    return render(request, 'missions/mission_detail_modern.html', context)


@login_required
def accept_mission(request, mission_id):
    """Accepter une mission (pour les livreurs)"""
    if request.user.user_type != 'livreur':
        messages.error(request, 'Seuls les livreurs peuvent accepter des missions.')
        return redirect('missions:list')
    mission = get_object_or_404(Mission, id=mission_id, status='en_attente')
    if hasattr(request.user, 'livreur_profile'):
        if not request.user.livreur_profile.is_available:
            messages.error(request, 'Vous n\'êtes pas disponible pour les missions.')
            return redirect('missions:list')
    mission.livreur = request.user
    mission.status = 'acceptee'
    mission.save()
    MissionTracking.objects.create(
        mission=mission,
        status='Acceptée',
        description=f'Mission acceptée par {request.user.username}'
    )
    messages.success(request, 'Mission acceptée avec succès !')
    return redirect('missions:detail', mission_id=mission.id)

@login_required
def update_status(request, mission_id):
    """Mettre à jour le statut d'une mission"""
    mission = get_object_or_404(Mission, id=mission_id)
    if request.user != mission.livreur and request.user != mission.client:
        messages.error(request, 'Vous n\'avez pas les permissions pour modifier cette mission.')
        return redirect('missions:list')
    if request.method == 'POST':
        new_status = request.POST.get('status')
        description = request.POST.get('description', '')
        if new_status in dict(Mission.STATUS_CHOICES):
            mission.status = new_status
            if new_status == 'en_cours':
                mission.pickup_time = timezone.now()
            elif new_status == 'livree':
                mission.delivery_time = timezone.now()
            mission.save()
            MissionTracking.objects.create(
                mission=mission,
                status=new_status.title(),
                description=description or f'Statut mis à jour vers {new_status}'
            )
            messages.success(request, 'Statut mis à jour avec succès !')
        else:
            messages.error(request, 'Statut invalide.')
    return redirect('missions:detail', mission_id=mission.id)

@login_required
def mission_tracking(request, mission_id):
    """Suivi en temps réel d'une mission"""
    mission = get_object_or_404(Mission, id=mission_id)
    if request.user != mission.client and request.user != mission.livreur:
        messages.error(request, 'Vous n\'avez pas accès à cette mission.')
        return redirect('missions:list')
    context = {
        'title': f'Suivi Mission #{mission.id}',
        'mission': mission,
        'tracking_events': mission.tracking_events.all(),
        'documents': mission.documents.all(),
    }
    return render(request, 'missions/mission_tracking.html', context)

@login_required
def enterprise_mission_list(request):
    if request.user.user_type != 'entreprise':
        messages.error(request, "Vous n'avez pas l'autorisation d'accéder à cette page.")
        return redirect('public:dashboard')

    missions = Mission.objects.filter(client=request.user).order_by('-created_at')

    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        missions = missions.filter(status=status_filter)

    context = {
        'title': 'Mes Missions',
        'missions': missions,
        'status_choices': Mission.STATUS_CHOICES,
        'current_status_filter': status_filter or 'all',
    }
    return render(request, 'missions/enterprise_mission_list.html', context)