"""
Vues pour la gestion des paiements dans le dashboard client
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
import json
import logging

from .models import ClientProfile, Transaction, MoyenPaiement, Portefeuille
from .payment_gateways import payment_manager, PaymentGatewayError
from rbac.decorators import require_any_role
from missions.models import Mission

logger = logging.getLogger(__name__)


@login_required
@require_any_role('client')
def initier_paiement(request):
    """Vue pour initier un paiement"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Récupération des données
            mission_id = data.get('mission_id')
            payment_method = data.get('payment_method')
            amount = float(data.get('amount', 0))
            phone_number = data.get('phone_number')
            
            # Validation
            if not all([mission_id, payment_method, amount]):
                return JsonResponse({
                    'success': False,
                    'error': 'Données manquantes'
                })
            
            # Récupération de la mission
            mission = get_object_or_404(Mission, id=mission_id, client=request.user)
            
            # Récupération du profil client
            client_profile, created = ClientProfile.objects.get_or_create(user=request.user)
            
            # Récupération du moyen de paiement
            moyen_paiement = None
            if payment_method != 'portefeuille':
                moyen_paiement = get_object_or_404(
                    MoyenPaiement, 
                    id=data.get('payment_method_id'),
                    client=client_profile
                )
                phone_number = moyen_paiement.numero_compte
            
            # Traitement selon le type de paiement
            if payment_method == 'portefeuille':
                return process_wallet_payment(request, client_profile, mission, amount)
            else:
                return process_gateway_payment(
                    request, client_profile, mission, amount, 
                    moyen_paiement, phone_number
                )
                
        except Exception as e:
            logger.error(f"Erreur initiation paiement: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Erreur lors de l\'initiation du paiement'
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


def process_wallet_payment(request, client_profile, mission, amount):
    """Traite un paiement par portefeuille"""
    try:
        # Récupération du portefeuille
        portefeuille, created = Portefeuille.objects.get_or_create(client=client_profile)
        
        # Vérification du solde
        if portefeuille.solde < amount:
            return JsonResponse({
                'success': False,
                'error': 'Solde insuffisant',
                'solde_actuel': float(portefeuille.solde)
            })
        
        # Débit du portefeuille
        portefeuille.solde -= amount
        portefeuille.save()
        
        # Création de la transaction
        transaction = Transaction.objects.create(
            client=client_profile,
            mission=mission,
            type_transaction='paiement',
            montant=amount,
            description=f'Paiement mission: {mission.title}',
            statut='reussie',
            reference_externe=f'WALLET_{timezone.now().timestamp()}'
        )
        
        # Mise à jour de la mission
        mission.status = 'paid'
        mission.final_price = amount
        mission.save()
        
        return JsonResponse({
            'success': True,
            'transaction_id': transaction.id,
            'nouveau_solde': float(portefeuille.solde),
            'message': 'Paiement effectué avec succès'
        })
        
    except Exception as e:
        logger.error(f"Erreur paiement portefeuille: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Erreur lors du paiement par portefeuille'
        })


def process_gateway_payment(request, client_profile, mission, amount, moyen_paiement, phone_number):
    """Traite un paiement via une passerelle externe"""
    try:
        # Création de la transaction en attente
        transaction = Transaction.objects.create(
            client=client_profile,
            mission=mission,
            moyen_paiement=moyen_paiement,
            type_transaction='paiement',
            montant=amount,
            description=f'Paiement mission: {mission.title}',
            statut='en_attente'
        )
        
        # Initiation du paiement via la passerelle
        payment_result = payment_manager.initiate_payment(
            payment_method=moyen_paiement.type_paiement,
            amount=amount,
            phone_number=phone_number,
            description=f'LivraFaso - Mission #{mission.id}'
        )
        
        if payment_result.get('success'):
            # Mise à jour de la transaction avec la référence externe
            transaction.reference_externe = payment_result.get('transaction_id')
            transaction.save()
            
            return JsonResponse({
                'success': True,
                'transaction_id': transaction.id,
                'payment_url': payment_result.get('payment_url'),
                'payment_token': payment_result.get('payment_token'),
                'wave_launch_url': payment_result.get('wave_launch_url'),
                'message': 'Paiement initié avec succès'
            })
        else:
            # Échec de l'initiation
            transaction.statut = 'echouee'
            transaction.save()
            
            return JsonResponse({
                'success': False,
                'error': payment_result.get('error', 'Erreur inconnue')
            })
            
    except Exception as e:
        logger.error(f"Erreur paiement passerelle: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Erreur lors du paiement'
        })


@login_required
@require_any_role('client')
def verifier_statut_paiement(request, transaction_id):
    """Vérifie le statut d'un paiement"""
    try:
        client_profile = get_object_or_404(ClientProfile, user=request.user)
        transaction = get_object_or_404(
            Transaction, 
            id=transaction_id, 
            client=client_profile
        )
        
        # Si le paiement est déjà finalisé, retourner le statut
        if transaction.statut in ['reussie', 'echouee', 'annulee']:
            return JsonResponse({
                'success': True,
                'status': transaction.statut,
                'transaction_id': transaction.id
            })
        
        # Vérification via la passerelle si c'est un paiement externe
        if transaction.moyen_paiement and transaction.reference_externe:
            payment_status = payment_manager.check_payment_status(
                transaction.moyen_paiement.type_paiement,
                transaction.reference_externe
            )
            
            # Mise à jour du statut selon la réponse
            status_mapping = {
                'success': 'reussie',
                'failed': 'echouee',
                'pending': 'en_attente',
                'cancelled': 'annulee'
            }
            
            new_status = status_mapping.get(payment_status.get('status'), 'en_attente')
            
            if new_status != transaction.statut:
                transaction.statut = new_status
                transaction.save()
                
                # Si le paiement est réussi, mettre à jour la mission
                if new_status == 'reussie':
                    transaction.mission.status = 'paid'
                    transaction.mission.final_price = transaction.montant
                    transaction.mission.save()
        
        return JsonResponse({
            'success': True,
            'status': transaction.statut,
            'transaction_id': transaction.id
        })
        
    except Exception as e:
        logger.error(f"Erreur vérification statut: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Erreur lors de la vérification'
        })


@login_required
@require_any_role('client')
def recharger_portefeuille(request):
    """Recharge le portefeuille client"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            amount = float(data.get('amount', 0))
            payment_method_id = data.get('payment_method_id')
            
            if amount <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Montant invalide'
                })
            
            client_profile, created = ClientProfile.objects.get_or_create(user=request.user)
            moyen_paiement = get_object_or_404(
                MoyenPaiement, 
                id=payment_method_id,
                client=client_profile
            )
            
            # Création de la transaction de recharge
            transaction = Transaction.objects.create(
                client=client_profile,
                moyen_paiement=moyen_paiement,
                type_transaction='recharge',
                montant=amount,
                description='Recharge portefeuille',
                statut='en_attente'
            )
            
            # Initiation du paiement
            payment_result = payment_manager.initiate_payment(
                payment_method=moyen_paiement.type_paiement,
                amount=amount,
                phone_number=moyen_paiement.numero_compte,
                description='LivraFaso - Recharge portefeuille'
            )
            
            if payment_result.get('success'):
                transaction.reference_externe = payment_result.get('transaction_id')
                transaction.save()
                
                return JsonResponse({
                    'success': True,
                    'transaction_id': transaction.id,
                    'payment_url': payment_result.get('payment_url'),
                    'message': 'Recharge initiée avec succès'
                })
            else:
                transaction.statut = 'echouee'
                transaction.save()
                
                return JsonResponse({
                    'success': False,
                    'error': payment_result.get('error')
                })
                
        except Exception as e:
            logger.error(f"Erreur recharge portefeuille: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Erreur lors de la recharge'
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


@csrf_exempt
@require_http_methods(["POST"])
def callback_orange_money(request):
    """Callback pour les paiements Orange Money"""
    try:
        data = json.loads(request.body)
        
        transaction_ref = data.get('transaction_id')
        status = data.get('status')
        amount = data.get('amount')
        
        # Recherche de la transaction
        transaction = Transaction.objects.filter(
            reference_externe=transaction_ref
        ).first()
        
        if transaction:
            # Mise à jour du statut
            if status == 'SUCCESS':
                transaction.statut = 'reussie'
                
                # Si c'est une recharge, créditer le portefeuille
                if transaction.type_transaction == 'recharge':
                    portefeuille, created = Portefeuille.objects.get_or_create(
                        client=transaction.client
                    )
                    portefeuille.solde += transaction.montant
                    portefeuille.save()
                
                # Si c'est un paiement de mission, mettre à jour la mission
                elif transaction.mission:
                    transaction.mission.status = 'paid'
                    transaction.mission.final_price = transaction.montant
                    transaction.mission.save()
                    
            elif status == 'FAILED':
                transaction.statut = 'echouee'
            
            transaction.save()
            
            return JsonResponse({'success': True})
        
        return JsonResponse({'success': False, 'error': 'Transaction non trouvée'})
        
    except Exception as e:
        logger.error(f"Erreur callback Orange Money: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def callback_moov_money(request):
    """Callback pour les paiements Moov Money"""
    try:
        data = json.loads(request.body)
        
        transaction_ref = data.get('reference')
        status = data.get('status')
        
        transaction = Transaction.objects.filter(
            reference_externe=transaction_ref
        ).first()
        
        if transaction:
            if status == 'SUCCESSFUL':
                transaction.statut = 'reussie'
                
                if transaction.type_transaction == 'recharge':
                    portefeuille, created = Portefeuille.objects.get_or_create(
                        client=transaction.client
                    )
                    portefeuille.solde += transaction.montant
                    portefeuille.save()
                elif transaction.mission:
                    transaction.mission.status = 'paid'
                    transaction.mission.save()
                    
            elif status == 'FAILED':
                transaction.statut = 'echouee'
            
            transaction.save()
            
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f"Erreur callback Moov Money: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def webhook_wave(request):
    """Webhook pour les paiements Wave"""
    try:
        data = json.loads(request.body)
        
        transaction_ref = data.get('transaction_ref')
        status = data.get('status')
        
        transaction = Transaction.objects.filter(
            reference_externe=transaction_ref
        ).first()
        
        if transaction:
            if status == 'completed':
                transaction.statut = 'reussie'
                
                if transaction.type_transaction == 'recharge':
                    portefeuille, created = Portefeuille.objects.get_or_create(
                        client=transaction.client
                    )
                    portefeuille.solde += transaction.montant
                    portefeuille.save()
                elif transaction.mission:
                    transaction.mission.status = 'paid'
                    transaction.mission.save()
                    
            elif status == 'failed':
                transaction.statut = 'echouee'
            
            transaction.save()
            
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f"Erreur webhook Wave: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_any_role('client')
def historique_transactions(request):
    """Affiche l'historique des transactions"""
    client_profile = get_object_or_404(ClientProfile, user=request.user)
    
    transactions = Transaction.objects.filter(
        client=client_profile
    ).order_by('-created_at')
    
    # Filtrage par type si spécifié
    type_filter = request.GET.get('type')
    if type_filter:
        transactions = transactions.filter(type_transaction=type_filter)
    
    # Filtrage par statut si spécifié
    status_filter = request.GET.get('status')
    if status_filter:
        transactions = transactions.filter(statut=status_filter)
    
    context = {
        'transactions': transactions,
        'type_filter': type_filter,
        'status_filter': status_filter
    }
    
    return render(request, 'client_dashboard/historique_transactions.html', context)
