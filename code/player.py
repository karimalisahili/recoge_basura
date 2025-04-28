from settings import * 
from trashbin import TrashBin
from pointindicator import PointIndicator

from trash import Trash
class Player(pygame.sprite.Sprite):
    def __init__(self, pos, groups, collision_sprites, trash_group):
        super().__init__(groups)
        self.load_images()
        self.state, self.frame_index = 'right', 0
        self.image = pygame.image.load(join('images', 'player', 'down', '0.png')).convert_alpha()
        self.rect = self.image.get_rect(center = pos)
        self.hitbox_rect = self.rect.inflate(-60, -90)

        # Score
        self.score = 0
    
        # movement 
        self.direction = pygame.Vector2()
        self.speed = 500
        self.collision_sprites = collision_sprites

        # trash collection
        self.trash_group = trash_group
        self.carrying_trash = False  # Whether the player is carrying trash
        self.carrying_trash_type = None  # Type of trash being carried

    def load_images(self):
        self.frames = {'left': [], 'right': [], 'up': [], 'down': []}

        for state in self.frames.keys():
            for folder_path, sub_folders, file_names in walk(join('images', 'player', state)):
                if file_names:
                    for file_name in sorted(file_names, key= lambda name: int(name.split('.')[0])):
                        full_path = join(folder_path, file_name)
                        surf = pygame.image.load(full_path).convert_alpha()
                        self.frames[state].append(surf)

    def input(self):
        keys = pygame.key.get_pressed()
        self.direction.x = int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT])
        self.direction.y = int(keys[pygame.K_DOWN]) - int(keys[pygame.K_UP])
        self.direction = self.direction.normalize() if self.direction else self.direction

        # Collect trash
        if keys[pygame.K_SPACE] and not self.carrying_trash:
            self.collect_trash()

        # Dispose of trash
        if keys[pygame.K_e] and self.carrying_trash:
            self.dispose_trash()

    def collect_trash(self):
        for trash in self.trash_group:
            if isinstance(trash, Trash):  # Ensure the object is a Trash instance
                if self.hitbox_rect.colliderect(trash.hitbox_rect):
                    print(f"Collision detected with trash at {trash.rect.topleft}")
                    trash.kill()  # Remove the trash from the game
                    self.carrying_trash = True  # Player is now carrying trash
                    self.carrying_trash_type = trash.type  # Store the type of trash
                    print(f"Trash collected! Carrying trash: {self.carrying_trash_type}")
                    return  # Exit after collecting one trash
        print("No trash collected.")

    def dispose_trash(self):
        for bin in self.trash_group:
            if isinstance(bin, TrashBin) and self.hitbox_rect.colliderect(bin.hitbox_rect):
                if self.carrying_trash:
                    if bin.type == self.carrying_trash_type:
                        print(f"Disposed of {self.carrying_trash_type} trash in the correct bin!")
                        self.carrying_trash = False
                        self.carrying_trash_type = None
                        self.score += 100  # Add points for correct disposal

                        PointIndicator(self.rect.center, 100, self.groups()[0])  # Add to the same group as the player
                        return
                    else:
                        print(f"Wrong bin! This is a {bin.type} bin.")

    def draw_trash_icon(self, surface):
        if self.carrying_trash:  # Only draw the icon if the player is carrying trash
            # Create a small square icon with the color of the trash type
            icon_size = TILE_SIZE // 4
            icon = pygame.Surface((icon_size, icon_size))
            if self.carrying_trash_type == 'plastic':
                icon.fill((0, 0, 255))  # Blue for plastic
            elif self.carrying_trash_type == 'paper':
                icon.fill((255, 255, 0))  # Yellow for paper
            elif self.carrying_trash_type == 'glass':
                icon.fill((0, 255, 0))  # Green for glass

            # Position the icon above the center of the screen
            screen_center_x = WINDOW_WIDTH // 2
            screen_center_y = WINDOW_HEIGHT // 2
            icon_rect = icon.get_rect(midbottom=(screen_center_x, screen_center_y - 40))  # 40 pixels above the player
            surface.blit(icon, icon_rect)

    def move(self, dt):
        self.hitbox_rect.x += self.direction.x * self.speed * dt
        self.collision('horizontal')
        self.hitbox_rect.y += self.direction.y * self.speed * dt
        self.collision('vertical')
        self.rect.center = self.hitbox_rect.center

    def collision(self, direction):
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.hitbox_rect):
                if direction == 'horizontal':
                    if self.direction.x > 0: self.hitbox_rect.right = sprite.rect.left
                    if self.direction.x < 0: self.hitbox_rect.left = sprite.rect.right
                else:
                    if self.direction.y < 0: self.hitbox_rect.top = sprite.rect.bottom
                    if self.direction.y > 0: self.hitbox_rect.bottom = sprite.rect.top

    def animate(self, dt):
        # get state 
        if self.direction.x != 0:
            self.state = 'right' if self.direction.x > 0 else 'left'
        if self.direction.y != 0:
            self.state = 'down' if self.direction.y > 0 else 'up'

        # animate
        self.frame_index = self.frame_index + 5 * dt if self.direction else 0
        self.image = self.frames[self.state][int(self.frame_index) % len(self.frames[self.state])]

    def update(self, dt):
        self.input()
        self.move(dt)
        self.animate(dt)