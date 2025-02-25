import structure as s
import structure_bis as sb
import time

world = sb.create_world()

def updtate():
    world.jour_suivant()

while True:
    updtate()
