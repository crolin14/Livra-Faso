from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import SubscriptionPlan, UserSubscription, Payment
from datetime import timedelta
import json

def subscription_plans(request):
    """Page publique des plans d'abonnement"""
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    
    # Vérifier l'abonnement actuel si utilisateur connecté
    current_subscription = None
    if request.user.is_authenticated:
        current_subscription = UserSubscription.objects.filter(
            user=request.user,
            status='active'
        ).first()
    
    context = {
        'title': 'Plans d\'abonnement - LivraFaso',
        'plans': plans,
        'current_subscription': current_subscription,
    }
    return render(request, 'subscriptions/plans.html', context)

@login_required
def plan_list(request):
    """Liste des plans d'abonnement pour utilisateurs connectés"""
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    
    # Vérifier l'abonnement actuel de l'utilisateur
    current_subscription = UserSubscription.objects.filter(
        user=request.user,
        status='active'
    ).first()
    
    context = {
        'title': 'Plans d\'abonnement',
        'plans': plans,
        'current_subscription': current_subscription,
    }
    return render(request, 'subscriptions/plan_list.html', context)

@login_required
def subscribe(request, plan_id):
    """S'abonner à un plan"""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
    
    # Vérifier si l'utilisateur a déjà un abonnement actif
    active_subscription = UserSubscription.objects.filter(
        user=request.user,
        status='active'
    ).first()
    
    if active_subscription:
        messages.warning(request, 'Vous avez déjà un abonnement actif.')
        return redirect('subscriptions:plans')
    
    if request.method == 'POST':
        # Créer l'abonnement
        start_date = timezone.now()
        end_date = start_date + timedelta(days=plan.duration)
        
        subscription = UserSubscription.objects.create(
            user=request.user,
            plan=plan,
            start_date=start_date,
            end_date=end_date,
            status='pending'
        )
        
        messages.success(request, f'Abonnement au plan {plan.name} créé !')
        return redirect('subscriptions:payment', subscription_id=subscription.id)
    
    context = {
        'title': f'S\'abonner à {plan.name}',
        'plan': plan,
    }
    return render(request, 'subscriptions/subscribe.html', context)

@login_required
def payment(request, subscription_id):
    """Paiement pour un abonnement"""
    subscription = get_object_or_404(UserSubscription, id=subscription_id, user=request.user)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.user = request.user
            payment.subscription = subscription
            payment.amount = subscription.plan.price
            payment.save()
            
            # Simuler le traitement du paiement (dans un vrai projet, intégrer un gateway de paiement)
            if payment.payment_method == 'mobile_money':
                # Simulation de paiement Mobile Money
                payment.status = 'completed'
                payment.transaction_id = f"MM_{payment.id}_{int(timezone.now().timestamp())}"
                payment.save()
                
                # Activer l'abonnement
                subscription.status = 'active'
                subscription.amount_paid = payment.amount
                subscription.payment_method = payment.payment_method
                subscription.save()
                
                messages.success(request, 'Paiement effectué avec succès ! Votre abonnement est maintenant actif.')
                return redirect('subscriptions:plans')
            else:
                messages.info(request, 'Paiement en cours de traitement...')
                return redirect('subscriptions:history')
    else:
        form = PaymentForm()
    
    context = {
        'title': 'Paiement',
        'form': form,
        'subscription': subscription,
    }
    return render(request, 'subscriptions/payment.html', context)

@login_required
def payment_history(request):
    """Historique des paiements"""
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')
    subscriptions = UserSubscription.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'title': 'Historique des paiements',
        'payments': payments,
        'subscriptions': subscriptions,
    }
    return render(request, 'subscriptions/payment_history.html', context)

@login_required
def cancel_subscription(request, subscription_id):
    """Annuler un abonnement"""
    subscription = get_object_or_404(UserSubscription, id=subscription_id, user=request.user)
    
    if subscription.status == 'active':
        subscription.status = 'cancelled'
        subscription.save()
        messages.success(request, 'Abonnement annulé avec succès.')
    else:
        messages.error(request, 'Cet abonnement ne peut pas être annulé.')
    
    return redirect('subscriptions:history')

@login_required
@require_POST
def process_payment(request):
    """Traiter un paiement"""
    try:
        payment_method = request.POST.get('payment_method')
        subscription_id = request.POST.get('subscription_id')
        
        subscription = get_object_or_404(UserSubscription, id=subscription_id, user=request.user)
        
        # Créer le paiement
        payment = Payment.objects.create(
            user=request.user,
            subscription=subscription,
            amount=subscription.plan.price,
            payment_method=payment_method,
            status='pending'
        )
        
        if payment_method == 'card':
            # Traitement paiement carte
            card_number = request.POST.get('card_number', '').replace(' ', '')
            if len(card_number) >= 16:
                payment.status = 'completed'
                payment.transaction_id = f"CARD_{payment.id}_{int(timezone.now().timestamp())}"
                payment.save()
                
                # Activer l'abonnement
                subscription.status = 'active'
                subscription.save()
                
                messages.success(request, 'Paiement par carte effectué avec succès!')
                return redirect('subscriptions:plans')
            else:
                messages.error(request, 'Numéro de carte invalide.')
                
        elif payment_method == 'mobile_money':
            # Traitement Mobile Money
            mobile_number = request.POST.get('mobile_number')
            mobile_operator = request.POST.get('mobile_operator')
            
            if mobile_number and mobile_operator:
                payment.status = 'pending'
                payment.transaction_id = f"MM_{mobile_operator.upper()}_{payment.id}"
                payment.save()
                
                messages.info(request, f'Paiement Mobile Money initié. Composez le code USSD pour confirmer.')
                return redirect('subscriptions:history')
            else:
                messages.error(request, 'Informations Mobile Money incomplètes.')
        
        return redirect('subscriptions:payment', subscription_id=subscription.id)
        
    except Exception as e:
        messages.error(request, f'Erreur lors du traitement du paiement: {str(e)}')
        return redirect('subscriptions:plans')

@login_required
@require_POST
def confirm_bank_transfer(request):
    """Confirmer un virement bancaire"""
    try:
        subscription_id = request.POST.get('subscription_id')
        subscription = get_object_or_404(UserSubscription, id=subscription_id, user=request.user)
        
        # Créer le paiement en attente
        payment = Payment.objects.create(
            user=request.user,
            subscription=subscription,
            amount=subscription.plan.price,
            payment_method='bank_transfer',
            status='pending'
        )
        
        payment.transaction_id = f"BANK_{payment.id}_{int(timezone.now().timestamp())}"
        payment.save()
        
        messages.info(request, 'Virement bancaire enregistré. Votre abonnement sera activé après vérification du paiement (1-3 jours ouvrables).')
        return redirect('subscriptions:history')
        
    except Exception as e:
        messages.error(request, f'Erreur lors de l\'enregistrement du virement: {str(e)}')
        return redirect('subscriptions:plans')
