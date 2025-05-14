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
    def __init__(self, pos, groups, trash_type):
        super().__init__(groups)
        self.type = trash_type  # Type of trash: 'recycle', 'garbage', or 'compost'

        # Randomly select an image based on the trash type
        if self.type in TRASH_IMAGES:
            image_name = choice(TRASH_IMAGES[self.type])
            self.image = pygame.image.load(join('images', 'waste', image_name)).convert_alpha()
        else:
            raise ValueError(f"Unknown trash type: {self.type}")

        # Scale the image to fit the tile size
        self.image = pygame.transform.scale(self.image, (TILE_SIZE // 2, TILE_SIZE // 2))

        # Set the rect for positioning
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox_rect = self.rect.inflate(-10, -10)  # Smaller hitbox for better collision detection