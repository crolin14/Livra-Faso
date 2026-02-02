from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from datetime import timedelta
from decimal import Decimal
import json

from .models import (
    ClientProfile, Transaction, ListeCourses, ArticleCourses,
    Portefeuille, MoyenPaiement, AdresseFavorite, EstimationPrix
)
from .forms import ListeCoursesForm
from missions.models import Mission
# from rbac.decorators import require_any_role

@login_required
# @require_any_role('client')
def client_dashboard(request):
    """Dashboard principal du client"""
    client = request.user
    
    # Créer le profil client s'il n'existe pas
    client_profile, created = ClientProfile.objects.get_or_create(user=client)
    
    # Statistiques générales
    missions_stats = {
        'total_missions': Mission.objects.filter(client=client).count(),
        'missions_en_cours': Mission.objects.filter(client=client, status__in=['en_attente', 'acceptee', 'en_cours']).count(),
        'missions_completees': Mission.objects.filter(client=client, status='livree').count(),
        'missions_annulees': Mission.objects.filter(client=client, status='annulee').count(),
    }
    
    # Missions récentes
    recent_missions = Mission.objects.filter(client=client).order_by('-created_at')[:5]
    
    # Transactions récentes
    recent_transactions = Transaction.objects.filter(client=client).order_by('-created_at')[:5]
    
    # Portefeuille
    portefeuille, _ = Portefeuille.objects.get_or_create(user=client)
    
    # Listes de courses favorites
    favorite_lists = ListeCourses.objects.filter(client=client, is_favorite=True)[:3]
    
    context = {
        'client_profile': client_profile,
        'missions_stats': missions_stats,
        'recent_missions': recent_missions,
        'recent_transactions': recent_transactions,
        'portefeuille': portefeuille,
        'favorite_lists': favorite_lists,
    }
    
    return render(request, 'client_dashboard/dashboard.html', context)

@login_required
# @require_any_role('client')
def mes_livraisons(request):
    """Liste des livraisons du client avec sections : Envoi colis, Courses, Expédition"""
    client = request.user
    status_filter = request.GET.get('status', 'all')
    section = request.GET.get('section', 'envoi-colis')
    
    # Récupérer les missions (envois de colis)
    missions = Mission.objects.filter(client=client)
    
    if status_filter != 'all':
        missions = missions.filter(status=status_filter)
    
    missions = missions.order_by('-created_at')
    
    # Pagination pour les missions
    paginator = Paginator(missions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Récupérer les listes de courses
    listes_courses = ListeCourses.objects.filter(client=client).order_by('-updated_at')[:12]
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'status_choices': Mission.STATUS_CHOICES,
        'listes_courses': listes_courses,
        'current_section': section,
    }
    
    return render(request, 'client_dashboard/mes_livraisons.html', context)

@login_required
# @require_any_role('client')
def nouvelle_livraison(request):
    """Créer une nouvelle livraison"""
    client_profile, created = ClientProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            pickup_address = request.POST.get('pickup_address', '').strip()
            delivery_address = request.POST.get('delivery_address', '').strip()
            estimated_price = request.POST.get('estimated_price', 0)
            priority = request.POST.get('priority', 'normal')
            
            # Validation basique
            if not all([title, pickup_address, delivery_address]):
                messages.error(request, 'Veuillez remplir tous les champs obligatoires.')
                return redirect('client_dashboard:nouvelle_livraison')
            
            # Gérer correctement la logique du prix : toujours fournir price (pas NULL)
            valeur_prix = float(request.POST.get('price') or estimated_price or 0)
            if valeur_prix <= 0:
                messages.error(request, "Le prix estimé ou calculé est obligatoire.")
                return redirect('client_dashboard:nouvelle_livraison')

            mission = Mission.objects.create(
                client=request.user,
                title=title,
                description=description,
                pickup_address=pickup_address,
                delivery_address=delivery_address,
                estimated_price=float(estimated_price) if estimated_price else 0,
                price=valeur_prix,
                priority=priority,
                status='pending',  # En attente d'un livreur
            )
            
            if request.content_type == 'application/json':
                return JsonResponse({
                    'success': True,
                    'mission_id': mission.id,
                    'message': 'Mission créée avec succès!'
                })
            else:
                messages.success(request, 'Mission créée avec succès!')
                return redirect('client_dashboard:mes_livraisons')
                
        except Exception as e:
            if request.content_type == 'application/json':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })
            else:
                messages.error(request, f'Erreur lors de la création: {str(e)}')
    
    # Récupérer les données pour le formulaire
    adresses_favorites = AdresseFavorite.objects.filter(client=request.user)
    moyens_paiement = MoyenPaiement.objects.filter(client=request.user, is_active=True)
    
    context = {
        'adresses_favorites': adresses_favorites,
        'moyens_paiement': moyens_paiement,
    }
    
    return render(request, 'client_dashboard/nouvelle_livraison.html', context)

@login_required
def faire_courses(request):
    """Interface pour faire ses courses"""
    client_profile, created = ClientProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = ListeCoursesForm(request.POST)
        if form.is_valid():
            liste = form.save(commit=False)
            liste.client = request.user
            liste.save()
            messages.success(request, f'Liste "{liste.nom}" créée avec succès!')
            return redirect('client_dashboard:detail_liste_courses', liste_id=liste.id)
    else:
        form = ListeCoursesForm()

    # Récupérer les listes existantes
    mes_listes = ListeCourses.objects.filter(client=request.user).order_by('-updated_at')
    listes_templates = ListeCourses.objects.filter(client=request.user, is_template=True)
    
    # Récupérer les listes de la semaine (7 derniers jours)
    date_limite = timezone.now() - timedelta(days=7)
    listes_semaine = mes_listes.filter(created_at__gte=date_limite)
    
    context = {
        'form': form,
        'mes_listes': mes_listes,
        'listes_templates': listes_templates,
        'listes_semaine': listes_semaine,
    }
    
    return render(request, 'client_dashboard/faire_courses.html', context)

@login_required
# @require_any_role('client')
def detail_liste_courses(request, liste_id):
    """Détail d'une liste de courses"""
    liste = get_object_or_404(ListeCourses, id=liste_id, client=request.user)
    
    if request.method == 'POST':
        # Ajouter un article
        nom = request.POST.get('nom')
        quantite = request.POST.get('quantite', '1')
        prix_estime = request.POST.get('prix_estime')
        notes = request.POST.get('notes', '')
        
        ArticleCourses.objects.create(
            liste=liste,
            nom=nom,
            quantite=quantite,
            prix_estime=Decimal(prix_estime) if prix_estime else None,
            notes=notes
        )
        
        messages.success(request, f'Article "{nom}" ajouté!')
        return redirect('client_dashboard:detail_liste_courses', liste_id=liste.id)
    
    articles = liste.articles.all()
    
    context = {
        'liste': liste,
        'articles': articles,
    }
    
    return render(request, 'client_dashboard/detail_liste_courses.html', context)

@login_required
# @require_any_role('client')
def historique_recu(request):
    """Historique des transactions et reçus"""
    client = request.user
    
    transactions = Transaction.objects.filter(client=client).order_by('-created_at')
    
    # Filtres
    status_filter = request.GET.get('status')
    if status_filter:
        transactions = transactions.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(transactions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiques
    stats = {
        'total_depense': transactions.filter(status='completed').aggregate(
            total=Sum('amount'))['total'] or 0,
        'nb_transactions': transactions.count(),
        'moyenne_transaction': transactions.filter(status='completed').aggregate(
            avg=Sum('amount'))['avg'] or 0,
    }
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'status_choices': Transaction.STATUS_CHOICES,
        'stats': stats,
    }
    
    return render(request, 'client_dashboard/historique_recu.html', context)

@login_required
# @require_any_role('client')
def mon_profil(request):
    """Gestion du profil client"""
    client = request.user
    client_profile, _ = ClientProfile.objects.get_or_create(user=client)
    portefeuille, _ = Portefeuille.objects.get_or_create(client=client)
    
    if request.method == 'POST':
        # Mise à jour du profil
        client.first_name = request.POST.get('first_name', client.first_name)
        client.last_name = request.POST.get('last_name', client.last_name)
        client.email = request.POST.get('email', client.email)
        client.phone_number = request.POST.get('phone_number', client.phone_number)
        client.save()
        
        client_profile.default_payment_method = request.POST.get('default_payment_method', 
                                                               client_profile.default_payment_method)
        client_profile.save()
        
        messages.success(request, 'Profil mis à jour avec succès!')
        return redirect('client_dashboard:mon_profil')
    
    # Adresses et moyens de paiement
    adresses = AdresseFavorite.objects.filter(client=request.user)
    moyens_paiement = MoyenPaiement.objects.filter(client=request.user)
    
    context = {
        'client_profile': client_profile,
        'portefeuille': portefeuille,
        'adresses': adresses,
        'moyens_paiement': moyens_paiement,
    }
    
    return render(request, 'client_dashboard/mon_profil.html', context)

@login_required
# @require_any_role('client')
@require_http_methods(["POST"])
def estimation_prix(request):
    """API pour estimer le prix d'une livraison"""
    try:
        data = json.loads(request.body)
        
        # Logique d'estimation simplifiée
        # Dans un vrai projet, cela utiliserait des APIs de géolocalisation
        distance_base = 5  # km par défaut
        prix_base = 1000  # FCFA
        
        # Facteurs de prix
        facteurs = {
            'normale': 1.0,
            'urgente': 1.5,
            'express': 2.0,
        }
        
        type_colis_facteurs = {
            'document': 0.8,
            'colis_petit': 1.0,
            'colis_moyen': 1.3,
            'colis_volumineux': 1.8,
            'nourriture': 1.2,
            'medicament': 1.4,
        }
        
        priorite = data.get('priority', 'normale')
        type_colis = data.get('package_type', 'colis_petit')
        
        prix_estime = prix_base * facteurs.get(priorite, 1.0) * type_colis_facteurs.get(type_colis, 1.0)
        
        # Délai estimé en minutes
        delai_base = {
            'normale': 240,  # 4h
            'urgente': 120,  # 2h
            'express': 60,   # 1h
        }
        
        delai_estime = delai_base.get(priorite, 240)
        
        # Sauvegarder l'estimation
        estimation = EstimationPrix.objects.create(
            client=request.user,
            adresse_depart=data.get('pickup_address', ''),
            adresse_arrivee=data.get('delivery_address', ''),
            type_colis=type_colis,
            priorite=priorite,
            distance_km=distance_base,
            prix_estime=prix_estime,
            delai_estime=delai_estime
        )
        
        return JsonResponse({
            'success': True,
            'prix_estime': round(prix_estime),
            'delai_estime': delai_estime,
            'distance_km': distance_base,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
# @require_any_role('client')
@require_http_methods(["POST"])
def ajouter_adresse(request):
    """Ajouter une adresse favorite"""
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        
        client_profile, created = ClientProfile.objects.get_or_create(user=request.user)
        
        adresse = AdresseFavorite.objects.create(
            client=request.user,
            nom=data.get('nom'),
            type_adresse=data.get('type_adresse', 'autre'),
            adresse_complete=data.get('adresse_complete'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            instructions=data.get('instructions', ''),
            is_default=data.get('is_default', False)
        )
        
        if request.content_type == 'application/json':
            return JsonResponse({
                'success': True,
                'adresse_id': adresse.id,
                'message': 'Adresse ajoutée avec succès!'
            })
        else:
            messages.success(request, 'Adresse ajoutée avec succès!')
            return redirect('client_dashboard:mon_profil')
            
    except Exception as e:
        if request.content_type == 'application/json':
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        else:
            messages.error(request, f'Erreur: {str(e)}')
            return redirect('client_dashboard:mon_profil')

@login_required
# @require_any_role('client')
@require_http_methods(["POST"])
def ajouter_moyen_paiement(request):
    """Ajouter un moyen de paiement"""
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        
        client_profile, created = ClientProfile.objects.get_or_create(user=request.user)
        
        moyen = MoyenPaiement.objects.create(
            client=request.user,
            type_paiement=data.get('type_paiement'),
            nom_affiche=data.get('nom_affiche'),
            numero_masque=data.get('numero_masque'),
            is_default=data.get('is_default', False)
        )
        
        if request.content_type == 'application/json':
            return JsonResponse({
                'success': True,
                'moyen_id': moyen.id,
                'message': 'Moyen de paiement ajouté!'
            })
        else:
            messages.success(request, 'Moyen de paiement ajouté!')
            return redirect('client_dashboard:mon_profil')
            
    except Exception as e:
        if request.content_type == 'application/json':
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        else:
            messages.error(request, f'Erreur: {str(e)}')
            return redirect('client_dashboard:mon_profil')

@login_required
# @require_any_role('client')
def suivi_mission(request, mission_id):
    """Suivi détaillé d'une mission"""
    mission = get_object_or_404(Mission, id=mission_id, client=request.user)
    
    # Récupérer les événements de suivi depuis MissionTracking
    from missions.models import MissionTracking
    tracking_events = list(MissionTracking.objects.filter(mission=mission).order_by('timestamp'))
    
    # Si aucun événement, créer un événement initial
    if not tracking_events:
        # Créer un événement initial pour la création
        initial_event = type('Event', (), {
            'status': 'created',
            'timestamp': mission.created_at,
            'description': 'Mission créée',
            'location': '',
            'icon': 'plus-circle'
        })()
        tracking_events = [initial_event]
        
        # Ajouter un événement pour le statut actuel si différent de "en_attente"
        if mission.status != 'en_attente':
            status_event = type('Event', (), {
                'status': mission.status,
                'timestamp': mission.updated_at,
                'description': f'Mission {mission.get_status_display().lower()}',
                'location': '',
                'icon': 'check-circle' if mission.status == 'livree' else 'clock'
            })()
            tracking_events.append(status_event)
    
    context = {
        'mission': mission,
        'tracking_events': tracking_events,
    }
    
    return render(request, 'client_dashboard/suivi_mission.html', context)

@login_required
# @require_any_role('client')
def detail_mission(request, mission_id):
    """Détails complets d'une mission"""
    mission = get_object_or_404(Mission, id=mission_id, client=request.user)
    
    # Récupérer les documents associés
    from missions.models import MissionDocument
    documents = MissionDocument.objects.filter(mission=mission)
    
    # Récupérer les événements de suivi
    from missions.models import MissionTracking
    tracking_events = MissionTracking.objects.filter(mission=mission).order_by('-timestamp')[:10]
    
    context = {
        'mission': mission,
        'documents': documents,
        'tracking_events': tracking_events,
    }
    
    return render(request, 'client_dashboard/detail_mission.html', context)

@login_required
# @require_any_role('client')
@require_http_methods(["POST"])
def annuler_mission(request, mission_id):
    """Annuler une mission"""
    mission = get_object_or_404(Mission, id=mission_id, client=request.user)
    
    # Vérifier que la mission peut être annulée
    if mission.status not in ['en_attente', 'acceptee']:
        messages.error(request, 'Cette mission ne peut plus être annulée.')
        return redirect('client_dashboard:detail_mission', mission_id=mission_id)
    
    try:
        mission.status = 'annulee'
        mission.save()
        
        # Créer un événement de suivi
        from missions.models import MissionTracking
        MissionTracking.objects.create(
            mission=mission,
            status='Annulée',
            description='Mission annulée par le client',
            location=''
        )
        
        messages.success(request, 'Mission annulée avec succès.')
        
        if request.content_type == 'application/json':
            return JsonResponse({
                'success': True,
                'message': 'Mission annulée avec succès'
            })
        else:
            return redirect('client_dashboard:mes_livraisons')
            
    except Exception as e:
        if request.content_type == 'application/json':
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
        else:
            messages.error(request, f'Erreur lors de l\'annulation: {str(e)}')
            return redirect('client_dashboard:detail_mission', mission_id=mission_id)
