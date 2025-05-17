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
        self.hitbox_rect.center = self.rect.center  # <-- Centra el hitbox respecto al sprite

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
        # Ya no se recoge basura localmente, se hace por sincronización del servidor
        pass

    def dispose_trash(self):
        # Ya no se usa aquí, la lógica está en main.py
        pass

    def draw_trash_icon(self, surface):
        if self.carrying_trash and hasattr(self, "carrying_trash_image"):
            icon_size = TILE_SIZE // 2
            trash_icon = pygame.transform.scale(self.carrying_trash_image, (icon_size, icon_size))
            # Dibuja el ícono sobre el jugador (no en el centro de la pantalla)
            icon_rect = trash_icon.get_rect(midbottom=(self.rect.centerx, self.rect.top - 10))
            surface.blit(trash_icon, icon_rect)

    def move(self, dt):
        # Calcula el desplazamiento
        dx = self.direction.x * self.speed * dt
        dy = self.direction.y * self.speed * dt

        # Mueve el rect principal
        self.rect.x += dx
        self.collision('horizontal')
        self.rect.y += dy
        self.collision('vertical')

        # Centra el hitbox respecto al rect después de mover
        self.hitbox_rect.center = self.rect.center

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