from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from users.models import User

def get_livreur_location(request, livreur_id):
    livreur = get_object_or_404(User, id=livreur_id)
    if livreur.user_type != 'livreur':
        return JsonResponse({'error': 'Cet utilisateur n\'est pas un livreur.'}, status=400)

    location = {
        'latitude': livreur.latitude,
        'longitude': livreur.longitude,
    }
    return JsonResponse(location)