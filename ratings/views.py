from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import Rating, RatingCategory, CategoryRating
from .forms import RatingForm
from django.db import models

User = get_user_model()

@login_required
def user_ratings(request, user_id):
    """Afficher les évaluations d'un utilisateur"""
    user = get_object_or_404(User, id=user_id)
    ratings = Rating.objects.filter(rated_user=user).order_by('-created_at')
    
    context = {
        'title': f'Évaluations de {user.username}',
        'rated_user': user,
        'ratings': ratings,
        'average_rating': ratings.aggregate(avg=models.Avg('rating'))['avg'] or 0,
    }
    return render(request, 'ratings/user_ratings.html', context)

@login_required
def rate_user(request, user_id):
    """Évaluer un utilisateur"""
    rated_user = get_object_or_404(User, id=user_id)
    
    # Vérifier que l'utilisateur ne s'évalue pas lui-même
    if rated_user == request.user:
        messages.error(request, 'Vous ne pouvez pas vous évaluer vous-même.')
        return redirect('home')
    
    # Vérifier si l'utilisateur a déjà évalué cet utilisateur
    existing_rating = Rating.objects.filter(rater=request.user, rated_user=rated_user).first()
    
    if request.method == 'POST':
        form = RatingForm(request.POST, instance=existing_rating)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.rater = request.user
            rating.rated_user = rated_user
            rating.save()
            
            messages.success(request, f'Évaluation de {rated_user.username} enregistrée !')
            return redirect('ratings:user_ratings', user_id=user_id)
    else:
        form = RatingForm(instance=existing_rating)
    
    context = {
        'title': f'Évaluer {rated_user.username}',
        'form': form,
        'rated_user': rated_user,
        'existing_rating': existing_rating,
    }
    return render(request, 'ratings/rate_user.html', context)

@login_required
def rate_mission(request, mission_id):
    """Évaluer une mission complétée"""
    from missions.models import Mission
    
    mission = get_object_or_404(Mission, id=mission_id, status='livree')
    
    # Vérifier que l'utilisateur est impliqué dans cette mission
    if request.user != mission.client and request.user != mission.livreur:
        messages.error(request, 'Vous n\'avez pas accès à cette mission.')
        return redirect('missions:list')
    
    # Déterminer qui évaluer
    if request.user == mission.client:
        user_to_rate = mission.livreur
    else:
        user_to_rate = mission.client
    
    # Vérifier si l'utilisateur a déjà évalué cette mission
    existing_rating = Rating.objects.filter(
        rater=request.user, 
        rated_user=user_to_rate,
        mission=mission
    ).first()
    
    if request.method == 'POST':
        form = RatingForm(request.POST, instance=existing_rating)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.rater = request.user
            rating.rated_user = user_to_rate
            rating.mission = mission
            rating.save()
            
            messages.success(request, f'Évaluation de {user_to_rate.username} enregistrée !')
            return redirect('missions:detail', mission_id=mission.id)
    else:
        form = RatingForm(instance=existing_rating)
    
    context = {
        'title': f'Évaluer la mission #{mission.id}',
        'form': form,
        'mission': mission,
        'user_to_rate': user_to_rate,
        'existing_rating': existing_rating,
    }
    return render(request, 'ratings/rate_mission.html', context)
