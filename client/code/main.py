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
import uuid

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

        for obj in map.get_layer_by_name('Collisions'):
            CollisionSprite((obj.x, obj.y), pygame.Surface((obj.width, obj.height)), self.collision_sprites)

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

            player_id = f"jugador_{uuid.uuid4().hex[:6]}"
            total_players = 2
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
                        # Solo mantener los jugadores que están en el estado recibido y tienen player_id válido
                        current_ids = set(p.player_id for p in game_state.players if p.player_id)
                        # Eliminar jugadores que ya no están
                        for pid in list(self.players_dict.keys()):
                            if pid not in current_ids:
                                del self.players_dict[pid]
                        self.players_positions = {
                            p.player_id: (p.x, p.y)
                            for p in game_state.players if p.player_id
                        }
                        # Crea los Player si no existen y el id es válido
                        for p in game_state.players:
                            if p.player_id and p.player_id not in self.players_dict:
                                self.players_dict[p.player_id] = Player(
                                    (p.x, p.y),
                                    self.all_sprites, self.collision_sprites, self.trash_group
                                )
                                # Inicializa posición interpolada y objetivo
                                self.players_dict[p.player_id].interp_pos = pygame.Vector2(p.x, p.y)
                                self.players_dict[p.player_id].target_pos = pygame.Vector2(p.x, p.y)
                            elif p.player_id:
                                # Actualiza la posición objetivo para interpolación
                                self.players_dict[p.player_id].target_pos = pygame.Vector2(p.x, p.y)
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
                        self.send_movement()  # Solo aquí
                elif event.type == pygame.KEYUP:
                    if event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
                        self.keys_pressed.discard(event.key)

            # Limpiar superficie del mapa sin zoom
            self.map_surface.fill((30, 30, 30))

            # Dibujar todos los sprites (mapa, basura, etc) en la superficie sin zoom
            sprites_with_image = [spr for spr in self.all_sprites if hasattr(spr, "image")]
            if sprites_with_image:
                pygame.sprite.Group(sprites_with_image).draw(self.map_surface)

            # Actualizar y dibujar jugadores
            with self.players_positions_lock:
                for player_id, pos in self.players_positions.items():
                    if player_id in self.players_dict:
                        player = self.players_dict[player_id]
                        # Actualiza la posición objetivo para interpolación
                        if not hasattr(player, "interp_pos"):
                            player.interp_pos = pygame.Vector2(player.rect.topleft)
                        player.target_pos = pygame.Vector2(pos)
                        speed = 200  # píxeles por segundo (ajusta a gusto)
                        direction = player.target_pos - player.interp_pos
                        distance = direction.length()
                        if distance > 0:
                            move_dist = min(speed * dt, distance)
                            if direction.length_squared() > 0:
                                direction = direction.normalize()
                            # Calcular nueva posición tentativa
                            new_interp_pos = player.interp_pos + direction * move_dist
                            new_rect = player.rect.copy()
                            new_rect.topleft = (round(new_interp_pos.x), round(new_interp_pos.y))
                            # Verificar colisión antes de mover
                            collision = pygame.sprite.spritecollideany(
                                type('TempSprite', (pygame.sprite.Sprite,), {'rect': new_rect})(), 
                                self.collision_sprites
                            )
                            if not collision:
                                player.interp_pos = new_interp_pos
                        player.rect.topleft = (round(player.interp_pos.x), round(player.interp_pos.y))

                        # Animación según dirección
                        if direction.length_squared() > 0:
                            player.direction = direction.normalize()
                        else:
                            player.direction = pygame.Vector2(0, 0)
                        player.animate(dt)
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
