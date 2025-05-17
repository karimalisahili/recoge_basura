from settings import * 

class AllSprites(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.Vector2()
    
    def draw(self, target_pos):
        zoom = 0.65
        # Adjust the camera offset (shift focus downward by 80 pixels)
        self.offset.x = -(target_pos[0] - (WINDOW_WIDTH / 2) / zoom)
        self.offset.y = -(target_pos[1] - (WINDOW_HEIGHT / 2) / zoom)

        # Create a temporary surface for scaling
        temp_surface = pygame.Surface(
            (WINDOW_WIDTH / zoom, WINDOW_HEIGHT / zoom)
        )
        temp_surface.fill('black')

        # Draw sprites onto the temporary surface
        ground_sprites = [sprite for sprite in self if hasattr(sprite, 'ground')] 
        object_sprites = [sprite for sprite in self if not hasattr(sprite, 'ground')] 
        
        for layer in [ground_sprites, object_sprites]:
            for sprite in sorted(layer, key=lambda sprite: sprite.rect.centery):
                temp_surface.blit(sprite.image, sprite.rect.topleft + self.offset)

        # Scale the temporary surface and blit it to the display surface
        scaled_surface = pygame.transform.scale(
            temp_surface, (WINDOW_WIDTH, WINDOW_HEIGHT)
        )
        self.display_surface.blit(scaled_surface, (0, 0))