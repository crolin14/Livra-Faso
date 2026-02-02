"""
Validateurs personnalisés pour la sécurité - LivraFaso
Phase 2: Validation renforcée des mots de passe
"""

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class CustomPasswordValidator:
    """
    Validateur de mot de passe personnalisé avec règles renforcées
    """
    
    def validate(self, password, user=None):
        """
        Valider le mot de passe selon les critères de sécurité
        """
        errors = []
        
        # Vérifier la longueur minimale (déjà géré par MinimumLengthValidator)
        if len(password) < 12:
            errors.append(_("Le mot de passe doit contenir au moins 12 caractères."))
        
        # Vérifier la présence de majuscules
        if not re.search(r'[A-Z]', password):
            errors.append(_("Le mot de passe doit contenir au moins une lettre majuscule."))
        
        # Vérifier la présence de minuscules
        if not re.search(r'[a-z]', password):
            errors.append(_("Le mot de passe doit contenir au moins une lettre minuscule."))
        
        # Vérifier la présence de chiffres
        if not re.search(r'\d', password):
            errors.append(_("Le mot de passe doit contenir au moins un chiffre."))
        
        # Vérifier la présence de caractères spéciaux
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append(_("Le mot de passe doit contenir au moins un caractère spécial (!@#$%^&*(),.?\":{}|<>)."))
        
        # Vérifier qu'il n'y a pas de séquences répétitives
        if re.search(r'(.)\1{2,}', password):
            errors.append(_("Le mot de passe ne doit pas contenir plus de 2 caractères identiques consécutifs."))
        
        # Vérifier qu'il n'y a pas de séquences communes
        common_sequences = ['123', 'abc', 'qwe', 'asd', 'zxc', '000', '111', '222']
        for sequence in common_sequences:
            if sequence.lower() in password.lower():
                errors.append(_("Le mot de passe ne doit pas contenir de séquences communes (123, abc, etc.)."))
                break
        
        # Vérifier contre les informations utilisateur si disponibles
        if user:
            user_info = [
                user.username.lower() if hasattr(user, 'username') else '',
                user.first_name.lower() if hasattr(user, 'first_name') else '',
                user.last_name.lower() if hasattr(user, 'last_name') else '',
                user.email.split('@')[0].lower() if hasattr(user, 'email') and user.email else '',
            ]
            
            for info in user_info:
                if info and len(info) > 2 and info in password.lower():
                    errors.append(_("Le mot de passe ne doit pas contenir d'informations personnelles."))
                    break
        
        if errors:
            raise ValidationError(errors)
    
    def get_help_text(self):
        return _(
            "Votre mot de passe doit contenir au moins 12 caractères, "
            "incluant des majuscules, minuscules, chiffres et caractères spéciaux. "
            "Évitez les séquences répétitives et les informations personnelles."
        )

class PhoneNumberValidator:
    """
    Validateur pour les numéros de téléphone burkinabé
    """
    
    def __call__(self, value):
        # Format burkinabé: +226 XX XX XX XX ou 0X XX XX XX XX
        burkina_pattern = r'^(\+226|0)[567]\d{7}$'
        
        if not re.match(burkina_pattern, value.replace(' ', '')):
            raise ValidationError(
                _("Numéro de téléphone invalide. Format attendu: +226 XX XX XX XX ou 0X XX XX XX XX"),
                code='invalid_phone'
            )

class SecureFileValidator:
    """
    Validateur pour les uploads de fichiers sécurisés
    """
    
    def __init__(self, allowed_extensions=None, max_size=None):
        self.allowed_extensions = allowed_extensions or ['.jpg', '.jpeg', '.png', '.pdf', '.doc', '.docx']
        self.max_size = max_size or 5 * 1024 * 1024  # 5MB par défaut
    
    def __call__(self, value):
        # Vérifier l'extension
        if value.name:
            ext = value.name.lower().split('.')[-1]
            if f'.{ext}' not in self.allowed_extensions:
                raise ValidationError(
                    _("Type de fichier non autorisé. Extensions autorisées: {}").format(
                        ', '.join(self.allowed_extensions)
                    ),
                    code='invalid_extension'
                )
        
        # Vérifier la taille
        if value.size > self.max_size:
            raise ValidationError(
                _("Fichier trop volumineux. Taille maximale: {} MB").format(
                    self.max_size // (1024 * 1024)
                ),
                code='file_too_large'
            )
        
        # Vérifier le contenu (basique)
        if hasattr(value, 'read'):
            # Lire les premiers bytes pour détecter les fichiers malveillants
            value.seek(0)
            header = value.read(1024)
            value.seek(0)
            
            # Vérifier les signatures de fichiers dangereux
            dangerous_signatures = [
                b'MZ',  # Exécutable Windows
                b'\x7fELF',  # Exécutable Linux
                b'<?php',  # Script PHP
                b'<script',  # Script JavaScript
            ]
            
            for signature in dangerous_signatures:
                if header.startswith(signature) or signature in header:
                    raise ValidationError(
                        _("Fichier potentiellement dangereux détecté."),
                        code='dangerous_file'
                    )

class BusinessLicenseValidator:
    """
    Validateur pour les numéros de licence d'entreprise burkinabé
    """
    
    def __call__(self, value):
        # Format simplifié pour le Burkina Faso
        # À adapter selon les vrais formats officiels
        if not re.match(r'^[A-Z]{2}\d{6,10}$', value.upper()):
            raise ValidationError(
                _("Format de licence d'entreprise invalide."),
                code='invalid_license'
            )
