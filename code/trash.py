from settings import *

class Trash(pygame.sprite.Sprite):
    def __init__(self, pos, groups, trash_type):
        super().__init__(groups)
        self.type = trash_type  # Type of trash: 'plastic', 'paper', or 'glass'

        # Assign color based on trash type
        if self.type == 'plastic':
            color = (0, 0, 255)  # Blue for plastic
        elif self.type == 'paper':
            color = (255, 255, 0)  # Yellow for paper
        elif self.type == 'glass':
            color = (0, 255, 0)  # Green for glass
        else:
            color = (255, 0, 0)  # Default red (in case of an invalid type)

        # Create the trash sprite
        self.image = pygame.Surface((TILE_SIZE // 2, TILE_SIZE // 2))  # Square for trash
        self.image.fill(color)  # Fill with the assigned color
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox_rect = self.rect.inflate(-10, -10)  # Smaller hitbox for better collision detection