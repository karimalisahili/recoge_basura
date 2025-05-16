from settings import *

class PointIndicator(pygame.sprite.Sprite):
    def __init__(self, pos, points, groups):
        super().__init__(groups)

        adjusted_pos = (pos[0], pos[1] - 80)  # Move 50 pixels higher
        
        self.image = pygame.font.SysFont('Arial', 40).render(f"+{points} pts", True, (255, 255, 0))  # Use default font
        self.rect = self.image.get_rect(center=adjusted_pos)
        self.timer = 1.0  # Indicator will last for 2 second

    def update(self, dt):
        self.timer -= dt
        self.rect.y -= 50 * dt  # Move the indicator upward
        if self.timer <= 0:
            self.kill()  # Remove the indicator after 2 second