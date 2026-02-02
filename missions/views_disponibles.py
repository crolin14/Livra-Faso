from django.shortcuts import render
from .models import Mission

def missions_disponibles(request):
    missions = Mission.objects.filter(livreur__isnull=True)  # ou adaptez selon votre logique
    return render(request, 'missions/missions_disponibles.html', {'missions': missions})
