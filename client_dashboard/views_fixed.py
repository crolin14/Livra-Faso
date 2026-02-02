from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from datetime import timedelta
import json

from .models import (
    ClientProfile, Transaction, ListeCourses, ArticleCourses,
    Portefeuille, MoyenPaiement, AdresseFavorite, EstimationPrix
)
from missions.models import Mission
from rbac.decorators import require_any_role

@login_required
@require_any_role('client')
def client_dashboard(request):
    """Dashboard principal du client"""
    client = request.user
    
    # Créer le profil client s'il n'existe pas
    client_profile, created = ClientProfile.objects.get_or_create(user=client)
    
    # Statistiques générales
    missions_stats = {
        'total_missions': Mission.objects.filter(client=client).count(),
        'missions_en_cours': Mission.objects.filter(client=client, status__in=['en_attente', 'acceptee', 'en_cours']).count(),
        'missions_terminees': Mission.objects.filter(client=client, status='terminee').count(),
    }
    
    # Missions récentes
    missions_recentes = Mission.objects.filter(client=client).order_by('-created_at')[:5]
    
    # Portefeuille
    portefeuille, created = Portefeuille.objects.get_or_create(client=client_profile)
    
    # Transactions récentes
    transactions_recentes = Transaction.objects.filter(client=client_profile).order_by('-created_at')[:5]
    
    # Listes de courses actives
    listes_courses = ListeCourses.objects.filter(client=client_profile, est_completee=False)[:3]
    
    context = {
        'client_profile': client_profile,
        'missions_stats': missions_stats,
        'missions_recentes': missions_recentes,
        'portefeuille': portefeuille,
        'transactions_recentes': transactions_recentes,
        'listes_courses': listes_courses,
    }
    
    return render(request, 'client_dashboard/dashboard.html', context)

@login_required
@require_any_role('client')
def nouvelle_livraison(request):
    """Créer une nouvelle mission de livraison"""
    client_profile, created = ClientProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            title = request.POST.get('title')
            description = request.POST.get('description', '')
            pickup_address = request.POST.get('pickup_address')
            delivery_address = request.POST.get('delivery_address')
            estimated_price = request.POST.get('estimated_price', 0)
            priority = request.POST.get('priority', 'normal')
            
            # Validation des champs requis
            if not title or not pickup_address or not delivery_address:
                if request.content_type == 'application/json':
                    return JsonResponse({
                        'success': False,
                        'error': 'Veuillez remplir tous les champs obligatoires'
                    })
                else:
                    messages.error(request, 'Veuillez remplir tous les champs obligatoires')
                    return redirect('client_dashboard:nouvelle_livraison')
            
            # Logique robuste pour le prix : toujours garantir qu'il y a un prix valide
            prix = request.POST.get('price')
            prix_estime = estimated_price
            
            if prix and float(prix) > 0:
                prix_final = float(prix)
            elif prix_estime and float(prix_estime) > 0:
                prix_final = float(prix_estime)
            else:
                messages.error(request, "Le prix estimé ou calculé est obligatoire.")
                return redirect('client_dashboard:nouvelle_livraison')
            
            # Créer la mission
            mission = Mission.objects.create(
                client=request.user,
                title=title,
                description=description,
                pickup_address=pickup_address,
                delivery_address=delivery_address,
                estimated_price=float(prix_estime) if prix_estime else 0,
                price=prix_final,
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
    adresses_favorites = AdresseFavorite.objects.filter(client=client_profile)
    moyens_paiement = MoyenPaiement.objects.filter(client=client_profile, est_actif=True)
    
    context = {
        'adresses_favorites': adresses_favorites,
        'moyens_paiement': moyens_paiement,
    }
    
    return render(request, 'client_dashboard/nouvelle_livraison.html', context)

@login_required
@require_any_role('client')
def faire_courses(request):
    """Interface pour faire ses courses"""
    client_profile, created = ClientProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Créer une nouvelle liste de courses
        nom = request.POST.get('nom')
        description = request.POST.get('description', '')
        budget_max = request.POST.get('budget_max')
        
        liste = ListeCourses.objects.create(
            client=client_profile,
            nom=nom,
            description=description,
            budget_max=float(budget_max) if budget_max else None
        )
        
        messages.success(request, f'Liste "{nom}" créée avec succès!')
        return redirect('client_dashboard:detail_liste_courses', liste_id=liste.id)
    
    # Listes existantes
    mes_listes = ListeCourses.objects.filter(client=client_profile).order_by('-updated_at')
    listes_templates = ListeCourses.objects.filter(client=client_profile, est_template=True)
    
    context = {
        'mes_listes': mes_listes,
        'listes_templates': listes_templates,
    }
    
    return render(request, 'client_dashboard/faire_courses.html', context)

@login_required
@require_any_role('client')
def mon_profil(request):
    """Profil du client"""
    client_profile, created = ClientProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Mise à jour du profil
        client_profile.telephone = request.POST.get('telephone', client_profile.telephone)
        client_profile.adresse = request.POST.get('adresse', client_profile.adresse)
        client_profile.date_naissance = request.POST.get('date_naissance') or client_profile.date_naissance
        client_profile.save()
        
        # Mise à jour de l'utilisateur
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.email = request.POST.get('email', request.user.email)
        request.user.save()
        
        messages.success(request, 'Profil mis à jour avec succès!')
        return redirect('client_dashboard:mon_profil')
    
    # Portefeuille
    portefeuille, created = Portefeuille.objects.get_or_create(client=client_profile)
    
    # Adresses favorites
    adresses = AdresseFavorite.objects.filter(client=client_profile)
    
    # Moyens de paiement
    moyens_paiement = MoyenPaiement.objects.filter(client=client_profile)
    
    context = {
        'client_profile': client_profile,
        'portefeuille': portefeuille,
        'adresses': adresses,
        'moyens_paiement': moyens_paiement,
        'payment_methods': ClientProfile._meta.get_field('default_payment_method').choices,
    }
    
    return render(request, 'client_dashboard/mon_profil.html', context)

@login_required
@require_any_role('client')
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
@require_any_role('client')
@require_http_methods(["POST"])
def ajouter_adresse(request):
    """Ajouter une adresse favorite"""
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        
        client_profile, created = ClientProfile.objects.get_or_create(user=request.user)
        
        adresse = AdresseFavorite.objects.create(
            client=client_profile,
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
@require_any_role('client')
@require_http_methods(["POST"])
def ajouter_moyen_paiement(request):
    """Ajouter un moyen de paiement"""
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        
        client_profile, created = ClientProfile.objects.get_or_create(user=request.user)
        
        moyen = MoyenPaiement.objects.create(
            client=client_profile,
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
@require_any_role('client')
def suivi_mission(request, mission_id):
    """Suivi détaillé d'une mission"""
    mission = get_object_or_404(Mission, id=mission_id, client=request.user)
    
    # Événements de suivi (simulés pour l'instant)
    tracking_events = [
        {
            'status': 'created',
            'timestamp': mission.created_at,
            'description': 'Mission créée',
            'icon': 'plus-circle'
        }
    ]
    
    if mission.status != 'pending':
        tracking_events.append({
            'status': 'accepted',
            'timestamp': mission.updated_at,
            'description': 'Mission acceptée par un livreur',
            'icon': 'user-check'
        })
    
    if mission.status == 'completed':
        tracking_events.append({
            'status': 'completed',
            'timestamp': mission.updated_at,
            'description': 'Mission terminée',
            'icon': 'check-circle'
        })
    
    context = {
        'mission': mission,
        'tracking_events': tracking_events,
    }
    
    return render(request, 'client_dashboard/suivi_mission.html', context)

@login_required
@require_any_role('client')
def mes_livraisons(request):
    """Liste des livraisons du client"""
    missions = Mission.objects.filter(client=request.user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(missions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'missions': page_obj,
    }
    
    return render(request, 'client_dashboard/mes_livraisons.html', context)

@login_required
@require_any_role('client')
def detail_liste_courses(request, liste_id):
    """Détail d'une liste de courses"""
    client_profile, created = ClientProfile.objects.get_or_create(user=request.user)
    liste = get_object_or_404(ListeCourses, id=liste_id, client=client_profile)
    
    if request.method == 'POST':
        # Ajouter un article à la liste
        nom_article = request.POST.get('nom_article')
        quantite = request.POST.get('quantite', 1)
        prix_unitaire = request.POST.get('prix_unitaire', 0)
        
        ArticleCourses.objects.create(
            liste=liste,
            nom=nom_article,
            quantite=int(quantite),
            prix_unitaire=float(prix_unitaire) if prix_unitaire else 0
        )
        
        messages.success(request, 'Article ajouté à la liste!')
        return redirect('client_dashboard:detail_liste_courses', liste_id=liste.id)
    
    articles = ArticleCourses.objects.filter(liste=liste)
    total_estime = sum(article.quantite * article.prix_unitaire for article in articles)
    
    context = {
        'liste': liste,
        'articles': articles,
        'total_estime': total_estime,
    }
    
    return render(request, 'client_dashboard/detail_liste_courses.html', context)

@login_required
@require_any_role('client')
def historique_recu(request):
    """Historique des reçus et transactions"""
    client_profile, created = ClientProfile.objects.get_or_create(user=request.user)
    transactions = Transaction.objects.filter(client=client_profile).order_by('-created_at')
    
    # Filtres
    type_filter = request.GET.get('type')
    if type_filter:
        transactions = transactions.filter(type_transaction=type_filter)
    
    # Pagination
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'transactions': page_obj,
        'type_filter': type_filter,
    }
    
    return render(request, 'client_dashboard/historique_recu.html', context)
