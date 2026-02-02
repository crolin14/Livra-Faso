#!/usr/bin/env python3
"""
Générateur de nouveaux composants CSS pour LivraFaso
Crée des composants spécialisés avec le système CSS unifié
"""

def create_mission_components():
    """Crée des composants spécialisés pour les missions"""
    components = """
/* ===== COMPOSANTS MISSIONS LIVRAFASO ===== */

/* Mission Card - Carte de mission avec statut */
.lf-mission-card {
    background: var(--lf-white);
    border: 2px solid var(--lf-gray-200);
    border-radius: var(--lf-radius-2xl);
    padding: var(--lf-space-6);
    box-shadow: var(--lf-shadow-md);
    transition: all var(--lf-transition-normal);
    position: relative;
    overflow: hidden;
}

.lf-mission-card:hover {
    transform: translateY(-4px);
    box-shadow: var(--lf-shadow-xl);
    border-color: var(--lf-primary);
}

.lf-mission-card__header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--lf-space-4);
}

.lf-mission-card__title {
    font-family: var(--lf-font-display);
    font-size: var(--lf-text-xl);
    font-weight: 700;
    color: var(--lf-gray-900);
    margin: 0;
}

.lf-mission-card__price {
    font-size: var(--lf-text-2xl);
    font-weight: 700;
    color: var(--lf-primary);
}

.lf-mission-card__details {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--lf-space-3);
    margin-bottom: var(--lf-space-4);
}

.lf-mission-card__detail {
    display: flex;
    align-items: center;
    gap: var(--lf-space-2);
    font-size: var(--lf-text-sm);
    color: var(--lf-gray-600);
}

.lf-mission-card__actions {
    display: flex;
    gap: var(--lf-space-3);
    margin-top: var(--lf-space-4);
}

/* Priority Indicator */
.lf-mission-card--urgent {
    border-left: 4px solid var(--lf-error);
}

.lf-mission-card--high {
    border-left: 4px solid var(--lf-warning);
}

.lf-mission-card--normal {
    border-left: 4px solid var(--lf-primary);
}

/* Dashboard Stats Card */
.lf-dashboard-stat {
    background: linear-gradient(135deg, var(--lf-white) 0%, var(--lf-gray-50) 100%);
    border: 1px solid var(--lf-gray-200);
    border-radius: var(--lf-radius-2xl);
    padding: var(--lf-space-8);
    text-align: center;
    transition: all var(--lf-transition-normal);
    position: relative;
    overflow: hidden;
}

.lf-dashboard-stat::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: var(--lf-gradient-primary);
}

.lf-dashboard-stat:hover {
    transform: translateY(-6px);
    box-shadow: var(--lf-shadow-xl);
}

.lf-dashboard-stat__number {
    font-size: var(--lf-text-5xl);
    font-weight: 700;
    color: var(--lf-primary);
    margin-bottom: var(--lf-space-2);
    line-height: 1;
}

.lf-dashboard-stat__label {
    font-size: var(--lf-text-base);
    font-weight: 600;
    color: var(--lf-gray-700);
    margin-bottom: var(--lf-space-1);
}

.lf-dashboard-stat__change {
    font-size: var(--lf-text-sm);
    font-weight: 500;
}

.lf-dashboard-stat__change--positive {
    color: var(--lf-success);
}

.lf-dashboard-stat__change--negative {
    color: var(--lf-error);
}

/* User Profile Card */
.lf-profile-card {
    background: var(--lf-white);
    border-radius: var(--lf-radius-2xl);
    box-shadow: var(--lf-shadow-lg);
    overflow: hidden;
    transition: all var(--lf-transition-normal);
}

.lf-profile-card__header {
    background: var(--lf-gradient-primary);
    padding: var(--lf-space-8);
    text-align: center;
    color: var(--lf-white);
}

.lf-profile-card__avatar {
    width: 80px;
    height: 80px;
    border-radius: var(--lf-radius-full);
    border: 4px solid rgba(255, 255, 255, 0.3);
    margin: 0 auto var(--lf-space-4);
}

.lf-profile-card__name {
    font-size: var(--lf-text-2xl);
    font-weight: 700;
    margin-bottom: var(--lf-space-1);
}

.lf-profile-card__role {
    font-size: var(--lf-text-base);
    opacity: 0.9;
}

.lf-profile-card__body {
    padding: var(--lf-space-6);
}

.lf-profile-card__stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--lf-space-4);
    text-align: center;
}

.lf-profile-card__stat-number {
    font-size: var(--lf-text-xl);
    font-weight: 700;
    color: var(--lf-primary);
}

.lf-profile-card__stat-label {
    font-size: var(--lf-text-sm);
    color: var(--lf-gray-600);
}

/* Notification Toast */
.lf-toast {
    position: fixed;
    top: var(--lf-space-6);
    right: var(--lf-space-6);
    background: var(--lf-white);
    border-radius: var(--lf-radius-xl);
    box-shadow: var(--lf-shadow-xl);
    padding: var(--lf-space-4) var(--lf-space-6);
    display: flex;
    align-items: center;
    gap: var(--lf-space-3);
    z-index: 1000;
    transform: translateX(100%);
    transition: transform var(--lf-transition-normal);
}

.lf-toast--show {
    transform: translateX(0);
}

.lf-toast--success {
    border-left: 4px solid var(--lf-success);
}

.lf-toast--error {
    border-left: 4px solid var(--lf-error);
}

.lf-toast--warning {
    border-left: 4px solid var(--lf-warning);
}

.lf-toast__icon {
    width: 24px;
    height: 24px;
    flex-shrink: 0;
}

.lf-toast__content {
    flex: 1;
}

.lf-toast__title {
    font-weight: 600;
    color: var(--lf-gray-900);
    margin-bottom: var(--lf-space-1);
}

.lf-toast__message {
    font-size: var(--lf-text-sm);
    color: var(--lf-gray-600);
}

/* Loading Spinner */
.lf-spinner {
    width: 40px;
    height: 40px;
    border: 4px solid var(--lf-gray-200);
    border-top: 4px solid var(--lf-primary);
    border-radius: var(--lf-radius-full);
    animation: lf-spin 1s linear infinite;
    margin: var(--lf-space-4) auto;
}

.lf-spinner--sm {
    width: 20px;
    height: 20px;
    border-width: 2px;
}

.lf-spinner--lg {
    width: 60px;
    height: 60px;
    border-width: 6px;
}

/* Progress Bar */
.lf-progress {
    background: var(--lf-gray-200);
    border-radius: var(--lf-radius-full);
    height: 8px;
    overflow: hidden;
}

.lf-progress__bar {
    height: 100%;
    background: var(--lf-gradient-primary);
    border-radius: var(--lf-radius-full);
    transition: width var(--lf-transition-normal);
}

.lf-progress--success .lf-progress__bar {
    background: var(--lf-success);
}

.lf-progress--warning .lf-progress__bar {
    background: var(--lf-warning);
}

.lf-progress--error .lf-progress__bar {
    background: var(--lf-error);
}

/* Responsive */
@media (max-width: 768px) {
    .lf-mission-card__details {
        grid-template-columns: 1fr;
    }
    
    .lf-mission-card__actions {
        flex-direction: column;
    }
    
    .lf-profile-card__stats {
        grid-template-columns: 1fr;
    }
    
    .lf-toast {
        top: var(--lf-space-4);
        right: var(--lf-space-4);
        left: var(--lf-space-4);
        transform: translateY(-100%);
    }
    
    .lf-toast--show {
        transform: translateY(0);
    }
}
"""
    return components

def create_component_examples():
    """Crée des exemples d'utilisation des nouveaux composants"""
    examples = """# NOUVEAUX COMPOSANTS LIVRAFASO

## 🎯 Mission Card

```html
<div class="lf-mission-card lf-mission-card--urgent">
    <div class="lf-mission-card__header">
        <h3 class="lf-mission-card__title">Livraison urgente centre-ville</h3>
        <span class="lf-mission-card__price">25,000 FCFA</span>
    </div>
    
    <div class="lf-mission-card__details">
        <div class="lf-mission-card__detail">
            <span>📍</span>
            <span>Ouagadougou → Bobo-Dioulasso</span>
        </div>
        <div class="lf-mission-card__detail">
            <span>📦</span>
            <span>Colis fragile - 2.5kg</span>
        </div>
        <div class="lf-mission-card__detail">
            <span>⏰</span>
            <span>Avant 18h aujourd'hui</span>
        </div>
        <div class="lf-mission-card__detail">
            <span>🚗</span>
            <span>Véhicule requis</span>
        </div>
    </div>
    
    <span class="lf-badge lf-status--pending">En attente</span>
    
    <div class="lf-mission-card__actions">
        <button class="lf-btn lf-btn--primary">Postuler</button>
        <button class="lf-btn lf-btn--secondary">Détails</button>
    </div>
</div>
```

## 📊 Dashboard Stats

```html
<div class="lf-dashboard-stat">
    <div class="lf-dashboard-stat__number">127</div>
    <div class="lf-dashboard-stat__label">Missions terminées</div>
    <div class="lf-dashboard-stat__change lf-dashboard-stat__change--positive">
        +12% ce mois
    </div>
</div>
```

## 👤 Profile Card

```html
<div class="lf-profile-card">
    <div class="lf-profile-card__header">
        <img src="/static/images/avatar.jpg" alt="Avatar" class="lf-profile-card__avatar">
        <h2 class="lf-profile-card__name">Amadou Traoré</h2>
        <p class="lf-profile-card__role">Livreur Expert</p>
    </div>
    
    <div class="lf-profile-card__body">
        <div class="lf-profile-card__stats">
            <div>
                <div class="lf-profile-card__stat-number">4.8</div>
                <div class="lf-profile-card__stat-label">Note</div>
            </div>
            <div>
                <div class="lf-profile-card__stat-number">156</div>
                <div class="lf-profile-card__stat-label">Missions</div>
            </div>
            <div>
                <div class="lf-profile-card__stat-number">98%</div>
                <div class="lf-profile-card__stat-label">Succès</div>
            </div>
        </div>
    </div>
</div>
```

## 🔔 Toast Notifications

```html
<div class="lf-toast lf-toast--success lf-toast--show">
    <div class="lf-toast__icon">✅</div>
    <div class="lf-toast__content">
        <div class="lf-toast__title">Mission acceptée</div>
        <div class="lf-toast__message">Vous avez été sélectionné pour cette livraison</div>
    </div>
</div>
```

## ⏳ Loading & Progress

```html
<!-- Spinner -->
<div class="lf-spinner"></div>

<!-- Progress Bar -->
<div class="lf-progress">
    <div class="lf-progress__bar" style="width: 75%"></div>
</div>
```

## 🎨 JavaScript pour les Toasts

```javascript
function showToast(type, title, message) {
    const toast = document.createElement('div');
    toast.className = `lf-toast lf-toast--${type}`;
    toast.innerHTML = `
        <div class="lf-toast__icon">${type === 'success' ? '✅' : type === 'error' ? '❌' : '⚠️'}</div>
        <div class="lf-toast__content">
            <div class="lf-toast__title">${title}</div>
            <div class="lf-toast__message">${message}</div>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // Animer l'apparition
    setTimeout(() => toast.classList.add('lf-toast--show'), 100);
    
    // Auto-supprimer après 5 secondes
    setTimeout(() => {
        toast.classList.remove('lf-toast--show');
        setTimeout(() => document.body.removeChild(toast), 300);
    }, 5000);
}

// Utilisation
showToast('success', 'Mission terminée', 'Félicitations ! Votre livraison a été validée.');
```
"""
    return examples

def main():
    """Génère les nouveaux composants"""
    print("🎨 CRÉATION DE NOUVEAUX COMPOSANTS CSS")
    print("=" * 40)
    
    # 1. Créer les composants CSS
    components_css = create_mission_components()
    
    # Ajouter au fichier CSS unifié
    with open('static/css/livrafaso-unified.css', 'a', encoding='utf-8') as f:
        f.write('\n\n')
        f.write(components_css)
    
    print("✅ Composants ajoutés à livrafaso-unified.css")
    
    # 2. Créer les exemples
    examples = create_component_examples()
    with open('NOUVEAUX_COMPOSANTS_EXEMPLES.md', 'w', encoding='utf-8') as f:
        f.write(examples)
    
    print("✅ Exemples créés: NOUVEAUX_COMPOSANTS_EXEMPLES.md")
    
    print()
    print("🎉 NOUVEAUX COMPOSANTS CRÉÉS!")
    print("📋 Composants disponibles:")
    print("• lf-mission-card (cartes de missions)")
    print("• lf-dashboard-stat (statistiques)")
    print("• lf-profile-card (profils utilisateurs)")
    print("• lf-toast (notifications)")
    print("• lf-spinner (chargement)")
    print("• lf-progress (barres de progression)")
    
    return True

if __name__ == "__main__":
    main()
