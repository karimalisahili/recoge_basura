from settings import *
import pygame
from random import choice

# Define the mapping of trash types to their corresponding images
TRASH_IMAGES = {
    'recycle': [
        'botella.png', 'lata.png', 'vidrio.png', 'marcadores.png'
    ],
    'garbage': [
        'caja-pizza.png', 'curita.png', 'hueso.png', 'utensilios.png'
    ],
    'compost': [
        'manzana.png', 'cascara.png', 'huevo.png', 'carton.png'
    ]
}

class Trash(pygame.sprite.Sprite):
    def __init__(self, pos, groups, trash_type, image_name=None):
        super().__init__(groups)
        self.type = trash_type  # Type of trash: 'recycle', 'garbage', or 'compost'
        self.id = None  # Nuevo: id única asignada por el servidor

        # Usa la imagen exacta si viene del servidor, si no elige aleatoria
        if image_name:
            self.image = pygame.image.load(join('images', 'waste', image_name)).convert_alpha()
        elif self.type in TRASH_IMAGES:
            image_name = choice(TRASH_IMAGES[self.type])
            self.image = pygame.image.load(join('images', 'waste', image_name)).convert_alpha()
        else:
            raise ValueError(f"Unknown trash type: {self.type}")

        # Scale the image to fit the tile size
        self.image = pygame.transform.scale(self.image, (TILE_SIZE // 2, TILE_SIZE // 2))

        # Asegura que pos sea una tupla de enteros
        if pos is None or len(pos) != 2:
            print(f"[ERROR] Trash pos inválido: {pos}")
            pos = (0, 0)
        x, y = int(pos[0]), int(pos[1])
        self.rect = self.image.get_rect(topleft=(x, y))
        self.hitbox_rect = self.rect.inflate(-10, -10)  # Smaller hitbox for better collision detection