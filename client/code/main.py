from settings import *
from player import Player
from sprites import *
from pytmx.util_pygame import load_pygame
from groups import AllSprites
from trashbin import TrashBin
from trash import Trash
from random import randint, choice
from scoreboard import Scoreboard
import threading
import grpc
import game_pb2
import game_pb2_grpc
import time
import random
import pygame
from os.path import join

ZOOM = 0.3  # Ajusta el zoom aquí (1 = normal, 2 = doble, etc)

class Game:
    def __init__(self):
        pygame.init()
        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Recoge basura')
        self.clock = pygame.time.Clock()
        self.running = True

        # Grupos de sprites
        self.all_sprites = pygame.sprite.Group()
        self.collision_sprites = pygame.sprite.Group()
        self.trash_group = pygame.sprite.Group()

        self.players_dict = {}  # player_id -> Player
        self.players_positions = {}  # player_id -> (x_px, y_px)
        self.players_positions_lock = threading.Lock()

        self.local_player_id = None
        self.grpc_thread = None
        self.grpc_running = True
        self.pending_actions = []

        # Tamaño total del mapa (ajustar según tu mapa)
        self.map_width = 40  # ejemplo, ajusta al tamaño real
        self.map_height = 40

        # Crear superficie donde se dibuja el mapa y sprites (sin zoom)
        self.map_surface = pygame.Surface((self.map_width * TILE_SIZE, self.map_height * TILE_SIZE))

        self.keys_pressed = set()  # para controlar teclas presionadas

        self.setup()
        self.start_grpc_client()

    def setup(self):
        map = load_pygame(join('data', 'maps', 'world.tmx'))
        random.seed(42)

        for x, y, image in map.get_layer_by_name('Ground').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, self.all_sprites)

        for obj in map.get_layer_by_name('Objects'):
            CollisionSprite((obj.x, obj.y), obj.image, (self.all_sprites, self.collision_sprites))

        for obj in map.get_layer_by_name('Collisions'):
            CollisionSprite((obj.x, obj.y), pygame.Surface((obj.width, obj.height)), self.collision_sprites)

        self.players = [
            Player((obj.x, obj.y), self.all_sprites, self.collision_sprites, self.trash_group)
            for obj in map.get_layer_by_name('Entities') if obj.name == 'Player'
        ]

        self.scoreboard = Scoreboard(self.players)

        bin_positions = [
            ((22 * TILE_SIZE, 17 * TILE_SIZE), 'recycle'),
            ((27 * TILE_SIZE, 17 * TILE_SIZE), 'garbage'),
            ((32 * TILE_SIZE, 17 * TILE_SIZE), 'compost')
        ]
        for pos, bin_type in bin_positions:
            TrashBin(pos, (self.all_sprites, self.trash_group), bin_type)

        trash_types = ['recycle', 'garbage', 'compost']
        for _ in range(10):
            x = randint(19, 35) * TILE_SIZE
            y = randint(18, 35) * TILE_SIZE
            trash_type = choice(trash_types)
            Trash((x, y), (self.all_sprites, self.trash_group), trash_type)

    def start_grpc_client(self):
        def grpc_loop():
            channel = grpc.insecure_channel("localhost:50051")
            stub = game_pb2_grpc.GameServiceStub(channel)

            player_id = input("Ingresa tu nombre de jugador: ")
            total_players = int(input("¿Cuántos jugadores participarán? (solo el primero debe indicar): ") or 0)
            self.local_player_id = player_id

            def action_stream():
                # Enviar acción inicial para registrar al jugador
                yield game_pb2.PlayerAction(
                    player_id=player_id,
                    action=game_pb2.MOVE,
                    direction=game_pb2.NONE,
                    total_players=total_players if total_players > 0 else None
                )
                while self.grpc_running:
                    if self.pending_actions:
                        action_type, direction = self.pending_actions.pop(0)
                        yield game_pb2.PlayerAction(
                            player_id=player_id,
                            action=action_type,
                            direction=direction
                        )
                    else:
                        time.sleep(0.05)

            try:
                for game_state in stub.Connect(action_stream()):
                    tick = getattr(game_state, 'tick', None)
                    print(f"[gRPC] Tick recibido: {tick if tick is not None else 'N/A'}")
                    # Actualiza las posiciones de todos los jugadores
                    with self.players_positions_lock:
                        self.players_positions = {
                            p.player_id: (p.x * TILE_SIZE, p.y * TILE_SIZE)
                            for p in game_state.players
                        }
                        # Crea los Player si no existen
                        for p in game_state.players:
                            if p.player_id not in self.players_dict:
                                self.players_dict[p.player_id] = Player(
                                    (p.x * TILE_SIZE, p.y * TILE_SIZE),
                                    self.all_sprites, self.collision_sprites, self.trash_group
                                )
            except grpc.RpcError as e:
                print("Error de conexión gRPC:", e)

        self.grpc_thread = threading.Thread(target=grpc_loop, daemon=True)
        self.grpc_thread.start()

    def send_movement(self):
        if not self.keys_pressed:
            return
        key = next(iter(self.keys_pressed))
        if key == pygame.K_UP:
            action = game_pb2.MOVE
            direction = game_pb2.DOWN
        elif key == pygame.K_DOWN:
            action = game_pb2.MOVE
            direction = game_pb2.UP
        elif key == pygame.K_LEFT:
            action = game_pb2.MOVE
            direction = game_pb2.LEFT
        elif key == pygame.K_RIGHT:
            action = game_pb2.MOVE
            direction = game_pb2.RIGHT
        else:
            return  # no enviamos nada si no es una tecla válida

        # Añadir acción pendiente para enviar al servidor
        self.pending_actions.append((action, direction))

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
                        self.keys_pressed.add(event.key)
                        self.send_movement()
                elif event.type == pygame.KEYUP:
                    if event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
                        self.keys_pressed.discard(event.key)

            # Limpiar superficie del mapa sin zoom
            self.map_surface.fill((30, 30, 30))

            # Dibujar todos los sprites (mapa, basura, etc) en la superficie sin zoom
            self.all_sprites.draw(self.map_surface)

            # Actualizar y dibujar jugadores
            with self.players_positions_lock:
                for player_id, pos in self.players_positions.items():
                    if player_id in self.players_dict:
                        player = self.players_dict[player_id]
                        player.rect.topleft = pos

                        if player_id == self.local_player_id:
                            player.update(dt)  # El local procesa input, movimiento y animación
                        else:
                            # Para remotos: fuerza la animación si la posición cambió
                            if not hasattr(player, "last_pos"):
                                player.last_pos = player.rect.topleft
                            dx = pos[0] - player.last_pos[0]
                            dy = pos[1] - player.last_pos[1]
                            direction = pygame.Vector2(dx, dy)
                            if direction.length_squared() > 0:
                                direction = direction.normalize()
                            player.direction = direction
                            player.animate(dt)
                            player.last_pos = pos

                        self.map_surface.blit(player.image, player.rect)
                        player.draw_trash_icon(self.map_surface)

            # Escalar superficie para zoom
            scaled_surface = pygame.transform.scale(
                self.map_surface,
                (int(self.map_surface.get_width() * ZOOM), int(self.map_surface.get_height() * ZOOM))
            )
            self.display_surface.blit(scaled_surface, (0, 0))

            pygame.display.flip()

        pygame.quit()


if __name__ == '__main__':
    game = Game()
    game.run()
