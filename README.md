# LivraFaso - Plateforme de Livraison Digitale

Plateforme complète de livraison pour le Burkina Faso et l'Afrique de l'Ouest, développée avec Django.

## 📋 Description

LivraFaso est une plateforme de livraison digitale qui connecte les clients, les livreurs et les entreprises pour faciliter les livraisons de colis et de courses dans toute la région.

## ✨ Fonctionnalités principales

- 🚚 **Gestion de missions de livraison** : Création, suivi et gestion des missions
- 👥 **Multi-acteurs** : Clients, Livreurs, Entreprises et Administrateurs
- 💳 **Paiements intégrés** : Orange Money, Moov Money, Wave et cartes bancaires
- 📍 **Géolocalisation** : Suivi en temps réel des livraisons
- 💬 **Chat en temps réel** : Communication entre clients et livreurs
- 📊 **Analytics** : Tableaux de bord et statistiques détaillées
- 🔐 **Sécurité** : Système RBAC (Role-Based Access Control) complet
- 📱 **Notifications** : SMS, Email et notifications push

## 🛠️ Technologies

- **Backend** : Django 5.2.4
- **Base de données** : PostgreSQL
- **Temps réel** : Django Channels (WebSocket)
- **API** : Django REST Framework
- **Frontend** : HTML, CSS, JavaScript (moderne)

## 📦 Installation

### Prérequis

- Python 3.8+
- PostgreSQL
- pip

### Étapes d'installation

1. **Cloner le dépôt**
```bash
git clone https://github.com/crolin14/Livra-Faso.git
cd Livraison_Faso
```

2. **Créer un environnement virtuel**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer les variables d'environnement**
```bash
cp .env.example .env
# Éditer .env avec vos configurations
```

5. **Configurer la base de données**
```bash
python manage.py migrate
python manage.py createsuperuser
```

6. **Lancer le serveur**
```bash
python manage.py runserver
```

## 🔧 Configuration

### Variables d'environnement importantes

- `SECRET_KEY` : Clé secrète Django (générer avec `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`)
- `DEBUG` : Mode debug (True/False)
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` : Configuration PostgreSQL
- `ALLOWED_HOSTS` : Liste des hôtes autorisés

## 📚 Structure du projet

```
Livraison_Faso/
├── admin/              # Gestion admin
├── admin_dashboard/    # Dashboard administrateur
├── analytics/          # Analytics et métriques
├── api/                # API REST
├── audit/              # Logs et audit
├── chat/               # Chat temps réel
├── client_dashboard/   # Dashboard client
├── geolocation/        # Géolocalisation
├── legal/              # Aspects légaux
├── location/           # Gestion localisation
├── missions/           # Cœur métier missions
├── notifications/      # Système de notifications
├── promotions/         # Promotions et offres
├── public/             # Pages publiques
├── ratings/            # Système d'évaluation
├── rbac/               # Gestion des rôles et permissions
├── subscriptions/      # Abonnements
├── support/            # Support client
├── users/              # Gestion utilisateurs
├── templates/          # Templates HTML
├── static/             # Fichiers statiques
└── Livraison_Faso/     # Configuration Django
```

## 🚀 Utilisation

### Créer un utilisateur administrateur
```bash
python create_admin_user.py
```

### Lancer les migrations
```bash
python manage.py migrate
```

### Collecter les fichiers statiques
```bash
python manage.py collectstatic
```

## 🔒 Sécurité

- ✅ Validation des URLs pour prévenir les attaques SSRF
- ✅ Protection contre les injections de commande
- ✅ Mots de passe stockés de manière sécurisée
- ✅ Système RBAC pour la gestion des permissions
- ✅ Protection CSRF activée

## 📝 Licence

Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 👥 Contribution

Les contributions sont les bienvenues ! Veuillez :
1. Fork le projet
2. Créer une branche pour votre fonctionnalité (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📞 Support

Pour toute question ou problème, veuillez ouvrir une issue sur GitHub.

## 🙏 Remerciements

- Django Community
- Tous les contributeurs du projet
