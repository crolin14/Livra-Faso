from django.shortcuts import render


def terms_view(request):
    """Afficher les conditions générales d'utilisation"""
    context = {
        'title': 'Conditions Générales d\'Utilisation',
    }
    return render(request, 'legal/terms.html', context)


def privacy_view(request):
    """Afficher la politique de confidentialité"""
    context = {
        'title': 'Politique de Confidentialité',
    }
    return render(request, 'legal/privacy.html', context)
