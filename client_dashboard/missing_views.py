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
