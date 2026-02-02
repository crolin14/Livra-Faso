from django.urls import path
from . import payment_views

app_name = 'client_dashboard_payment'

urlpatterns = [
    # Paiements
    path('initier/', payment_views.initier_paiement, name='initier_paiement'),
    path('statut/<int:transaction_id>/', payment_views.verifier_statut_paiement, name='verifier_statut_paiement'),
    path('recharger/', payment_views.recharger_portefeuille, name='recharger_portefeuille'),
    path('historique/', payment_views.historique_transactions, name='historique_transactions'),
    
    # Callbacks paiements
    path('orange/', payment_views.callback_orange_money, name='callback_orange_money'),
    path('moov/', payment_views.callback_moov_money, name='callback_moov_money'),
    path('wave/', payment_views.webhook_wave, name='webhook_wave'),
]
