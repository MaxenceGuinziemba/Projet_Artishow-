# Tableau de bord de simulation hospitalière

Un tableau de bord web complet pour surveiller et analyser les données de simulation hospitalière.

## Fonctionnalités

### Tableau de bord multi-pages

- **Page Analytique** : Graphiques temporels et statistiques complètes
- **Page Incidents** : Surveillance des alertes et analyse des périodes problématiques
- **Page Temps réel** : Lecture de la simulation avec vitesse configurable

### Capacités analytiques

- Flux de patients dans le temps (total, traités, en attente)
- Utilisation des médecins et métriques de performance
- Modèles horaires de traitement et analyse des temps d’attente
- Visualisation de la répartition des maladies
- Tendances de performance quotidienne
- Contrôles interactifs des graphiques (afficher/masquer séries, plages temporelles, types de graphiques)

### Surveillance des incidents

- Détection des périodes de forte attente
- Alertes de sur-utilisation des médecins
- Suivi du plus long temps d’attente patient
- Chronologie des événements de simulation
- Analyse des motifs d’incidents par heure et type

### Lecture temps réel de la simulation

- Lecture à vitesse variable (du temps réel à 1 mois = 1 minute)
- Surveillance en direct de l’état de l’hôpital
- Fil d’événements récents
- Suivi de l’état des médecins
- Système d’alertes actives
- Contrôles de lecture et navigation temporelle

## Installation

1. **Installer les dépendances**

   ```bash
   pip install -r requirements.txt
   ```

2. **Vérifier l’existence de la base de données**

   ```bash
   # Lancez d’abord une simulation pour générer des données
   python main.py --simulation --doctors=25 --rate=18 --minutes=1440
   ```

## Utilisation

### Démarrage rapide

```bash
# Lancer le tableau de bord directement
python dashboard.py

# Ou via le script principal
python main.py --dashboard

# Port personnalisé
python main.py --dashboard --port=8080
```

### Workflow complet

```bash
# 1. Lancer une simulation pour générer des données
python main.py --simulation --doctors=30 --rate=20 --minutes=2880

# 2. Lancer le tableau de bord pour visualiser
python main.py --dashboard

# 3. Ouvrir le navigateur sur http://localhost:5000
```

### Points d’accès API

Le tableau de bord fournit des endpoints API REST pour l’accès aux données :

- `GET /api/simulations` - Liste toutes les simulations
- `GET /api/simulation/{id}/info` - Détails d’une simulation
- `GET /api/simulation/{id}/analytics` - Données analytiques
- `GET /api/simulation/{id}/incidents` - Incidents et alertes
- `GET /api/simulation/{id}/realtime` - Données temps réel pour la lecture
- `GET /api/simulation/{id}/timerange` - Plage temporelle disponible

## Architecture

```text
src/visualizations/
├── dashboard.py          # Application Flask et routes API
├── templates/            # Modèles HTML
│   ├── index.html       # Page principale de sélection de simulation
│   ├── analytics.html   # Tableau de bord analytique
│   ├── incidents.html   # Surveillance des incidents
│   ├── realtime.html    # Lecture temps réel
│   └── predictions.html # Page HTML pour l'affichage des prédictions
└── static/              # Ressources frontend
    ├── css/
    │   └── dashboard.css # Styles complets
    └── js/
        ├── dashboard.js  # Fonctionnalité principale
        ├── analytics.js  # Gestion des graphiques
        ├── incidents.js  # Analyse des incidents
        ├── realtime.js   # Moteur de lecture temps réel
        └── predictions.js # Prédictions et visualisation IA

### Fichiers supplémentaires
- `predictions.py` : Endpoints Flask pour les prédictions IA
```

## Pages du tableau de bord

- Liste toutes les simulations disponibles
- Affiche les statistiques et l’état des simulations
- Navigation rapide vers les autres pages
- Interface de sélection de simulation

### Analytique (/analytics/{sim_id})

- **Graphiques de flux de patients** : Suivi du nombre de patients dans le temps
- **Utilisation des médecins** : Suivi de l’efficacité et des périodes de forte activité
- **Modèles horaires** : Identification des pics de traitement
- **Répartition des maladies** : Graphiques en secteurs des pathologies traitées
- **Métriques quotidiennes** : Performances agrégées par jour
- **Tableau de performance des médecins** : Statistiques individuelles

### Incidents (/incidents/{sim_id})

- **Alertes de forte attente** : Périodes avec attente excessive
- **Incidents d’occupation** : Trop de médecins occupés
- **Chronologie des événements** : Événements de simulation (épidémies, catastrophes, etc.)
- **Pires cas patients** : Plus longs temps d’attente individuels
- **Analyse des motifs** : Fréquence des incidents par heure et type

### Temps réel (/realtime/{sim_id})

- **Contrôles de lecture** : Lecture/pause/arrêt avec sélection de vitesse
- **Métriques en direct** : Nombre actuel de patients et médecins
- **Graphiques d’activité** : Fenêtre glissante de 2h d’activité
- **Événements récents** : Fil en direct des événements
- **Statut des médecins** : Affectations en temps réel
- **Système d’alertes** : Avertissements actifs pour conditions problématiques

### Prédictions (/predictions/{sim_id})

- **Prédictions de dangers** : Affichage des risques de surcharge, d'attente excessive, de sous-effectif, etc.
- **Scores de danger** : Visualisation des scores de danger actuels et futurs (court, moyen, long terme)
- **Explications des modèles** : Affichage des variables influentes et des seuils critiques
- **Historique des alertes prédictives** : Liste des périodes où un danger a été anticipé par l'IA
- **Comparaison réel vs prédit** : Graphiques comparant les métriques réelles et les prédictions du modèle

## Personnalisation

### Ajouter de nouveaux graphiques

1. Ajouter un endpoint de données dans `dashboard.py`
2. Créer le graphique dans le fichier JavaScript correspondant
3. Mettre à jour le modèle HTML avec le conteneur du graphique

### Options de vitesse

- **Temps réel** : 1 minute = 1 minute
- **Rapide** : 1 minute = 1 seconde
- **Très rapide** : 1 heure = 1 seconde (par défaut)
- **Jour** : 1 jour = 1 seconde
- **Mois** : 1 mois = 1 minute

### Contrôles de graphiques

- Afficher/masquer des séries
- Filtrage par plage temporelle (24h, 7j, 30j, tout)
- Granularité des données (minute, heure, jour)
- Changement de type de graphique (ligne, barre, aire)

## Dépannage

### Problèmes courants

1. **Aucune simulation trouvée**
   - Lancez d’abord une simulation : `python main.py --simulation`
   - Vérifiez l’existence de la base : `data/hospital_sim.db`

2. **Le tableau de bord ne démarre pas**
   - Installez Flask : `pip install flask`
   - Vérifiez la disponibilité du port : essayez `--port=8080`

3. **Pas de données dans les graphiques**
   - Vérifiez que la simulation s’est bien terminée
   - Vérifiez la base avec un navigateur SQLite
   - Vérifiez que l’ID de simulation existe

4. **Problèmes de lecture temps réel**
   - Vérifiez que la simulation a des données hospital_state
   - Vérifiez que la plage temporelle est valide
   - Essayez différents réglages de vitesse

### Conseils de performance

- Utilisez les filtres temporels pour les grands jeux de données
- Diminuez la granularité des graphiques pour de meilleures performances
- Fermez les onglets inutilisés lors de longues lectures

## Développement

### Technologies frontend

- **Bootstrap 5** : Framework UI réactif
- **Chart.js** : Graphiques interactifs
- **Font Awesome** : Icônes et éléments visuels
- **JavaScript Vanilla** : Pas de framework lourd pour de meilleures performances

### Technologies backend

- **Flask** : Framework web léger
- **SQLite** : Requêtes et agrégation de données
- **Python** : Traitement des données et logique API

### Conception de l’API

- Endpoints REST avec réponses JSON cohérentes
- Gestion des erreurs avec messages explicites
- Paramètres de requête flexibles pour le filtrage
- Requêtes SQL efficaces avec surcharge minimale
