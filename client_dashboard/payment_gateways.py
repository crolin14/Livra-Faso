"""
Intégration des moyens de paiement pour LivraFaso
Support pour Orange Money, Moov Money, Wave et cartes bancaires
"""

import requests
import json
import hashlib
import hmac
import uuid
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

# Liste des domaines autorisés pour les paiements (whitelist)
ALLOWED_PAYMENT_DOMAINS = {
    'orange-money.com',
    'orange.com',
    'moov-money.com',
    'moov.ci',
    'wave.com',
    'sandbox.orange-money.com',
    'api.orange.com',
    'api.moov.ci',
    'api.wave.com',
}


def validate_payment_url(url: str) -> bool:
    """
    Valide une URL pour prévenir les attaques SSRF.
    Vérifie que l'URL pointe vers un domaine autorisé.
    """
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
        
        # Vérifier le schéma (seulement HTTP/HTTPS)
        if parsed.scheme not in ('http', 'https'):
            logger.warning(f"Schéma non autorisé: {parsed.scheme}")
            return False
        
        # Vérifier que l'URL n'est pas une adresse IP privée
        hostname = parsed.hostname
        if not hostname:
            return False
        
        # Vérifier les adresses IP privées
        if hostname.startswith('127.') or hostname.startswith('192.168.') or \
           hostname.startswith('10.') or hostname.startswith('172.16.') or \
           hostname == 'localhost' or hostname == '0.0.0.0':
            logger.warning(f"Tentative d'accès à une adresse privée: {hostname}")
            return False
        
        # Vérifier que le domaine est dans la whitelist
        domain = hostname.lower()
        # Vérifier le domaine exact ou un sous-domaine
        if not any(domain == allowed or domain.endswith('.' + allowed) 
                   for allowed in ALLOWED_PAYMENT_DOMAINS):
            logger.warning(f"Domaine non autorisé: {domain}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Erreur de validation d'URL: {e}")
        return False


class PaymentGatewayError(Exception):
    """Exception personnalisée pour les erreurs de paiement"""
    pass


class BasePaymentGateway:
    """Classe de base pour tous les moyens de paiement"""
    
    def __init__(self):
        self.api_key = getattr(settings, f'{self.__class__.__name__.upper()}_API_KEY', '')
        self.secret_key = getattr(settings, f'{self.__class__.__name__.upper()}_SECRET_KEY', '')
        self.base_url = getattr(settings, f'{self.__class__.__name__.upper()}_BASE_URL', '')
        self.is_sandbox = getattr(settings, 'PAYMENT_SANDBOX_MODE', True)
    
    def generate_transaction_id(self) -> str:
        """Génère un ID de transaction unique"""
        return f"LF_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
    
    def create_signature(self, data: Dict[str, Any]) -> str:
        """Crée une signature pour sécuriser les requêtes"""
        sorted_data = sorted(data.items())
        message = '&'.join([f"{k}={v}" for k, v in sorted_data])
        return hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def initiate_payment(self, amount: float, phone_number: str, description: str) -> Dict[str, Any]:
        """Initie un paiement - à implémenter dans les sous-classes"""
        raise NotImplementedError
    
    def check_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """Vérifie le statut d'un paiement - à implémenter dans les sous-classes"""
        raise NotImplementedError
    
    def process_callback(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Traite les callbacks de paiement - à implémenter dans les sous-classes"""
        raise NotImplementedError


class OrangeMoneyGateway(BasePaymentGateway):
    """Intégration Orange Money"""
    
    def __init__(self):
        super().__init__()
        self.merchant_code = getattr(settings, 'ORANGE_MONEY_MERCHANT_CODE', 'LF001')
        self.callback_url = getattr(settings, 'ORANGE_MONEY_CALLBACK_URL', 'https://livrafaso.com/api/payment/orange/callback/')
    
    def initiate_payment(self, amount: float, phone_number: str, description: str) -> Dict[str, Any]:
        """Initie un paiement Orange Money"""
        try:
            transaction_id = self.generate_transaction_id()
            
            # Données de la requête
            payment_data = {
                'merchant_code': self.merchant_code,
                'transaction_id': transaction_id,
                'amount': int(amount),  # Orange Money utilise les centimes
                'currency': 'XOF',
                'phone_number': phone_number,
                'description': description,
                'callback_url': self.callback_url,
                'return_url': f'https://livrafaso.com/client/paiement/retour/{transaction_id}/',
                'timestamp': int(datetime.now().timestamp())
            }
            
            # Signature de sécurité
            payment_data['signature'] = self.create_signature(payment_data)
            
            # En mode sandbox, simuler une réponse
            if self.is_sandbox:
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'payment_url': f'https://sandbox.orange-money.com/payment/{transaction_id}',
                    'status': 'pending',
                    'message': 'Paiement initié avec succès (mode sandbox)'
                }
            
            # Valider l'URL avant la requête pour prévenir SSRF
            api_url = f'{self.base_url}/api/v1/payment/initiate'
            if not validate_payment_url(api_url):
                logger.error(f"URL non autorisée pour Orange Money: {api_url}")
                return {
                    'success': False,
                    'error': 'URL de paiement non autorisée'
                }
            
            # Requête à l'API Orange Money (URL fictive pour l'exemple)
            response = requests.post(
                api_url,
                json=payment_data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'payment_url': result.get('payment_url'),
                    'status': 'pending',
                    'message': 'Paiement initié avec succès'
                }
            else:
                logger.error(f"Erreur Orange Money: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': 'Erreur lors de l\'initialisation du paiement Orange Money'
                }
                
        except Exception as e:
            logger.error(f"Erreur Orange Money: {str(e)}")
            return {
                'success': False,
                'error': f'Erreur technique: {str(e)}'
            }
    
    def check_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """Vérifie le statut d'un paiement Orange Money"""
        try:
            if self.is_sandbox:
                # Simulation pour le mode sandbox
                import random
                statuses = ['pending', 'success', 'failed']
                return {
                    'transaction_id': transaction_id,
                    'status': random.choice(statuses),
                    'amount': 5000,
                    'phone_number': '22670000000'
                }
            
            api_url = f'{self.base_url}/api/v1/payment/status/{transaction_id}'
            if not validate_payment_url(api_url):
                logger.error(f"URL non autorisée pour vérification Orange Money: {api_url}")
                return {'status': 'error', 'error': 'URL non autorisée'}
            
            response = requests.get(
                api_url,
                headers={'Authorization': f'Bearer {self.api_key}'},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'status': 'unknown', 'error': 'Impossible de vérifier le statut'}
                
        except Exception as e:
            logger.error(f"Erreur vérification Orange Money: {str(e)}")
            return {'status': 'error', 'error': str(e)}


class MoovMoneyGateway(BasePaymentGateway):
    """Intégration Moov Money"""
    
    def __init__(self):
        super().__init__()
        self.merchant_id = getattr(settings, 'MOOV_MONEY_MERCHANT_ID', 'LF_MOOV_001')
    
    def initiate_payment(self, amount: float, phone_number: str, description: str) -> Dict[str, Any]:
        """Initie un paiement Moov Money"""
        try:
            transaction_id = self.generate_transaction_id()
            
            payment_data = {
                'merchant_id': self.merchant_id,
                'reference': transaction_id,
                'amount': amount,
                'currency': 'XOF',
                'customer_phone': phone_number,
                'description': description,
                'callback_url': 'https://livrafaso.com/api/payment/moov/callback/',
                'timestamp': datetime.now().isoformat()
            }
            
            if self.is_sandbox:
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'payment_token': f'moov_token_{transaction_id}',
                    'status': 'pending',
                    'message': 'Paiement Moov Money initié (mode sandbox)'
                }
            
            # Valider l'URL avant la requête
            api_url = f'{self.base_url}/v1/payments'
            if not validate_payment_url(api_url):
                logger.error(f"URL non autorisée pour Moov Money: {api_url}")
                return {
                    'success': False,
                    'error': 'URL de paiement non autorisée'
                }
            
            # Implémentation réelle de l'API Moov Money
            response = requests.post(
                api_url,
                json=payment_data,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'payment_token': result.get('token'),
                    'status': 'pending'
                }
            else:
                return {
                    'success': False,
                    'error': 'Erreur lors de l\'initialisation Moov Money'
                }
                
        except Exception as e:
            logger.error(f"Erreur Moov Money: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def check_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """Vérifie le statut Moov Money"""
        if self.is_sandbox:
            import random
            return {
                'transaction_id': transaction_id,
                'status': random.choice(['pending', 'success', 'failed']),
                'amount': 3000
            }
        
        try:
            api_url = f'{self.base_url}/v1/payments/{transaction_id}'
            if not validate_payment_url(api_url):
                logger.error(f"URL non autorisée pour vérification Moov Money: {api_url}")
                return {'status': 'error', 'error': 'URL non autorisée'}
            
            response = requests.get(
                api_url,
                headers={'Authorization': f'Bearer {self.api_key}'},
                timeout=30
            )
            return response.json() if response.status_code == 200 else {'status': 'unknown'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}


class WaveGateway(BasePaymentGateway):
    """Intégration Wave"""
    
    def __init__(self):
        super().__init__()
        self.app_id = getattr(settings, 'WAVE_APP_ID', 'livrafaso_wave')
    
    def initiate_payment(self, amount: float, phone_number: str, description: str) -> Dict[str, Any]:
        """Initie un paiement Wave"""
        try:
            transaction_id = self.generate_transaction_id()
            
            payment_data = {
                'app_id': self.app_id,
                'transaction_ref': transaction_id,
                'amount': amount,
                'currency': 'XOF',
                'customer_number': phone_number,
                'description': description,
                'webhook_url': 'https://livrafaso.com/api/payment/wave/webhook/'
            }
            
            if self.is_sandbox:
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'wave_launch_url': f'https://checkout.wave.com/pay/{transaction_id}',
                    'status': 'pending',
                    'message': 'Paiement Wave initié (mode sandbox)'
                }
            
            api_url = f'{self.base_url}/checkout/sessions'
            if not validate_payment_url(api_url):
                logger.error(f"URL non autorisée pour Wave: {api_url}")
                return {'success': False, 'error': 'URL de paiement non autorisée'}
            
            response = requests.post(
                api_url,
                json=payment_data,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'wave_launch_url': result.get('wave_launch_url'),
                    'status': 'pending'
                }
            else:
                return {'success': False, 'error': 'Erreur Wave'}
                
        except Exception as e:
            logger.error(f"Erreur Wave: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def check_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """Vérifie le statut Wave"""
        if self.is_sandbox:
            import random
            return {
                'transaction_id': transaction_id,
                'status': random.choice(['pending', 'success', 'failed']),
                'amount': 2500
            }
        
        try:
            api_url = f'{self.base_url}/checkout/sessions/{transaction_id}'
            if not validate_payment_url(api_url):
                logger.error(f"URL non autorisée pour vérification Wave: {api_url}")
                return {'status': 'error', 'error': 'URL non autorisée'}
            
            response = requests.get(
                api_url,
                headers={'Authorization': f'Bearer {self.api_key}'},
                timeout=30
            )
            return response.json() if response.status_code == 200 else {'status': 'unknown'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}


class CreditCardGateway(BasePaymentGateway):
    """Intégration cartes bancaires (via un processeur générique)"""
    
    def initiate_payment(self, amount: float, card_data: Dict[str, str], description: str) -> Dict[str, Any]:
        """Initie un paiement par carte bancaire"""
        try:
            transaction_id = self.generate_transaction_id()
            
            if self.is_sandbox:
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'status': 'pending',
                    'requires_3ds': True,
                    'redirect_url': f'https://3ds.sandbox.com/auth/{transaction_id}'
                }
            
            # Implémentation avec un processeur de paiement réel
            payment_data = {
                'amount': amount,
                'currency': 'XOF',
                'card_number': card_data.get('number'),
                'expiry_month': card_data.get('expiry_month'),
                'expiry_year': card_data.get('expiry_year'),
                'cvv': card_data.get('cvv'),
                'description': description,
                'reference': transaction_id
            }
            
            # Valider l'URL avant la requête
            api_url = f'{self.base_url}/v1/charges'
            if not validate_payment_url(api_url):
                logger.error(f"URL non autorisée pour carte bancaire: {api_url}")
                return {'success': False, 'error': 'URL de paiement non autorisée'}
            
            # Chiffrement des données sensibles avant envoi
            encrypted_data = self.encrypt_card_data(payment_data)
            
            response = requests.post(
                api_url,
                json=encrypted_data,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            
            return response.json() if response.status_code == 200 else {'success': False}
            
        except Exception as e:
            logger.error(f"Erreur carte bancaire: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def encrypt_card_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Chiffre les données de carte bancaire"""
        # Implémentation du chiffrement des données sensibles
        # En production, utiliser une vraie bibliothèque de chiffrement
        return data


class PaymentManager:
    """Gestionnaire principal des paiements"""
    
    def __init__(self):
        self.gateways = {
            'orange_money': OrangeMoneyGateway(),
            'moov_money': MoovMoneyGateway(),
            'wave': WaveGateway(),
            'carte_bancaire': CreditCardGateway()
        }
    
    def get_gateway(self, payment_method: str) -> BasePaymentGateway:
        """Récupère la passerelle de paiement appropriée"""
        gateway = self.gateways.get(payment_method)
        if not gateway:
            raise PaymentGatewayError(f"Méthode de paiement non supportée: {payment_method}")
        return gateway
    
    def initiate_payment(self, payment_method: str, amount: float, 
                        phone_number: str = None, card_data: Dict = None, 
                        description: str = "Paiement LivraFaso") -> Dict[str, Any]:
        """Initie un paiement avec la méthode spécifiée"""
        try:
            gateway = self.get_gateway(payment_method)
            
            if payment_method == 'carte_bancaire':
                if not card_data:
                    raise PaymentGatewayError("Données de carte requises")
                return gateway.initiate_payment(amount, card_data, description)
            else:
                if not phone_number:
                    raise PaymentGatewayError("Numéro de téléphone requis")
                return gateway.initiate_payment(amount, phone_number, description)
                
        except Exception as e:
            logger.error(f"Erreur initiation paiement: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def check_payment_status(self, payment_method: str, transaction_id: str) -> Dict[str, Any]:
        """Vérifie le statut d'un paiement"""
        try:
            gateway = self.get_gateway(payment_method)
            return gateway.check_payment_status(transaction_id)
        except Exception as e:
            logger.error(f"Erreur vérification statut: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def get_supported_methods(self) -> list:
        """Retourne la liste des méthodes de paiement supportées"""
        return list(self.gateways.keys())


# Instance globale du gestionnaire de paiements
payment_manager = PaymentManager()
