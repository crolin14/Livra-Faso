# LIVRAFASO - LOGIQUE MÉTIER COMPLÈTE
## Plateforme de Livraison Digitale pour le Burkina Faso et l'Afrique de l'Ouest

---

## 1. ACTEURS DU SYSTÈME

### 1.1 CLIENT (Particulier/Entreprise)
**Permissions et Capacités :**
- Créer et gérer des missions de livraison
- Suivre en temps réel l'état des livraisons
- Consulter l'historique des missions
- Évaluer les livreurs après livraison
- Gérer les moyens de paiement
- Accéder au support client
- Recevoir notifications SMS/Push/Email

**Types de Clients :**
- **Particulier** : Accès aux services de base
- **Entreprise Starter** : Tableau de bord basique, 50 missions/mois
- **Entreprise Premium** : Tableau de bord avancé, missions illimitées, API, support prioritaire

### 1.2 LIVREUR
**Permissions et Capacités :**
- Consulter les missions disponibles dans sa zone
- Postuler aux missions
- Gérer son statut de disponibilité
- Mettre à jour sa géolocalisation
- Gérer le statut des missions assignées
- Consulter l'historique et les gains
- Recevoir notifications de nouvelles missions

**Types de Livreurs :**
- **Livreur Gratuit** : Commission 15% sur chaque livraison, accès limité
- **Livreur Premium** : Abonnement mensuel, commission réduite 8%, priorité sur missions, assurance

### 1.3 ENTREPRISE
**Permissions et Capacités :**
- Créer des missions en masse
- Gérer une équipe de livreurs dédiés
- Accéder aux tableaux de bord analytiques
- Intégrer via API (Premium uniquement)
- Gérer les abonnements et facturations
- Support client prioritaire (Premium)

### 1.4 ADMINISTRATEUR SYSTÈME
**Permissions et Capacités :**
- Gestion complète des utilisateurs
- Modération des contenus et évaluations
- Gestion des litiges et incidents
- Configuration des tarifs et zones
- Accès aux analytics globaux
- Gestion des paiements et commissions
- Support technique avancé

---

## 2. PROCESSUS DE BASE - FLUX COMPLET DE LIVRAISON

### 2.1 Phase de Création de Mission
1. **Initiation par le Client**
   - Sélection du type de service (Standard, Courses pour moi, Envoi de colis)
   - Saisie des adresses de ramassage et livraison
   - Définition des détails du colis (poids, dimensions, fragilité)
   - Calcul automatique du prix selon les règles tarifaires
   - Sélection des options premium (assurance, livraison express)

2. **Validation et Paiement**
   - Confirmation des détails de la mission
   - Sélection du moyen de paiement
   - Pré-autorisation ou paiement immédiat
   - Création de la mission avec statut "En attente"

### 2.2 Phase d'Attribution
1. **Diffusion de la Mission**
   - Notification aux livreurs éligibles dans la zone
   - Priorité aux livreurs premium
   - Affichage dans la liste des missions disponibles

2. **Candidature des Livreurs**
   - Les livreurs postulent à la mission
   - Le client peut consulter les profils et évaluations
   - Attribution automatique ou manuelle selon les préférences

3. **Confirmation d'Attribution**
   - Notification au livreur sélectionné
   - Mise à jour du statut : "Acceptée"
   - Notification au client avec détails du livreur

### 2.3 Phase d'Exécution
1. **Ramassage**
   - Livreur se rend au point de ramassage
   - Mise à jour géolocalisation en temps réel
   - Confirmation de récupération du colis
   - Photo du colis (optionnel)
   - Statut : "En cours de ramassage" → "Ramassé"

2. **Transport**
   - Suivi GPS en temps réel
   - Notifications automatiques d'étapes
   - Statut : "En transit"
   - Estimation temps d'arrivée mise à jour

3. **Livraison**
   - Arrivée au point de livraison
   - Confirmation de livraison
   - Signature électronique ou photo
   - Statut : "Livré"

### 2.4 Phase de Finalisation
1. **Confirmation de Livraison**
   - Notification au client
   - Déclenchement du paiement final
   - Calcul et distribution des commissions

2. **Évaluation**
   - Client évalue le livreur (1-5 étoiles)
   - Livreur peut évaluer le client
   - Commentaires optionnels

3. **Clôture**
   - Archivage de la mission
   - Mise à jour des statistiques
   - Génération des rapports

---

## 3. RÈGLES DE TARIFICATION

### 3.1 Calcul de Base par Distance
```
Distance ≤ 3 km     : 500 FCFA
3 km < Distance ≤ 6 km    : 800 FCFA
6 km < Distance ≤ 10 km   : 1200 FCFA
10 km < Distance ≤ 15 km  : 2000 FCFA
15 km < Distance ≤ 20 km  : 3000 FCFA
20 km < Distance ≤ 30 km  : 4500 FCFA
Distance > 30 km    : 1000 + (Distance - 30) × 150 FCFA
```

### 3.2 Multiplicateurs par Type de Service
- **Livraison Standard** : Tarif de base
- **Courses pour moi** : Tarif de base × 1.2
- **Envoi de colis** : Tarif de base × 1.1
- **Livraison Express** : Tarif de base × 1.5

### 3.3 Options Premium
- **Assurance colis** : +200 FCFA (jusqu'à 50,000 FCFA de couverture)
- **Livraison Fast** : +300 FCFA (livraison sous 30 minutes)
- **Livraison programmée** : +100 FCFA
- **Signature requise** : +50 FCFA

### 3.4 Réductions et Promotions
- **Abonnement Entreprise Starter** : -5% sur toutes les livraisons
- **Abonnement Entreprise Premium** : -10% sur toutes les livraisons
- **Volume mensuel > 100 missions** : -15% supplémentaire
- **Première utilisation** : -20% (maximum 500 FCFA)

---

## 4. GESTION DES RÔLES ET ABONNEMENTS

### 4.1 Abonnements Entreprise

#### Starter (15,000 FCFA/mois)
- Jusqu'à 50 missions/mois
- Tableau de bord basique
- Support standard
- Réduction 5% sur livraisons
- Historique 3 mois

#### Premium (35,000 FCFA/mois)
- Missions illimitées
- Tableau de bord avancé avec analytics
- Intégration API
- Support prioritaire
- Réduction 10% sur livraisons
- Historique illimité
- Livreurs dédiés (optionnel)

### 4.2 Abonnement Livreur Premium (5,000 FCFA/mois)
- Commission réduite à 8% (vs 15% gratuit)
- Priorité sur les missions
- Assurance responsabilité civile
- Support prioritaire
- Outils de gestion avancés
- Formation continue

### 4.3 Règles d'Accès par Rôle
- **Particulier** : Accès complet aux fonctionnalités de base
- **Entreprise non-abonnée** : Tarifs majorés +20%, fonctionnalités limitées
- **Livreur non-vérifié** : Accès limité aux missions de faible valeur (<10,000 FCFA)
- **Utilisateur suspendu** : Accès lecture seule, pas de nouvelles missions

---

## 5. SYSTÈME DE SUIVI ET NOTIFICATIONS

### 5.1 Déclencheurs d'Événements

#### Pour le Client
- **Création mission** : SMS + Push confirmation
- **Mission acceptée** : SMS + Push avec détails livreur
- **Ramassage effectué** : Push notification
- **En transit** : Push avec lien de suivi
- **Livraison effectuée** : SMS + Push + Email
- **Problème détecté** : Appel + SMS urgent

#### Pour le Livreur
- **Nouvelle mission disponible** : Push notification
- **Mission attribuée** : SMS + Push
- **Instructions spéciales** : Push notification
- **Paiement reçu** : SMS confirmation
- **Évaluation reçue** : Push notification

#### Pour l'Entreprise
- **Rapport quotidien** : Email automatique
- **Seuil missions atteint** : Email + Push
- **Problème sur mission** : Email + SMS
- **Facture générée** : Email avec PDF

### 5.2 Canaux de Communication
- **SMS** : Notifications critiques (Orange, Moov)
- **Push Notifications** : Mises à jour en temps réel
- **Email** : Rapports et documents
- **In-App** : Notifications contextuelles

---

## 6. GESTION DES INCIDENTS

### 6.1 Types d'Incidents

#### Incidents Livreur
- **Retard** : >30 min après estimation
  - Notification automatique client
  - Pénalité 500 FCFA sur commission livreur
  - Mise à jour ETA automatique

- **Colis endommagé**
  - Photo obligatoire
  - Notification immédiate client
  - Activation assurance si souscrite
  - Enquête automatique

- **Livreur indisponible**
  - Réattribution automatique
  - Notification client du changement
  - Pénalité livreur selon historique

#### Incidents Client
- **Adresse incorrecte**
  - Frais supplémentaires 500 FCFA
  - Recalcul itinéraire
  - Confirmation nouvelle adresse

- **Destinataire absent**
  - 3 tentatives gratuites
  - Frais stockage 200 FCFA/jour après 48h
  - Retour expéditeur après 7 jours

- **Refus de livraison**
  - Paiement intégral maintenu
  - Frais retour à la charge du client

### 6.2 Processus de Résolution
1. **Détection automatique** via GPS/temps
2. **Notification immédiate** parties concernées
3. **Escalade support** si non résolu en 1h
4. **Compensation automatique** selon barème
5. **Suivi satisfaction** post-résolution

---

## 7. CALCUL DES COMMISSIONS ET PAIEMENTS

### 7.1 Structure des Commissions

#### Commission Plateforme
- **Livreur Gratuit** : 15% du prix de livraison
- **Livreur Premium** : 8% du prix de livraison
- **Entreprise Starter** : 3% de commission plateforme
- **Entreprise Premium** : 2% de commission plateforme

#### Répartition des Paiements
```
Prix Total Livraison = Prix Base + Options + Taxes
├── Commission Plateforme (8-15%)
├── Commission Paiement (2-3% selon moyen)
├── Taxes (18% TVA sur commission)
└── Montant Livreur (reste)
```

### 7.2 Processus de Paiement

#### Paiement Client
1. **Pré-autorisation** à la création de mission
2. **Capture définitive** à la livraison confirmée
3. **Remboursement automatique** en cas d'annulation

#### Paiement Livreur
1. **Calcul automatique** à la livraison
2. **Virement quotidien** pour Premium (J+1)
3. **Virement hebdomadaire** pour Gratuit (J+7)
4. **Seuil minimum** : 5,000 FCFA

### 7.3 Moyens de Paiement Intégrés

#### Orange Money
- Commission : 2%
- Délai : Instantané
- Limite : 500,000 FCFA/transaction

#### Moov Money
- Commission : 2.5%
- Délai : Instantané
- Limite : 300,000 FCFA/transaction

#### Wave
- Commission : 1.5%
- Délai : Instantané
- Limite : 1,000,000 FCFA/transaction

#### Cartes Bancaires (Visa/Mastercard)
- Commission : 3%
- Délai : 24-48h
- Limite : 2,000,000 FCFA/transaction

---

## 8. WORKFLOWS DE GÉOLOCALISATION ET SUIVI TEMPS RÉEL

### 8.1 Géolocalisation Livreur
- **Mise à jour** : Toutes les 30 secondes en mission
- **Précision requise** : <10 mètres
- **Historique** : Conservation 30 jours
- **Zones interdites** : Blocage automatique

### 8.2 Suivi Client
- **Interface web** : Carte temps réel
- **Application mobile** : Push notifications étapes
- **SMS** : Liens de suivi
- **Estimation arrivée** : Algorithme prédictif

### 8.3 Optimisation des Trajets
- **Calcul itinéraire** : API Google Maps/OpenStreetMap
- **Évitement embouteillages** : Données trafic temps réel
- **Points de passage** : Optimisation multi-livraisons
- **Zones de livraison** : Géofencing automatique

---

## 9. RÈGLES MÉTIER SPÉCIFIQUES

### 9.1 Validation des Missions
- **Poids maximum** : 50kg par colis
- **Dimensions maximum** : 100cm × 80cm × 60cm
- **Valeur déclarée** : Maximum 500,000 FCFA sans assurance premium
- **Produits interdits** : Liste noire automatique

### 9.2 Gestion des Zones
- **Zone urbaine** : Ouagadougou, Bobo-Dioulasso
- **Zone périurbaine** : Rayon 30km centres urbains
- **Zone rurale** : Tarification spéciale +50%
- **Zones interdites** : Mise à jour dynamique

### 9.3 Horaires de Service
- **Standard** : 6h00 - 22h00
- **Express** : 6h00 - 20h00
- **Nuit** : 22h00 - 6h00 (+100% tarif)
- **Dimanche** : Service limité (+20% tarif)

### 9.4 Système de Qualité
- **Note minimum livreur** : 3.5/5 pour rester actif
- **Taux de réussite** : >95% requis
- **Temps de réponse** : <5 minutes pour accepter mission
- **Formation continue** : Obligatoire livreurs premium

---

## 10. INTÉGRATIONS TECHNIQUES

### 10.1 APIs Externes
- **Paiement mobile** : Orange Money, Moov Money, Wave
- **Géolocalisation** : Google Maps, OpenStreetMap
- **SMS** : Opérateurs locaux (Orange, Moov)
- **Email** : Service SMTP sécurisé

### 10.2 Webhooks et Événements
- **Statut mission** : Notification temps réel
- **Paiement confirmé** : Déclenchement automatique
- **Géolocalisation** : Mise à jour continue
- **Incidents** : Alertes immédiates

### 10.3 Sécurité et Conformité
- **Chiffrement** : AES-256 pour données sensibles
- **Authentification** : OAuth 2.0 + 2FA
- **Audit trail** : Traçabilité complète
- **RGPD** : Conformité protection données

---

*Cette logique métier constitue la source de vérité pour l'implémentation technique de la plateforme LivraFaso. Elle doit être mise à jour régulièrement selon l'évolution des besoins métier et réglementaires.*
