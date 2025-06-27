# Présentation du projet

## Introduction - 1min

**Contenu du projet :**  Bonjour, notre projet développe un tableau de bord interactif pour suivre en temps réel l'activité hospitalière : arrivées de patients, pathologies et disponibilité des médecins. Nous avons utilisé l'IA pour déterminer les périodes où l'hôpital risque d'être saturé.

---

**Objectifs du projet :**  L'objectif final de notre projet est de créer un outil qui aide les gestionnaires d'hopitaux à mieux organiser les ressources, anticiper les moments de forte affluence et optimiser la prise en charge des patients en s'appuyant sur les données réelles de leurs hôpital.

**Rendu final :** Nous mettons donc à disposition un outil de visualisation de données et d'anticipation de cas de crises utilisable quasi-immédiatement dans les hopitaux en "branchant" notre implémentation à la base de donnée de l'hopital.

## Répartition du travail - 1min - Lukas 

Arsène a pris en charge la gestion des données, notamment la mise en place de la base de données SQLite et les échanges entre la simulation et le stockage.

Carl a travaillé sur les aspects mathématiques du projet, en participant à la modélisation des processus hospitaliers.

Maxence a également contribué à la simulation numérique, en codant les algorithmes permettant de reproduire le fonctionnement d’un hôpital.

Je me suis occupé du développement du dashboard, en assurant l’affichage web des données et l’intégration graphique de l’interface.


## Mathématiques du modéle - 1min - Carl

**Hypothèses du modèle**
Notre modèle consiste en une discrétisation du temps nous permettant de déterminer l'état de l'hopital à une période future en fonction de l'état actuel et de processus aléatoires.
### Hypothèse 1 :
$\text{L'écart entre deux arrivées de patients suit une loi de Poisson.}$
\
Ce résultat est connu pour être issu d'observations faites pour des stations recevant des appels téléphoniques, et convient également pour des arrivées en hôpital.


On note $ X \sim \mathcal{P}(\lambda) $\
Si $\space\forall n \in \mathbb{N}\space\space\space\space  \mathbb{P}(X=n) = \frac{\lambda^n}{n!}e^{-\lambda}$
### Hypothèse 2 :
$\text{Le pas de temps de la simulation doit être tel que :}$
$$dt \ll \frac{1}{\lambda}$$
Cette condition garanti que la loi simulée est effectivement une loi de poisson.
Si dt est trop grand, le temps minimal entre deux arrivées est donc de $dt$ et la loi n'est plus un loi de poisson.

Sous ces hypothèses, les patients arrivent à des intervalles aléatoires tirés selon une loi de Poisson, et sont ensuite libérés avec une probabilité dépenant de la maladie pour laquelle ils consultent, après avoir consulté le médecin adéquat.

## Simalution numérique - 2min - Maxence

Étant donné que nous avons rencontré beaucoup de difficultés pour trouver des données propres et utilisable pour notre projet. Notre encadrant nous a invité a créer notre propre simulation de donnée pour avoir une base sur laquelle s’appuyer. Cette approche nous permet de créer un dataset cohérent et contrôlé reproduisant fidèlement les dynamiques hospitalières réelles. L’objectif était simple, nous devions simuler

- 26 maladies les plus fréquentes dans les hôpitaux avec leurs saisonnalité et leurs durées moyennes de traitement
- Processus stochastiques d'arrivées des patiens
- Médecins spécialisés avec files d'attente dédiées
- la gestion des flux avec de le modéle de file d’attente que Carl vous a présenté

Pour ce faire, notre simulation, faite sur Python, utilise le framework SimPy pour implémenter un modèle à événements discrets avec un pas temporel fixe d'une minute. Et donc chaque minute, on va avoir une mse à jour de nos 3 classes  : **Hopital, Médecin et Personne **. 


Concernant la classe **Médécin**, on y trouve que chaque médecin possède sa spécialité, sa propre file d'attente et son statut d'occupation, permettant une gestion réaliste des ressources.

Dans la classe **Personne**, on crée des arrivées de patients suivent une loi de Poisson avec paramètre λ configurable (patients/heure). Chaque patient se voit attribuer une pathologie selon une distribution pondérée qui varie selon la saisonnalité (26 maladies modélisées avec facteurs mensuels).

Dans la classe **Hopital**, on gére la simulation qui avance par pas de 1 minute, avec suivi horaire, journalier et mensuel. Les temps de traitement suivent des lois exponentielles basées sur les durées moyennes par pathologie.

Au sorti de la simulation, le système met à jour la bases de données: **données horaires détaillées, statistiques journalières par pathologie, traitements effectués, bilans mensuels et métriques globales de performance hospitalière** qui seront transféré à Arsene et Lukas pour le dashboard.



## Gestion des datas - 2min - Arsène

Notre projet utilise *SQLite* comme base de données principale, optimisée pour les performances avec des techniques avancées :
    - Mode WAL pour l'accès concurrent
    - Système de cache et d'optimisations I/O
    - Structure modulaire avec 8 tables spécialisées

- Collecte de Données Multi-Dimensionnelle
- Nous capturons 3 niveaux de granularité/détail:
    - États hospitaliers (patients, médecins, temps d'attente) - temps réel
    - Traitements patients (spécialité, maladie, temps) - granulaire
    - Événements détaillés (arrivées, assignations) - trace complète

Ensuite pour que ces données soient accessibles depuis l'interface, mise en place d'une API RESTful avec Flask, qui permet ensuite à Lukas, qui gère l'app web en tant que telle, de posséder les données avec un format "standardiser", pour ensuite implémentater la logique de visualisation.

## Dashboard - 2min - Lukas

Tkinter pour un affichage local :

  -J’ai utilisé Tkinter pour afficher les premières données de simulation.

  -Cela m’a permis de valider rapidement le format et la mise à jour en temps réel des données.

Migration vers Dash pour une version web :

  -J’ai ensuite développé une première version du dashboard avec Dash.

  -L’objectif était d’avoir une interface web interactive et accessible.

Structuration et enrichissement du dashboard :

  -J’ai organisé le dashboard en plusieurs pages et ajouté des graphes plus complets.

  -Cela a permis une visualisation plus claire et plus ciblée des différents aspects de l’hôpital.

Connexion à l’API Flask pour la simulation :

  -J’ai intégré une API Flask pour récupérer les données du moteur de simulation.

  -Ainsi, les données affichées sont toujours synchronisées avec l’état de la simulation.

Intégration d’outils UI modernes :

  -J’ai utilisé Bootstrap pour le design et Chart.js pour les graphiques.

  -Le but était d’obtenir une interface responsive, moderne et agréable à utiliser.


## Machine Learning - 1min - Carl

Après avoir testé des méthodes d'apprentissage comme les k plus proches voisins ou encore des régressions par réseaux de neurones, nous nous sommes finalement tournés vers une approche d'ensemble mieux adaptée à notre contexte hospitalier.

Notre système combine Random Forest et Gradient Boosting, deux méthodes d'ensemble qui se complètent parfaitement pour notre cas d'usage.

### Random Forest pour la Classification des Dangers
La partie apprentissage de notre algorithme consiste à ajuster, en fonction des données historiques, les paramètres de nos arbres de décision. Chaque arbre apprend à reconnaître des patterns spécifiques :
    - Patterns temporels (heures de pointe, week-ends)
    - Corrélations entre charge patient et disponibilité médecin
    - Seuils critiques propres à chaque type de danger

Ainsi, pour chaque situation hospitalière, et en fonction des contextes temporels, les 100 arbres votent ensemble pour déterminer la probabilité de chaque type de danger.

### Gradient Boosting pour les Prédictions Numériques
Cette méthode ajuste séquentiellement ses paramètres en corrigeant les erreurs des prédicteurs précédents. Elle est adaptée pour prédire les valeurs continues comme les temps d'attente futurs ou l'affluence de patients.

En simulant un échantillon conséquent de données (qui en pratique serait disponible dans un hôpital), nous pouvons ajuster au mieux les paramètres de nos modèles pour décrire de manière précise l'évolution des situations critiques.
La validation croisée à 5 plis nous assure une généralisation robuste, tandis que la gestion automatique des déséquilibres de classes garantit une détection fiable même des événements rares.


## Difficultés rencontrées - 2min - Lukas + qqn d'autre ?

## Présentation du projet (ie dashboard)
