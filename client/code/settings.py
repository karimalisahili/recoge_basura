import os
import pygame 
from os.path import join 
from os import walk

WINDOW_WIDTH, WINDOW_HEIGHT = 720,640 
TILE_SIZE = 64

try:
    os.chdir(os.path.join(os.getcwd(), 'client'))
    print(f"✓ Directorio cambiado a: {os.getcwd()}")
except Exception as e:
    print(f"✗ Error cambiando directorio: {e}")
    print("ℹ Asegúrate que la carpeta 'client' exista")
