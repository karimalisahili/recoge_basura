from settings import *
import pygame

class TrashBin(pygame.sprite.Sprite):
    def __init__(self, pos, groups, bin_type):
        super().__init__(groups)
        self.type = bin_type  # Type of bin: 'recycle', 'garbage', or 'compost'

        # Load the appropriate image based on the bin type
        if self.type == 'recycle':
            self.image = pygame.image.load(join('images', 'bins', 'recyclebot.png')).convert_alpha()
        elif self.type == 'garbage':
            self.image = pygame.image.load(join('images', 'bins', 'garbagebot.png')).convert_alpha()
        elif self.type == 'compost':
            self.image = pygame.image.load(join('images', 'bins', 'compostbot.png')).convert_alpha()
        else:
            raise ValueError(f"Unknown bin type: {self.type}")
        
        # Scale the image to fit the tile size
        self.image = pygame.transform.scale(self.image, (int(TILE_SIZE* 1.5), int(TILE_SIZE*1.5)))

        # Set the rect for positioning
        self.rect = self.image.get_rect(topleft=pos)

        # Add a hitbox for collision detection
        self.hitbox_rect = self.rect.inflate(-10, -10)  # Slightly smaller hitbox
