from settings import *
from player import Player
from sprites import *
from pytmx.util_pygame import load_pygame
from groups import AllSprites
from trashbin import TrashBin
from trash import Trash
from random import randint, choice
from scoreboard import Scoreboard

class Game:
    def __init__(self):
        # setup
        pygame.init()
        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Survivor')
        self.clock = pygame.time.Clock()
        self.running = True

        # groups 
        self.all_sprites = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.trash_group = pygame.sprite.Group()

        self.setup()

        # sprites
        
    def setup(self):
        map = load_pygame(join('data', 'maps', 'world.tmx'))

        for x, y, image in map.get_layer_by_name('Ground').tiles():
            Sprite((x * TILE_SIZE,y * TILE_SIZE), image, self.all_sprites)
        
        for obj in map.get_layer_by_name('Objects'):
            CollisionSprite((obj.x, obj.y), obj.image, (self.all_sprites, self.collision_sprites))
        
        for obj in map.get_layer_by_name('Collisions'):
            CollisionSprite((obj.x, obj.y), pygame.Surface((obj.width, obj.height)), self.collision_sprites)

        self.players = [
            Player((obj.x, obj.y), self.all_sprites, self.collision_sprites, self.trash_group)
            for obj in map.get_layer_by_name('Entities') if obj.name == 'Player'
        ]

        self.scoreboard = Scoreboard(self.players)
        # Add trash bins to the map
        bin_positions = [
            ((22 * TILE_SIZE, 17 * TILE_SIZE), 'plastic'),  # Position and type for plastic bin
            ((27 * TILE_SIZE, 17 * TILE_SIZE), 'paper'),    # Position and type for paper bin
            ((32 * TILE_SIZE, 17 * TILE_SIZE), 'glass')     # Position and type for glass bin
        ]
        for pos, bin_type in bin_positions:
            TrashBin(pos, (self.all_sprites, self.trash_group), bin_type)  # Add bins to trash_group

        # Add trash objects within the specified range
        trash_types = ['plastic', 'paper', 'glass']  # Define the types of trash
        for _ in range(10):  # Add 10 trash objects randomly
            x = randint(19, 35) * TILE_SIZE  # X-coordinate within 17 to 36
            y = randint(18, 35) * TILE_SIZE  # Y-coordinate within 16 to 36
            trash_type = choice(trash_types)  # Randomly select a trash type
            Trash((x, y), (self.all_sprites, self.trash_group), trash_type)

    def run(self):
        while self.running:
            # dt 
            dt = self.clock.tick() / 1000

            # event loop 
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            # update 
            self.all_sprites.update(dt)

            

            # draw
            self.display_surface.fill('black')
            self.all_sprites.draw(self.players[0].rect.center)

            # Draw the trash icon above the player
            self.players[0].draw_trash_icon(self.display_surface)
            
            # Draw the scoreboard
            self.scoreboard.draw(self.display_surface)
        
            pygame.display.update()

        pygame.quit()

if __name__ == '__main__':
    game = Game()
    game.run()