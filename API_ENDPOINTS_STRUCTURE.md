# 🚀 API Endpoints & Project Structure

## 📁 Arborescence Projet Complète

```
livrafaso-admin/
├── backend/
│   ├── livrafaso/
│   │   ├── __init__.py
│   │   ├── settings/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   ├── production.py
│   │   │   └── testing.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   ├── asgi.py
│   │   └── celery.py
│   ├── apps/
│   │   ├── authentication/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── permissions.py
│   │   │   ├── middleware.py
│   │   │   └── urls.py
│   │   ├── rbac/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── decorators.py
│   │   │   └── urls.py
│   │   ├── cms/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── blocks/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── text.py
│   │   │   │   ├── image.py
│   │   │   │   └── video.py
│   │   │   └── urls.py
│   │   ├── orders/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── tasks.py
│   │   │   └── urls.py
│   │   ├── payments/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── providers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── orange_money.py
│   │   │   │   ├── moov_money.py
│   │   │   │   └── wave.py
│   │   │   └── urls.py
│   │   ├── notifications/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── consumers.py
│   │   │   ├── routing.py
│   │   │   └── urls.py
│   │   ├── analytics/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── services.py
│   │   │   └── urls.py
│   │   ├── support/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   └── urls.py
│   │   ├── promotions/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   └── urls.py
│   │   ├── audit/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── middleware.py
│   │   │   └── urls.py
│   │   └── i18n/
│   │       ├── __init__.py
│   │       ├── models.py
│   │       ├── serializers.py
│   │       ├── views.py
│   │       └── urls.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── permissions.py
│   │   ├── pagination.py
│   │   ├── filters.py
│   │   ├── validators.py
│   │   └── exceptions.py
│   ├── requirements/
│   │   ├── base.txt
│   │   ├── development.txt
│   │   ├── production.txt
│   │   └── testing.txt
│   ├── manage.py
│   └── pytest.ini
├── frontend/
│   ├── public/
│   │   ├── index.html
│   │   ├── favicon.ico
│   │   └── manifest.json
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   │   ├── button.tsx
│   │   │   │   ├── input.tsx
│   │   │   │   ├── table.tsx
│   │   │   │   ├── modal.tsx
│   │   │   │   └── index.ts
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Breadcrumbs.tsx
│   │   │   │   └── Layout.tsx
│   │   │   ├── charts/
│   │   │   │   ├── LineChart.tsx
│   │   │   │   ├── BarChart.tsx
│   │   │   │   ├── PieChart.tsx
│   │   │   │   └── Heatmap.tsx
│   │   │   ├── cms/
│   │   │   │   ├── BlockEditor.tsx
│   │   │   │   ├── DragDropProvider.tsx
│   │   │   │   ├── blocks/
│   │   │   │   │   ├── TextBlock.tsx
│   │   │   │   │   ├── ImageBlock.tsx
│   │   │   │   │   ├── VideoBlock.tsx
│   │   │   │   │   └── index.ts
│   │   │   │   └── PagePreview.tsx
│   │   │   └── notifications/
│   │   │       ├── NotificationCenter.tsx
│   │   │       ├── Toast.tsx
│   │   │       └── WebSocketProvider.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Users/
│   │   │   │   ├── UsersList.tsx
│   │   │   │   ├── UserForm.tsx
│   │   │   │   └── RoleManagement.tsx
│   │   │   ├── Orders/
│   │   │   │   ├── OrdersList.tsx
│   │   │   │   ├── OrderDetails.tsx
│   │   │   │   └── OrderTracking.tsx
│   │   │   ├── CMS/
│   │   │   │   ├── PagesList.tsx
│   │   │   │   ├── PageEditor.tsx
│   │   │   │   └── MediaLibrary.tsx
│   │   │   ├── Analytics/
│   │   │   │   ├── Overview.tsx
│   │   │   │   ├── Performance.tsx
│   │   │   │   └── Reports.tsx
│   │   │   └── Settings/
│   │   │       ├── General.tsx
│   │   │       ├── Pricing.tsx
│   │   │       └── Notifications.tsx
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── usePermissions.ts
│   │   │   ├── useWebSocket.ts
│   │   │   ├── useLocalStorage.ts
│   │   │   └── useTheme.ts
│   │   ├── store/
│   │   │   ├── index.ts
│   │   │   ├── authSlice.ts
│   │   │   ├── uiSlice.ts
│   │   │   └── notificationsSlice.ts
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   ├── auth.ts
│   │   │   ├── websocket.ts
│   │   │   └── storage.ts
│   │   ├── utils/
│   │   │   ├── constants.ts
│   │   │   ├── helpers.ts
│   │   │   ├── validators.ts
│   │   │   └── formatters.ts
│   │   ├── types/
│   │   │   ├── api.ts
│   │   │   ├── auth.ts
│   │   │   ├── cms.ts
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── tsconfig.json
├── docker/
│   ├── backend/
│   │   └── Dockerfile
│   ├── frontend/
│   │   └── Dockerfile
│   ├── nginx/
│   │   ├── Dockerfile
│   │   └── nginx.conf
│   └── postgres/
│       └── init.sql
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
└── README.md
```

## 🔗 Endpoints API REST

### 🔐 Authentication & RBAC
```
POST   /api/auth/login/                    # Connexion
POST   /api/auth/logout/                   # Déconnexion
POST   /api/auth/refresh/                  # Refresh token
GET    /api/auth/me/                       # Profil utilisateur
PUT    /api/auth/me/                       # Modifier profil

GET    /api/rbac/roles/                    # Liste des rôles
POST   /api/rbac/roles/                    # Créer rôle
GET    /api/rbac/roles/{id}/               # Détails rôle
PUT    /api/rbac/roles/{id}/               # Modifier rôle
DELETE /api/rbac/roles/{id}/               # Supprimer rôle

GET    /api/rbac/permissions/              # Liste permissions
GET    /api/rbac/permissions/by-module/    # Permissions par module

POST   /api/rbac/users/{id}/assign-role/   # Assigner rôle
DELETE /api/rbac/users/{id}/revoke-role/   # Révoquer rôle
GET    /api/rbac/users/{id}/permissions/   # Permissions utilisateur
```

### 👥 Users Management
```
GET    /api/users/                         # Liste utilisateurs
POST   /api/users/                         # Créer utilisateur
GET    /api/users/{id}/                    # Détails utilisateur
PUT    /api/users/{id}/                    # Modifier utilisateur
DELETE /api/users/{id}/                    # Supprimer utilisateur
POST   /api/users/{id}/activate/           # Activer compte
POST   /api/users/{id}/deactivate/         # Désactiver compte
POST   /api/users/{id}/reset-password/     # Reset mot de passe
GET    /api/users/stats/                   # Statistiques utilisateurs
GET    /api/users/export/                  # Export CSV/Excel
```

### 📦 Orders & Deliveries
```
GET    /api/orders/                        # Liste commandes
POST   /api/orders/                        # Créer commande
GET    /api/orders/{id}/                   # Détails commande
PUT    /api/orders/{id}/                   # Modifier commande
DELETE /api/orders/{id}/                   # Annuler commande
POST   /api/orders/{id}/assign-delivery/   # Assigner livreur
GET    /api/orders/{id}/timeline/          # Timeline événements
POST   /api/orders/{id}/events/            # Ajouter événement
GET    /api/orders/stats/                  # Statistiques commandes
GET    /api/orders/export/                 # Export données

GET    /api/deliveries/                    # Liste livraisons
GET    /api/deliveries/{id}/               # Détails livraison
PUT    /api/deliveries/{id}/status/        # Changer statut
GET    /api/deliveries/{id}/tracking/      # Suivi en temps réel
POST   /api/deliveries/{id}/rating/        # Noter livraison
GET    /api/deliveries/performance/        # Performance livreurs
```

### 💳 Payments & Subscriptions
```
GET    /api/payments/                      # Liste paiements
GET    /api/payments/{id}/                 # Détails paiement
POST   /api/payments/{id}/refund/          # Rembourser
GET    /api/payments/stats/                # Statistiques paiements
GET    /api/payments/export/               # Export transactions

GET    /api/subscriptions/plans/           # Plans d'abonnement
POST   /api/subscriptions/plans/           # Créer plan
GET    /api/subscriptions/plans/{id}/      # Détails plan
PUT    /api/subscriptions/plans/{id}/      # Modifier plan
DELETE /api/subscriptions/plans/{id}/      # Supprimer plan

GET    /api/subscriptions/                 # Abonnements actifs
GET    /api/subscriptions/{id}/            # Détails abonnement
POST   /api/subscriptions/{id}/renew/      # Renouveler
POST   /api/subscriptions/{id}/cancel/     # Annuler
GET    /api/subscriptions/stats/           # Statistiques abonnements
```

### 📝 CMS & Content
```
GET    /api/cms/pages/                     # Liste pages
POST   /api/cms/pages/                     # Créer page
GET    /api/cms/pages/{id}/                # Détails page
PUT    /api/cms/pages/{id}/                # Modifier page
DELETE /api/cms/pages/{id}/                # Supprimer page
POST   /api/cms/pages/{id}/publish/        # Publier page
POST   /api/cms/pages/{id}/unpublish/      # Dépublier page
GET    /api/cms/pages/{id}/versions/       # Versions page
POST   /api/cms/pages/{id}/revert/         # Revenir version
GET    /api/cms/pages/{id}/preview/        # Aperçu page

GET    /api/cms/blocks/                    # Blocs de contenu
POST   /api/cms/blocks/                    # Créer bloc
GET    /api/cms/blocks/{id}/               # Détails bloc
PUT    /api/cms/blocks/{id}/               # Modifier bloc
DELETE /api/cms/blocks/{id}/               # Supprimer bloc

GET    /api/cms/media/                     # Bibliothèque médias
POST   /api/cms/media/upload/              # Upload fichier
GET    /api/cms/media/{id}/                # Détails média
PUT    /api/cms/media/{id}/                # Modifier métadonnées
DELETE /api/cms/media/{id}/                # Supprimer média
```

### 📊 Analytics & Statistics
```
GET    /api/analytics/dashboard/           # Métriques dashboard
GET    /api/analytics/users/               # Analytics utilisateurs
GET    /api/analytics/orders/              # Analytics commandes
GET    /api/analytics/revenue/             # Analytics revenus
GET    /api/analytics/performance/         # Performance livreurs
GET    /api/analytics/zones/               # Heatmap zones
GET    /api/analytics/trends/              # Tendances temporelles
GET    /api/analytics/export/              # Export rapports
POST   /api/analytics/custom/              # Rapport personnalisé
```

### 🎯 Promotions & Marketing
```
GET    /api/promotions/                    # Liste promotions
POST   /api/promotions/                    # Créer promotion
GET    /api/promotions/{id}/               # Détails promotion
PUT    /api/promotions/{id}/               # Modifier promotion
DELETE /api/promotions/{id}/               # Supprimer promotion
POST   /api/promotions/{id}/activate/      # Activer promotion
POST   /api/promotions/{id}/deactivate/    # Désactiver promotion
GET    /api/promotions/{id}/usage/         # Statistiques usage
GET    /api/promotions/validate/{code}/    # Valider code promo
```

### 🎧 Support & Tickets
```
GET    /api/support/tickets/               # Liste tickets
POST   /api/support/tickets/               # Créer ticket
GET    /api/support/tickets/{id}/          # Détails ticket
PUT    /api/support/tickets/{id}/          # Modifier ticket
POST   /api/support/tickets/{id}/assign/   # Assigner ticket
POST   /api/support/tickets/{id}/close/    # Fermer ticket
GET    /api/support/tickets/{id}/messages/ # Messages ticket
POST   /api/support/tickets/{id}/messages/ # Ajouter message
GET    /api/support/stats/                 # Statistiques support
```

### 🔔 Notifications
```
GET    /api/notifications/                 # Liste notifications
POST   /api/notifications/                 # Envoyer notification
GET    /api/notifications/{id}/            # Détails notification
PUT    /api/notifications/{id}/read/       # Marquer lu
DELETE /api/notifications/{id}/            # Supprimer notification
POST   /api/notifications/mark-all-read/   # Tout marquer lu
GET    /api/notifications/preferences/     # Préférences utilisateur
PUT    /api/notifications/preferences/     # Modifier préférences
```

### 📋 Audit & Logs
```
GET    /api/audit/logs/                    # Journal d'audit
GET    /api/audit/logs/{id}/               # Détails log
GET    /api/audit/logs/export/             # Export logs
GET    /api/audit/stats/                   # Statistiques audit
GET    /api/audit/users/{id}/activity/     # Activité utilisateur
```

### ⚙️ Settings & Configuration
```
GET    /api/settings/                      # Configuration système
PUT    /api/settings/                      # Modifier configuration
GET    /api/settings/pricing/              # Grille tarifaire
PUT    /api/settings/pricing/              # Modifier tarifs
GET    /api/settings/zones/                # Zones de service
POST   /api/settings/zones/                # Créer zone
PUT    /api/settings/zones/{id}/           # Modifier zone
DELETE /api/settings/zones/{id}/           # Supprimer zone
```

### 🌐 Internationalization
```
GET    /api/i18n/languages/                # Langues disponibles
GET    /api/i18n/translations/             # Traductions
PUT    /api/i18n/translations/             # Modifier traductions
POST   /api/i18n/translations/import/      # Importer traductions
GET    /api/i18n/translations/export/      # Exporter traductions
GET    /api/i18n/content/{type}/{id}/      # Contenu localisé
PUT    /api/i18n/content/{type}/{id}/      # Modifier contenu localisé
```

## 📡 WebSocket Endpoints

```
/ws/notifications/                         # Notifications temps réel
/ws/orders/{order_id}/tracking/            # Suivi commande
/ws/chat/support/{ticket_id}/              # Chat support
/ws/admin/dashboard/                       # Métriques temps réel
```

## 📊 Exemples de Payloads

### Création d'utilisateur
```json
POST /api/users/
{
  "username": "john.doe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+226 70 12 34 56",
  "user_type": "client",
  "roles": ["client"],
  "metadata": {
    "source": "admin_creation",
    "notes": "Compte créé par admin"
  }
}
```

### Création de page CMS
```json
POST /api/cms/pages/
{
  "slug": "about-us",
  "title": "À propos de nous",
  "meta_title": "À propos - LivraFaso",
  "meta_description": "Découvrez l'histoire de LivraFaso",
  "content": {
    "blocks": [
      {
        "id": "hero-1",
        "type": "hero",
        "data": {
          "title": "Notre Histoire",
          "subtitle": "Depuis 2024, nous révolutionnons la livraison",
          "image": "/media/hero-about.jpg",
          "cta": {
            "text": "En savoir plus",
            "url": "#story"
          }
        }
      },
      {
        "id": "text-1",
        "type": "text",
        "data": {
          "content": "<p>LivraFaso est né d'une vision...</p>"
        }
      }
    ]
  },
  "template": "default",
  "language": "fr",
  "status": "draft"
}
```

### Création de promotion
```json
POST /api/promotions/
{
  "code": "WELCOME2024",
  "name": "Bienvenue 2024",
  "description": "Réduction de bienvenue pour nouveaux clients",
  "type": "percentage",
  "value": 20.00,
  "minimum_order_amount": 5000,
  "maximum_discount": 2000,
  "usage_limit": 1000,
  "user_limit": 1,
  "target_users": {
    "user_type": ["client"],
    "registration_date": {
      "after": "2024-01-01"
    }
  },
  "valid_from": "2024-01-01T00:00:00Z",
  "valid_until": "2024-12-31T23:59:59Z",
  "is_active": true
}
```

### Notification WebSocket
```json
{
  "type": "notification",
  "data": {
    "id": "notif-123",
    "title": "Nouvelle commande",
    "message": "Commande #CMD-2024-001 créée",
    "type": "order_created",
    "data": {
      "order_id": "order-uuid",
      "order_number": "CMD-2024-001",
      "client": "John Doe"
    },
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```
