import random as rd

N_HOPITAUX = 10
N_POPULATION = 1000000
N_MALADES = 100

class Medecin:
    def __init__(self):
        self.en_charge = None

    def occupé(self):
        return self.en_charge is not None

class Maladie:
    """
    Classe qui représente une maladie: - taux de mortalité (% de chance de mourrir chaque jour)
                                       - taux de contagion (% de chance qu'une personne tombe malade)
                                       - taux de rémission (% de chance qu'une personne guérisse d'elle même chaque jour)
                                       - un multiplicateur qui augmente le taux de rémission/diminue la mortalité quand le patient est à l'hopital
    """
    def __init__(self, taux_mortalite, taux_contagion, taux_remission, multiplicateur_hopital):
        self.taux_mortalite = taux_mortalite
        self.taux_contagion = taux_contagion
        self.taux_remission = taux_remission
        self.multiplicateur_hopital = multiplicateur_hopital

class Personne:
    """
    Classe qui représente une personne : - date d'arrivée à l'hopital
                                         - le type de maladie (si elle est malade)
                                         - son état (vivant ou mort)
    """
    def __init__(self, arrival_time=0, maladie=None):
        self.arrival_time = arrival_time
        self.maladie = maladie
        self.en_attente = False
        self.en_traitement = False
        self.vivant = True

    def est_malade(self):
        return self.maladie is not None

    def mourir(self):
        self.vivant = False

    def guerir(self):
        self.arrival_time = 0
        self.maladie = None
        self.en_traitement = False
        self.en_attente = False

    def jour_suivant(self):
        """
        Met à jour l'état de la personne en fonction de sa maladie
        """
        if self.est_malade():
            multiplicateur = self.maladie.multiplicateur_hopital if self.en_traitement else 1
            if self.maladie.taux_mortalite / multiplicateur > rd.random():
                self.mourir()
            elif self.maladie.taux_remission > rd.random():
                self.guerir()

class Hopital:
    """
    Classe qui réprésente un hopital : - un ensemble de lits
                                       - un ensemble de medecins
                                       - un ensemble de patients (en attente ou en traitement)
                                       - un nombre de lits disponibles
    """
    def __init__(self, lits=50, medecins=None):
        self.file_attente = []
        self.en_traitement = []
        self.lits_dispos = lits
        self.medecins = medecins if medecins else []

    def jour_suivant(self):
        """
        Met à jour l'état de l'hopital en supposant que la population a déjà été mise à jour:
            - les personnes qui ne sont plus vivantes ou guéries sont retirées de la file d'attente et du traitement
            - les personnes en attente qui sont malades et pour qui il reste des lits sont mises en traitement
        """
        self.en_traitement = [p for p in self.en_traitement if p.vivant and p.est_malade()]
        self.file_attente = [p for p in self.file_attente if p.vivant and p.est_malade()]

        while self.file_attente and self.lits_dispos > 0:
            patient = self.file_attente.pop(0)
            self.en_traitement.append(patient)
            self.lits_dispos -= 1

class World:
    """
    Classe qui représente le monde dans lequel on évolue: - un ensemble d'hopitaux
                                                          - une population
                                                          - un ensemble de maladies
                                                          - la date actuelle
    """
    def __init__(self, hopitaux=None, population=None, maladies=None):
        self.hopitaux = hopitaux if hopitaux else []
        self.population = population if population else []
        self.maladies = maladies if maladies else []
        self.nb_population_initiale = len(self.population)
        self.nb_malades_cache = sum(1 for p in self.population if p.est_malade() and p.vivant)
        self.jour = 0

    def nb_population(self):
        return len(self.population)

    def nb_malades(self):
        return self.nb_malades_cache

    def nb_morts(self):
        return self.nb_population_initiale - self.nb_population()

    def jour_suivant(self):
        self.jour += 1
        self.nb_malades_cache = 0

        nouveaux_malades = []
        population_vivante = []

        for personne in self.population:
            personne.jour_suivant()
            if personne.vivant:
                population_vivante.append(personne)
                if personne.est_malade():
                    self.nb_malades_cache += 1
                    if not personne.en_traitement and not personne.en_attente:
                        nouveaux_malades.append(personne)

        self.population = population_vivante

        nb_hopitaux = len(self.hopitaux)
        for personne in nouveaux_malades:
            self.hopitaux[rd.randint(0, nb_hopitaux - 1)].file_attente.append(personne)

        if self.nb_malades_cache > 0:
            nb_nouveaux_malades = int(self.maladies[0].taux_contagion * self.nb_malades_cache)
            candidats = [p for p in self.population if not p.est_malade()]
            for personne in rd.sample(candidats, min(nb_nouveaux_malades, len(candidats))):
                personne.maladie = self.maladies[0]

        for hopital in self.hopitaux:
            hopital.jour_suivant()

        print(f"Jour {self.jour} | Population: {len(self.population)} | Malades: {self.nb_malades()}")

def create_world(population_n=N_POPULATION, hopitaux_n=N_HOPITAUX, malades_initiaux=N_MALADES):
    """
    Crée un monde avec une population de population_n personnes et hopitaux hopitaux avec 5 medecins chacun
    """
    maladie_de_base = Maladie(0.003, 0.5, 0.2, 1)
    hopitaux = [Hopital(50, [Medecin() for _ in range(5)]) for _ in range(hopitaux_n)]
    population = [Personne() for _ in range(population_n)]
    
    for i in range(malades_initiaux):
        population[i].maladie = maladie_de_base
    
    return World(hopitaux, population, [maladie_de_base])
