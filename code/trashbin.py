from settings import *

class TrashBin(pygame.sprite.Sprite):
    def __init__(self, pos, groups, bin_type):
        super().__init__(groups)
        self.type = bin_type  # Type of bin: 'plastic', 'paper', or 'glass'

        # Assign color based on bin type
        if self.type == 'plastic':
            color = (0, 0, 255)  # Blue for plastic
        elif self.type == 'paper':
            color = (255, 255, 0)  # Yellow for paper
        elif self.type == 'glass':
            color = (0, 255, 0)  # Green for glass
        else:
            color = (255, 0, 0)  # Default red (in case of an invalid type)

        # Create the bin sprite
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))  # Square for bin
        self.image.fill(color)  # Fill with the assigned color
        self.rect = self.image.get_rect(topleft=pos)

        # Add a hitbox for collision detection
        self.hitbox_rect = self.rect.inflate(-10, -10)  # Slightly smaller hitbox