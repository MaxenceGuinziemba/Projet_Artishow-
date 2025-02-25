import structure as s
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import tkinter as tk
from tkinter import ttk

world = s.create_world()
jours = []
populations = []
malades = []
morts = []

fig, ax = plt.subplots()
ax.set_title("Évolution de la population")
ax.set_xlabel("Jours")
ax.set_ylabel("Nombre d'individus")

line_pop, = ax.plot([], [], 'g-', label="Population")
line_malades, = ax.plot([], [], 'r-', label="Malades")
line_morts, = ax.plot([], [], 'k-', label="Morts")

ax.legend()

def update_visual(frame):
    """
    Met à jour les données et redessine le graphe
    """
    world.jour_suivant()
    jours.append(frame)
    populations.append(world.nb_population())
    malades.append(world.nb_malades())
    morts.append(world.nb_morts())

    # Limitation du nombre de points affichés à 50
    del jours[:-50]
    del populations[:-50]
    del malades[:-50]
    del morts[:-50]
    
    # Mise à jour des données du graphe
    line_pop.set_data(jours, populations)
    line_malades.set_data(jours, malades)
    line_morts.set_data(jours, morts)

    ax.relim()
    ax.autoscale_view()
    return line_pop, line_malades, line_morts

def stop_simulation():
    """
    Arrête l'animation et ferme l'application
    """
    ani.event_source.stop()
    root.quit()
    root.destroy()

root = tk.Tk()
root.title("Simulation de population")

frame = ttk.Frame(root, padding=10)
frame.pack()

btn_stop = ttk.Button(frame, text="Arrêter", command=stop_simulation)
btn_stop.pack()

ani = animation.FuncAnimation(fig, update_visual, interval=1)

plt.show()
root.mainloop()
