# SUIVI - ARTISHOW - IA MEDICAL

> Maxence GUINZIEMBA-PROKOP, Arsène MALLET, Carl MONNAERT, Lukas TABOURI

## 14/02

- Découverte du sujet et mise en place d'un plan d'action pour la réalisation du projet. Nous nous sommes mis d'accord sur language que nous allions utilisé pour la simulation (Python) et les bibliothèques utiles.

- **(Tout le monde)** Carl et Lukas commencé la première simulation assez rapide du problème tant dis que Maxence et Arsène ont commencé à faire des recherches bibliographiques pour comprendre comment avoir une simulation et un modèle mathématique qui s'approche de la réalité (structure.py).

## 18/02

- **(Carl)** La première modélisation a bien fonctionné, nous avons modélisé une seule maladie avec un certain taux de contagion, de mortalité et de "récupération". Cependant, elle rencontre deux problèmes majeures qu'il faudra corriger : une complexité qui devient trop importante au fil des jours et une mauvaise gestion des modèles mathématiques (ce qui est normal à ce stade).
- **(Maxence, Lukas)** C'est notre rôle de trouver et comprendre les mathématiques derriere la gestion des patients au sein d'un hôpital. Nous avons découvert une revue scientifique ("Modélisation d'un file d'attente" : [lien](https://math.univ-lyon1.fr/~alachal/serveurOT/files_attente.pdf)) et allons nous inspirer du modelé utilisé dans les centres d'appel ie la loi d'Erlang, nous sommes dans la phase de compréhension de ce modèle et de détermination des hypothèses que nous allons faire.
- De son côté, **(Arsène)** a trouvé des bases de données open source très intéressantes dans lequel on peut trouver le temps moyen que chaque patient attend dans l’hôpital, le nombre de lit, le nombre de patient qui reste plus de 3 mois. Et toutes ces informations sur les 15 dernières années.

## 20/02

- **(Tous)** : RDV avec M. Clemençon (encadrant du projet), pour se mettre au point sur le projet, et lui poser nos questions :
  - Q : *Quelle est le livrable attendu du projet ?*
    - R : MINIMUM -> simulation d'hôpital simple + dashboard visualisation | OBJECTIF -> Avancer le + possible simulation/dashboard dans le but d'avoir un prototype intéressant pour un service de santé.
  - Q : *Comment peut-on accéder à des données réelles pour comparer nos simulations/entraîner de futurs modèles de prédiction ?*
    - R: Impossible d'en avoir, sujet trop sensible, se contenter de faire des hypothèses les + "réalistes" possibles.
  - Mise en garde : Communication cruciale, Commencer par des choses simples puis incrémenter, Discuter de l'avancement fréquemment.
  - Proposition de ressources : *Processus ponctuel marqué*, Méthode de développement *agile*.

## 21/02

- **(Tous)** : mise en place du planning -> Affectation des "rôles"/tâches de chacun et de leur répartition dans l'avancement du projet.

## 04/03

- **(Carl)** : Nous avons réalisé des dernières modifications sur la simulation pour optimiser notre algorithme de simulation. Pour des questions de temps de calcul on se restreindra d’abord à un seul hôpital puis lorsque suffisamment de fonctionnalités seront disponibles nous ajouterons une dimension spatiale etc. Pour la suite, je suis en train de suivre le cours de typescript en accéléré et de me renseigner sur la manière d'afficher nos graphes en temps réel, soit en faisant tourner le code côté client, soit en interrogeant seulement une base de donnée que nous aurons rempli préalablement avec nos résultats de simulations.
- **(Maxence)** : Fin des recherches bibliographiques. J'ai trouvé la première modélisation assez simple de notre simulation. J'ai commencé à en parler avec Carl pour l'implémentation.

- **(Arsène)** : Choix du SQL pour les différentes base de donnees que nous allons construire avec nos simulations. Renseignement sur les différentes structures/architectures possibles de ces DBs.

- **(Lukas)** : Recherche bibliographique pour interface graphique, la première version sera faite avec la bibliothèque Tkinter et si elle ne suffit pas, passage possible sur une autre biblio comme Dash ou Streamlit.

## 11/03

- **(Carl)** : Code de la nouvelle méthode de simulation en boucle infinie, tests de plusieurs paramètres pour quantifier le débit d'arrivée et le débit de sortie. Pour la prochaine fois implémenter une interface graphique en lien avec Lukas pour afficher sur une page web

- **(Maxence)** : Mise en place de la simulation qui a fonctionné (Simulation_Rapide.py). Aucun problème de complexité et réflexion sur la manière de s'approcher un peu plus de la réalité.

- **(Arsène)** : Implémentation d'une interface SQL avec python (sqlite3), fonction pour créer une table avec des clés de différents types.

- **(Lukas)** : Implementation d'un premier dashboard tres simpliste.

## 18/03

- **(Maxence)** : Amélioration de la simulation en essayant de modifier certains paramètres comme le taux moyen d'arrivé en une heure, le nombre de médecin, le temps moyen de consultation.
- **(Carl)** : Travail en parallèle de Lukas sur un modèle de simulation en temps réel utilisable par l'interface graphique
- **(Lukas)** : Réflexion avec les autres parties du projet sur les données fournies, changement d'api pour le dashboard (Dash).
- **(Arsène)** : Interface simple avec une db sql terminée (création, insertion, requêtes). Ajout d'une documentation également. Discussion avec les autres membres du groupe pour connaître leur(s) besoin(s)/avancement en terme de données.

## 8/04

- **(Brainstorming/Tout le monde)** : On aimerait pouvoir créer une simulation qui génère une base de données et que cette data puisse être réutiliser à n'importe quelle moment pour poursuivre la simulation. L'objectif à long terme est de "stopper" la simulation. Modifier la base de données pour modéliser un événement et voir comment notre simulation réagit à ce changement.
- **(Maxence, Carl)** : Aujourd'hui, nous avons finalisé la simulation rapide que nous avions envisagé (Simulation_Rapide_2). Tout marche bien, mais certaines modifications devront être fait. On va pouvoir tester si la simulation et le travail de Arsène sur la base de données marchent bien ensemble. Pour la prochaine fois, il faudra perfectionner la gestion des médecins et comprendre pourquoi lorsque nos paramètres sont trop élevés, le processus de file d'attente ne fonctionne plus.
- **(Lukas)** : Lecture de la documentation de l'api Dash et premiers tests
- **(Arsène)** : Implémentation de l'interface spécifique à la base de données de l'hôpital.

## 11/04

- **(Tous)**On a décidé de complexifier notre simulation pour ajouter plusieurs maladies et plusieurs spécialités par médecins. On a décidé de tous chercher une méthode pour le faire pour ensuite le partager mardi et prendre celle qui marche le mieux.

## 15/04

- **(Maxence)** : J'ai rajouté à la simulation de Carl plusieurs maladies et plusieurs spécialités par médecins. Je me suis concentré aussi sur l'explication de chaque ligne de code (Simulation_Plusieurs_Médecins dans la V2) pour que Arsène et Lukas comprennent plus facilement la structure et puisse implémenter leurs parties.
- **(Carl)** : Mise en commun de notre simulation Avec Lukas et Arsène pour la production d'une interface graphique et d'un fichier CSV commun aux 4 éléments de notre groupe
- **(Lukas)** : Premier dashboard fonctionnel, decision avec mes pairs de stocker les données sous la forme d'un fichier csv.
- **(Arsène)** : Ajout d'une fonction de sauvegarde des données de la simulation, permettant par la suite l'affichage de différentes statistiques de la simulation.

## 16/04

**(Tous)**: Poursuite de la séance du 15/04 (avec les memes objectifs)

## 17/04

**(Tous)** : Nous avons eu un entretien avec notre encadrant Monsieur Clemençon pour parler de notre projet et de notre avancé. Cela a permis de redéfinir les objectifs du projet et notre avancée actuelle.

## 05/05

- **(Maxence)** : Mise en place des lignes directrices de groupe pour finaliser le projet.
- **(Carl)** : Brainstorming et début de rédaction du rapport sur les impacts environnementaux et sociaux de notre projet
- **(Lukas)** : Réglage des bugs du dashboard suite a la mise en commun des différentes parties (notamment le bon formatage des données)
- **(Arsène)** : Découverte de l'api InfluxDB pour le stockage de séries temporelles.

## Ascension

**(Tous)** : Nous avons chacun perfectionné nos codes. C'est à a dire que la simulation donne une belle base de donnees et que le dashboard répond bien à notre premiere attentes même si la partie ergonomique reste à améliorer.

## 12/05

- **(Maxence)** : J'ai transformé notre simulation qui se faisait évolue que sur une journée en une simulation qui se fait maintenant sur plusieurs mois, voir années( fichier dans le dossier V3 : Simulation_Mois_par_Mois.py). Cela permet de mettre en évidence les saisonnalités des maladies et la gestion des spécialités des médecins selon la période de l'année (ie plus de pneumologues en hiver).

## Entre séance 12/05 et 26/05

- **(Tous)** : Mise à niveau global du groupe sur les choses qu'il restait à faire, de l'avancement vis-à-vis du planning, de l'organisation du dernier mois de travail.

- **(Arsène)** : Finalement pas d'InfluxDB ou de framework spécial de données de séries temporel, mais utilisation d'une base de données SQLite, suffisant pour nos besoins. (1an de simulation ~130MB de données). Implémentation du système de persistence des simulations, avec possibilités de les continuer.

- **(Arsène & Lukas)** : Mise à jour du dashboard, ajouts des différentes pages, des différents graphs, implémentation API Simulation (Flask), implémentation framework JS de graphes et d'UI (Bootstrap + Chart.js).

- **(Tous)** : Premiers tests de modèles de machine-learning pour la prediction de l'état de l'hôpital.

- **(Tous)** : Suppression des V1,V2,V3 dans la branche principal, tous le code est dorénavant dans le fichier [src](./src) sauf le programme [main](./main.py), qui est le point d'entrée à notre code. Les simulations précédentes seront disponibles dans la branche `archive` (et bien sûr en parcourant l'historique git).

## 26/05

  - **(Tous)** : Lecture des retours de nos camrades. Prise en considération de leurs avis et brainstorming sur les derniers étapes à faire. Mise en place d'une stratégie pour implémenter l'intelligence artificielle dans notre projet. Recherche de dataset intéressant et OpenSource sur Kaggle.

## 02/06

  - **(Arsène)** : Test des algorithmes de ML implémentés, renseignement sur les optimisations et alternatives.
  - **(Maxence)** : Lecture de documentation sur les ML implémentables, renseignement sur les dataset exploitables.

## 18/06 

  - **(Maxence et Arsène)** : Création du [poster](./img/poster-ia-medical.svg)

## 23/06

  - **(Maxence et Carl)** : Réunion pour l'implémentation de la logique de simulation de trajectoires en fonction des données de passées. Simuler Monte Carlo pour avoir un interval de confiance sur la stabilité du systéme.  
  - **(Arsène)** : Création de l'option de création de trajectoires futurs en fonction des données du passé.

## 24/06
    - **(Arsène)** : Finalisation de la feature "trajectories".

# 25/06
    - **(Arsène)** : Déploiement (merge sur la branche `main`) des dernières mises à jour, correction des bugs de l'interface.
    - **(Maxence et Arsène)** : Travail sur la présentation finale.









