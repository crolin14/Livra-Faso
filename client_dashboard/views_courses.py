"""
Vues pour le module "Faire mes courses" - Version 1.0
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from datetime import timedelta
from decimal import Decimal
import json

from .models import (
    MissionCourses, EtapeMission, ArticleCourseMission, 
    ValidationEtape, Transaction, Portefeuille
)
from .forms import (
    MissionCoursesForm, EtapeMissionForm, ArticleCourseMissionForm,
    ArticleCourseMissionFormSet
)

try:
    from location.utils import calculate_distance, geocode_address
except ImportError:
    # Fallback si location.utils n'existe pas
    def calculate_distance(lat1, lon1, lat2, lon2):
        """Calcul simple de distance"""
        from math import radians, cos, sin, asin, sqrt
        R = 6371.0
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return R * c
    
    def geocode_address(address):
        """Géocodage simple"""
        default_coords = {
            'ouagadougou': (12.3714, -1.5197),
            'bobo-dioulasso': (11.1781, -4.2967),
            'koudougou': (12.2530, -2.3621),
        }
        address_lower = address.lower() if address else ''
        for city, coords in default_coords.items():
            if city in address_lower:
                return coords
        return default_coords['ouagadougou']

logger = logging.getLogger(__name__)


@login_required
def creer_mission_courses(request):
    """Créer une mission de courses - Wizard multi-étapes"""
    if request.user.user_type != 'client':
        messages.error(request, "Seuls les clients peuvent créer des missions de courses.")
        return redirect('public:dashboard')
    
    # Étape actuelle du wizard
    step = request.GET.get('step', '1')
    
    if request.method == 'POST':
        if step == '1':
            # Étape 1 : Informations générales + Délai
            form = MissionCoursesForm(request.POST)
            if form.is_valid():
                mission = form.save(commit=False)
                mission.client = request.user
                mission.status = 'creee'
                mission.save()
                
                # Stocker l'ID de la mission en session pour les étapes suivantes
                request.session['mission_courses_id'] = mission.id
                return redirect('client_dashboard:creer_mission_courses?step=2')
        elif step == '2':
            # Étape 2 : Ajouter les étapes
            mission_id = request.session.get('mission_courses_id')
            if not mission_id:
                messages.error(request, "Session expirée. Veuillez recommencer.")
                return redirect('client_dashboard:creer_mission_courses')
            
            mission = get_object_or_404(MissionCourses, id=mission_id, client=request.user)
            
            # Traitement des étapes envoyées via JSON
            try:
                etapes_data = json.loads(request.POST.get('etapes', '[]'))
                
                with transaction.atomic():
                    for idx, etape_data in enumerate(etapes_data, start=1):
                        etape = EtapeMission.objects.create(
                            mission=mission,
                            numero_ordre=idx,
                            type_etape=etape_data.get('type_etape'),
                            adresse=etape_data.get('adresse'),
                            instructions=etape_data.get('instructions', ''),
                            action_requise=etape_data.get('action_requise', ''),
                            montant_requis=etape_data.get('montant_requis') or None
                        )
                        
                        # Géocodage de l'adresse
                        coords = geocode_address(etape.adresse)
                        if coords:
                            etape.latitude = coords[0]  # latitude
                            etape.longitude = coords[1]  # longitude
                            etape.save()
                        
                        # Ajouter les articles de cette étape
                        articles = etape_data.get('articles', [])
                        for article_data in articles:
                            ArticleCourseMission.objects.create(
                                etape=etape,
                                nom=article_data.get('nom'),
                                quantite=article_data.get('quantite', '1'),
                                prix_estime=article_data.get('prix_estime') or None,
                                prix_max_accepte=article_data.get('prix_max_accepte') or None,
                                substitution_autorisee=article_data.get('substitution_autorisee', False),
                                commentaire=article_data.get('commentaire', '')
                            )
                
                return redirect('client_dashboard:creer_mission_courses?step=3')
            except Exception as e:
                logger.error(f"Erreur lors de la création des étapes: {e}")
                messages.error(request, f"Erreur lors de la création des étapes: {str(e)}")
        elif step == '3':
            # Étape 3 : Calcul du prix et paiement
            mission_id = request.session.get('mission_courses_id')
            if not mission_id:
                messages.error(request, "Session expirée. Veuillez recommencer.")
                return redirect('client_dashboard:creer_mission_courses')
            
            mission = get_object_or_404(MissionCourses, id=mission_id, client=request.user)
            
        # Calculer la distance totale
        etapes = list(mission.etapes.all().order_by('numero_ordre'))
        distance_totale = Decimal('0')
        
        if len(etapes) > 1:
            for i in range(len(etapes) - 1):
                etape_actuelle = etapes[i]
                etape_suivante = etapes[i + 1]
                
                # Géocoder si pas encore fait
                if not etape_actuelle.latitude:
                    coords = geocode_address(etape_actuelle.adresse)
                    if coords:
                        etape_actuelle.latitude = coords[0]
                        etape_actuelle.longitude = coords[1]
                        etape_actuelle.save()
                
                if not etape_suivante.latitude:
                    coords = geocode_address(etape_suivante.adresse)
                    if coords:
                        etape_suivante.latitude = coords[0]
                        etape_suivante.longitude = coords[1]
                        etape_suivante.save()
                
                if etape_actuelle.latitude and etape_actuelle.longitude and \
                   etape_suivante.latitude and etape_suivante.longitude:
                    dist = calculate_distance(
                        float(etape_actuelle.latitude), float(etape_actuelle.longitude),
                        float(etape_suivante.latitude), float(etape_suivante.longitude)
                    )
                    if dist:
                        distance_totale += Decimal(str(dist))
            
            mission.distance_totale_km = distance_totale
            mission.calculer_prix_total()
            mission.save()
            
            # Calculer le montant total des courses
            montant_total_courses = Decimal('0')
            for etape in etapes:
                for article in etape.articles.all():
                    if article.prix_max_accepte:
                        montant_total_courses += article.prix_max_accepte
                    elif article.prix_estime:
                        montant_total_courses += article.prix_estime
            
            mission.montant_courses = montant_total_courses
            mission.save()
            
            # Rediriger vers la page de paiement
            return redirect('client_dashboard:paiement_mission_courses', mission_id=mission.id)
    
    # GET - Afficher le formulaire selon l'étape
    if step == '1':
        form = MissionCoursesForm()
        return render(request, 'client_dashboard/creer_mission_courses_etape1.html', {
            'form': form,
            'step': 1
        })
    elif step == '2':
        mission_id = request.session.get('mission_courses_id')
        if not mission_id:
            messages.error(request, "Veuillez d'abord remplir les informations générales.")
            return redirect('client_dashboard:creer_mission_courses?step=1')
        
        mission = get_object_or_404(MissionCourses, id=mission_id, client=request.user)
        return render(request, 'client_dashboard/creer_mission_courses_etape2.html', {
            'mission': mission,
            'step': 2
        })
    elif step == '3':
        mission_id = request.session.get('mission_courses_id')
        if not mission_id:
            messages.error(request, "Veuillez d'abord créer les étapes.")
            return redirect('client_dashboard:creer_mission_courses?step=2')
        
        mission = get_object_or_404(MissionCourses, id=mission_id, client=request.user)
        mission.calculer_prix_total()
        
        return render(request, 'client_dashboard/creer_mission_courses_etape3.html', {
            'mission': mission,
            'step': 3
        })
    else:
        return redirect('client_dashboard:creer_mission_courses?step=1')


@login_required
@csrf_protect
@require_http_methods(["POST"])
def calculer_prix_courses(request):
    """API pour calculer le prix d'une mission de courses"""
    try:
        data = json.loads(request.body)
        adresses = data.get('adresses', [])
        delai_type = data.get('delai_type', 'duree_max_minutes')
        duree_max_minutes = data.get('duree_max_minutes')
        heure_limite = data.get('heure_limite')
        
        if len(adresses) < 2:
            return JsonResponse({
                'success': False,
                'error': 'Au moins 2 adresses sont requises'
            }, status=400)
        
        # Calculer la distance totale
        distance_totale = Decimal('0')
        for i in range(len(adresses) - 1):
            coords1 = geocode_address(adresses[i])
            coords2 = geocode_address(adresses[i + 1])
            
            if coords1 and coords2:
                dist = calculate_distance(
                    coords1[0], coords1[1],  # latitude, longitude
                    coords2[0], coords2[1]   # latitude, longitude
                )
                if dist:
                    distance_totale += Decimal(str(dist))
        
        # Calculer le prix
        tarif_km = Decimal('500.00')
        frais_service = Decimal('1000.00')
        prix_base = distance_totale * tarif_km + frais_service
        
        # Surcharge urgence
        surcharge = Decimal('0.00')
        if delai_type == 'duree_max_minutes' and duree_max_minutes:
            if duree_max_minutes <= 60:
                surcharge = prix_base * Decimal('0.5')
            elif duree_max_minutes <= 120:
                surcharge = prix_base * Decimal('0.25')
        
        prix_total = prix_base + surcharge
        
        return JsonResponse({
            'success': True,
            'distance_km': float(distance_totale),
            'prix_base': float(prix_base),
            'surcharge_urgence': float(surcharge),
            'prix_total': float(prix_total)
        })
        
    except Exception as e:
        logger.error(f"Erreur calcul prix: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def paiement_mission_courses(request, mission_id):
    """Page de paiement pour une mission de courses"""
    mission = get_object_or_404(MissionCourses, id=mission_id, client=request.user)
    
    if mission.paiement_effectue:
        messages.info(request, "Cette mission est déjà payée.")
        return redirect('client_dashboard:detail_mission_courses', mission_id=mission.id)
    
    if mission.status != 'creee':
        messages.error(request, "Cette mission ne peut plus être payée.")
        return redirect('client_dashboard:mes_livraisons')
    
    # Calculer le prix si pas encore fait
    if not mission.prix_total or mission.prix_total == 0:
        mission.calculer_prix_total()
        mission.save()
    
    # Récupérer le portefeuille
    portefeuille, created = Portefeuille.objects.get_or_create(client=request.user)
    
    if request.method == 'POST':
        # Traitement du paiement
        try:
            with transaction.atomic():
                # Vérifier le solde
                if portefeuille.solde_total < mission.prix_total:
                    messages.error(request, f"Solde insuffisant. Votre solde: {portefeuille.solde_total} FCFA, Montant requis: {mission.prix_total} FCFA")
                    return redirect('client_dashboard:recharger_portefeuille')
                
                # Débiter le portefeuille
                portefeuille.solde -= mission.prix_total
                portefeuille.save()
                
                # Créer la transaction
                transaction_paiement = Transaction.objects.create(
                    client=request.user,
                    amount=mission.prix_total,
                    payment_method='portefeuille',
                    status='completed',
                    transaction_id=f"MC{mission.id}_{timezone.now().timestamp()}",
                    notes=f"Paiement mission courses #{mission.id}"
                )
                
                # Mettre à jour la mission
                mission.paiement_effectue = True
                mission.status = 'payee'
                mission.transaction_paiement = transaction_paiement
                mission.save()
                
                # Publier la mission
                mission.status = 'publiee'
                mission.date_publication = timezone.now()
                mission.save()
                
                # Nettoyer la session
                if 'mission_courses_id' in request.session:
                    del request.session['mission_courses_id']
                
                messages.success(request, "Paiement effectué avec succès ! Votre mission est maintenant publiée.")
                return redirect('client_dashboard:detail_mission_courses', mission_id=mission.id)
                
        except Exception as e:
            logger.error(f"Erreur paiement: {e}")
            messages.error(request, f"Erreur lors du paiement: {str(e)}")
    
    return render(request, 'client_dashboard/paiement_mission_courses.html', {
        'mission': mission,
        'portefeuille': portefeuille
    })


@login_required
def detail_mission_courses(request, mission_id):
    """Détails d'une mission de courses"""
    mission = get_object_or_404(MissionCourses, id=mission_id, client=request.user)
    
    # Calculer le temps restant si mission en cours
    temps_restant = None
    if mission.delai_debut and mission.status in ['acceptee', 'en_cours']:
        if mission.delai_type == 'heure_limite' and mission.heure_limite:
            temps_restant = mission.heure_limite - timezone.now()
        elif mission.delai_type == 'duree_max_minutes' and mission.duree_max_minutes:
            delai_fin = mission.delai_debut + timedelta(minutes=mission.duree_max_minutes)
            temps_restant = delai_fin - timezone.now()
    
    return render(request, 'client_dashboard/detail_mission_courses.html', {
        'mission': mission,
        'temps_restant': temps_restant,
        'est_en_retard': mission.est_en_retard
    })


@login_required
def missions_courses_disponibles(request):
    """Liste des missions de courses disponibles pour les livreurs"""
    if request.user.user_type != 'livreur':
        messages.error(request, "Seuls les livreurs peuvent voir les missions disponibles.")
        return redirect('public:dashboard')
    
    missions = MissionCourses.objects.filter(
        status='publiee',
        livreur__isnull=True
    ).order_by('-date_publication')
    
    # Vérifier si le livreur a déjà postulé
    user_has_applied = missions.filter(candidats=request.user).values_list('id', flat=True)
    
    return render(request, 'client_dashboard/missions_courses_disponibles.html', {
        'missions': missions,
        'user_has_applied': set(user_has_applied),
        'show_limited_info': True
    })


@login_required
@csrf_protect
@require_http_methods(["POST"])
def postuler_mission_courses(request, mission_id):
    """Permettre à un livreur de postuler à une mission de courses"""
    if request.user.user_type != 'livreur':
        messages.error(request, "Seuls les livreurs peuvent postuler.")
        return redirect('public:dashboard')
    
    mission = get_object_or_404(MissionCourses, id=mission_id, status='publiee')
    
    if mission.candidats.filter(id=request.user.id).exists():
        messages.info(request, "Vous avez déjà postulé à cette mission.")
        return redirect('client_dashboard:missions_courses_disponibles')
    
    mission.candidats.add(request.user)
    messages.success(request, "Votre candidature a été envoyée avec succès !")
    
    return redirect('client_dashboard:missions_courses_disponibles')


@login_required
def executer_mission_courses(request, mission_id):
    """Vue pour le livreur d'exécuter une mission étape par étape"""
    mission = get_object_or_404(MissionCourses, id=mission_id, livreur=request.user)
    
    if mission.status not in ['acceptee', 'en_cours']:
        messages.error(request, "Cette mission n'est pas encore acceptée ou est terminée.")
        return redirect('public:dashboard')
    
    etape_actuelle = mission.etapes.filter(numero_ordre=mission.etape_actuelle).first()
    etapes = mission.etapes.all().order_by('numero_ordre')
    
    return render(request, 'client_dashboard/executer_mission_courses.html', {
        'mission': mission,
        'etape_actuelle': etape_actuelle,
        'etapes': etapes
    })


@login_required
@csrf_protect
@require_http_methods(["POST"])
def valider_etape_courses(request, mission_id, etape_id):
    """Valider une étape de la mission"""
    mission = get_object_or_404(MissionCourses, id=mission_id, livreur=request.user)
    etape = get_object_or_404(EtapeMission, id=etape_id, mission=mission)
    
    if etape.numero_ordre != mission.etape_actuelle:
        messages.error(request, "Vous devez valider les étapes dans l'ordre.")
        return redirect('client_dashboard:executer_mission_courses', mission_id=mission.id)
    
    try:
        with transaction.atomic():
            # Marquer l'étape comme validée
            etape.est_validee = True
            etape.date_validation = timezone.now()
            if not etape.date_debut:
                etape.date_debut = timezone.now()
            etape.date_fin = timezone.now()
            etape.commentaire_validation = request.POST.get('commentaire', '')
            etape.save()
            
            # Créer une validation avec preuve si fichier fourni
            if 'fichier_preuve' in request.FILES:
                ValidationEtape.objects.create(
                    etape=etape,
                    type_preuve='photo',
                    fichier=request.FILES['fichier_preuve'],
                    commentaire=request.POST.get('commentaire', '')
                )
            
            # Mettre à jour les articles achetés
            articles_achetes = request.POST.getlist('articles_achetes')
            for article_id in articles_achetes:
                article = ArticleCourseMission.objects.filter(id=article_id, etape=etape).first()
                if article:
                    article.est_achete = True
                    prix_reel = request.POST.get(f'prix_reel_{article_id}')
                    if prix_reel:
                        article.prix_reel = Decimal(prix_reel)
                    article.save()
            
            # Passer à l'étape suivante ou terminer
            if mission.etape_actuelle < mission.nombre_etapes:
                mission.etape_actuelle += 1
                mission.status = 'en_cours'
            else:
                # Dernière étape validée = mission terminée
                mission.status = 'livree'
                mission.date_livraison = timezone.now()
            
            mission.save()
            
            messages.success(request, f"Étape {etape.numero_ordre} validée avec succès !")
            
            if mission.status == 'livree':
                return redirect('client_dashboard:detail_mission_courses', mission_id=mission.id)
            else:
                return redirect('client_dashboard:executer_mission_courses', mission_id=mission.id)
                
    except Exception as e:
        logger.error(f"Erreur validation étape: {e}")
        messages.error(request, f"Erreur lors de la validation: {str(e)}")
        return redirect('client_dashboard:executer_mission_courses', mission_id=mission.id)

