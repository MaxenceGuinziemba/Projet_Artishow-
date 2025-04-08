#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr  8 16:54:09 2025

@author: maxence
"""

import numpy as np
from numpy import random as rd
from datetime import datetime, timedelta
import time
import sys

class Medecin:
    """
    Classe représentant un médecin
    """
    def __init__(self, identifiant):
        self.id = identifiant
        self.patients_traites = 0
        self.occupe = False
        self.file_attente = []
    
    def __str__(self):
        """
        Affiche l'état du médecin
        """
        statut = "Occupé" if self.occupe else "Libre"
        return f"Médecin {self.id}: {statut}, Patients en attente: {len(self.file_attente)}, Patients traités: {self.patients_traites}"

class Hopital:

    def __init__(self, dt : int, files_attente=6, lambda_poisson=10, mu_exponetielle=3):
        """
        Classe qui représente un hôpital
        :param dt: durée d'un tour de boucle
        :param files_attente: nombre de files d'attente (nombre de médecins)
        :param lambda_poisson: paramètre de la loi de Poisson qui génère les arrivées de patients (nombre de gens qui arrive par heure)
        :param mu_exponentielle : paramètre de la loi Exponentielle qui simule le temps moyen de chaque traitement 
        """
        self.dt = dt
        self.nb_medecins = files_attente
        self.medecins = [Medecin(i+1) for i in range(files_attente)]
        self.files_attente = [medecin.file_attente for medecin in self.medecins]  # Référence aux files des médecins
        self.lambda_poisson = 1/lambda_poisson  # nombre de gens qui arrive par heure
        self.mu_exponetielle = mu_exponetielle  # temps moyen du temps de traitement 
        self.prochaine_arrivee = 0
        self.soignés = 0
        self.temps_total = 0
        self.patients_totaux = 0


    def arrivee_patients(self):
        """
        Génère les arrivées de patients et les attribue en priorité aux médecins libres
        """
        if self.prochaine_arrivee <= 0:         
            prochaine_arrivee = np.random.poisson(self.lambda_poisson*self.dt*60)
            self.prochaine_arrivee = prochaine_arrivee

            # Utilisation directe de mu_exponentielle comme moyenne pour la distribution exponentielle
            # Ajout d'un max pour éviter les temps de traitement trop courts
            temps_de_traitement = max(1, int(np.random.exponential(self.mu_exponetielle)))
            
            # Identifier les médecins libres
            medecins_libres = [medecin for medecin in self.medecins if not medecin.occupe]
            
            # S'il y a des médecins libres, en choisir un aléatoirement
            if medecins_libres:
                medecin_choisi = rd.choice(medecins_libres)
            else:
                # Si aucun médecin n'est libre, choisir celui avec la file d'attente la plus courte
                index_file_min = np.argmin([len(medecin.file_attente) for medecin in self.medecins])
                medecin_choisi = self.medecins[index_file_min]
                
            patient = Personne(temps_de_traitement, self.dt)
            medecin_choisi.file_attente.append(patient)
            self.patients_totaux += 1
        else:
            self.prochaine_arrivee -= self.dt

    def mise_a_jour_patients(self):
        """
        Met à jour l'état de l'hôpital et des médecins
        """
        for medecin in self.medecins:
            if len(medecin.file_attente) > 0:
                medecin.occupe = True
                medecin.file_attente[0].mise_a_jour()
            else:
                medecin.occupe = False
            
        for k, medecin in enumerate(self.medecins):
            avant = len(medecin.file_attente)
            medecin.file_attente = [personne for personne in medecin.file_attente if personne.temps_de_traitement > 0]
            apres = len(medecin.file_attente)
            patients_traites = avant - apres
            medecin.patients_traites += patients_traites
            self.soignés += patients_traites

    def suivant(self):
        """
        Passe au tour de boucle suivant
        """
        self.arrivee_patients()
        self.mise_a_jour_patients()
        self.temps_total += self.dt

    def __str__(self):
        """
        Affiche l'état de l'hôpital (patients traités et files d'attente)
        """
        self.file_attente()
        self.en_consultation()
        self.nombre_total_traite()
        
        # Afficher l'état de chaque médecin
        print("\nÉtat des médecins:")
        for medecin in self.medecins:
            print(f"  {medecin}")
            
        return ""  # Retourne une chaîne vide car l'affichage est déjà fait
            
    def nombre_total_traite(self): 
        """
        Affiche le nombre total de patients traités
        """
        print(f"Total Patients traités     : {self.soignés}")
        
    def file_attente(self):
        """
        Affiche le nombre total de patients en file d'attente (toutes files confondues)
        """
        total_attente = sum(len(medecin.file_attente) for medecin in self.medecins)
        print(f"Patients en file d'attente : {total_attente}")
        
    def en_consultation(self):
        """
        Affiche le nombre de médecins en consultation
        """
        nb_occupes = sum(1 for medecin in self.medecins if medecin.occupe)
        print(f"Médecins en consultation   : {nb_occupes}/{self.nb_medecins}")
        
    def afficher_bilan_final(self, sig=None, frame=None):
        """
        Affiche un bilan complet de la simulation lorsque le programme est fermé
        """
        print("\n" + "="*50)
        print("BILAN FINAL DE LA SIMULATION")
        print("="*50)
        print(f"Temps simulé: {timedelta(minutes=self.temps_total)}")
        print(f"Nombre total de patients arrivés: {self.patients_totaux}")
        print(f"Nombre total de patients traités: {self.soignés}")
        
        print("\nStatistiques par médecin:")
        for medecin in self.medecins:
            print(f"  Médecin {medecin.id}: {medecin.patients_traites} patients traités")
        
        print("\nEfficacité du système:")
        if self.temps_total > 0:
            patients_par_heure = (self.soignés * 60) / self.temps_total
            print(f"  Moyenne de patients traités par heure: {patients_par_heure:.2f}")
        
        taux_traitement = (self.soignés / self.patients_totaux * 100) if self.patients_totaux > 0 else 0
        print(f"  Taux de traitement: {taux_traitement:.2f}%")
        
        print("="*50)
        
        # Quitter proprement le programme
        sys.exit(0)


class Personne:
    """
    Classe qui représente une personne
    :param temps_de_traitement: temps de traitement de la personne
    :param statut: statut de la personne (False : en attente ou True : en traitement)
    """
    def __init__(self, temps_de_traitement : int, dt : int = 1):
        self.temps_de_traitement = temps_de_traitement
        #print(temps_de_traitement)
        self.dt = dt

    def mise_a_jour(self):
        self.temps_de_traitement -= self.dt
        if self.temps_de_traitement <= 0:
            #print("Patient traité")
            pass
            

def run():
    h = Hopital(1, 3, 20, 8) # dt = 1 minutes ; nombre de médecins = 3 ; nombre moyen d'arrivé en une heure : 20 ; temps de traitement : 10
    compte = 0
    
    try:
        while True:
            print("\n" + "_"*50)
            print("\nHeure                      :", timedelta(minutes=h.dt*compte))
            h.suivant()
            print(h)  # Appel à __str__ pour afficher l'état
            compte += 1
            time.sleep(0.3)
    except KeyboardInterrupt:
        h.afficher_bilan_final()

if __name__ == "__main__":
    run() 
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
