#!/usr/bin/env python3
"""
Configuration de Sécurité Avancée - LivraFaso
Phase 2: Implémentation des corrections de sécurité
"""

import os
import secrets
from pathlib import Path

def generate_secure_secret_key():
    """Générer une SECRET_KEY sécurisée"""
    return secrets.token_urlsafe(50)

def create_env_file():
    """Créer le fichier .env avec les variables sécurisées"""
    
    env_content = f"""# Configuration de Production LivraFaso
# Généré automatiquement - NE PAS COMMITER

# Sécurité Django
DEBUG=False
SECRET_KEY={generate_secure_secret_key()}
ALLOWED_HOSTS=livrafaso.bf,www.livrafaso.bf,127.0.0.1,localhost

# Base de données PostgreSQL
DB_NAME=livraison_faso_prod
DB_USER=livraison_user_prod
DB_PASSWORD={secrets.token_urlsafe(32)}
DB_HOST=localhost
DB_PORT=5432

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@livrafaso.bf
EMAIL_HOST_PASSWORD=your_email_password_here

# Sécurité avancée
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_BROWSER_XSS_FILTER=True
SECURE_REFERRER_POLICY=strict-origin-when-cross-origin

# Sessions sécurisées
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_AGE=3600
SESSION_EXPIRE_AT_BROWSER_CLOSE=True

# CSRF Protection
CSRF_COOKIE_SECURE=True
CSRF_COOKIE_HTTPONLY=True
CSRF_USE_SESSIONS=True

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/livrafaso/app.log
"""
    
    with open('.env.production', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ Fichier .env.production créé avec des valeurs sécurisées")
    print("⚠️  IMPORTANT: Modifiez les mots de passe avant utilisation")

if __name__ == "__main__":
    create_env_file()
