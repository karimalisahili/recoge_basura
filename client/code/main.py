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

DEBUG_DRAW_HITBOX = True  # Activa el dibujo de hitboxes

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

        self.trash_dict = {}  # trash_id -> Trash
        self.trash_bins = []  # Lista de TrashBin locales

        # Tamaño total del mapa (ajustar según tu mapa)
        self.map_width = 40  # ejemplo, ajusta al tamaño real
        self.map_height = 40

        # Crear superficie donde se dibuja el mapa y sprites (sin zoom)
        self.map_surface = pygame.Surface((self.map_width * TILE_SIZE, self.map_height * TILE_SIZE))

        self.keys_pressed = set()  # para controlar teclas presionadas

        self.last_score = 0
        self.score_message_time = 0
        self.score_message = ""

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
            ((22 * TILE_SIZE, 18 * TILE_SIZE), 'recycle'),
            ((27 * TILE_SIZE, 18 * TILE_SIZE), 'garbage'),
            ((32 * TILE_SIZE, 18 * TILE_SIZE), 'compost')
        ]
        for pos, bin_type in bin_positions:
            bin_obj = TrashBin(pos, (self.all_sprites, self.trash_group), bin_type)
            self.trash_bins.append(bin_obj)

        # No crear basura aquí, ahora la crea el servidor y se sincroniza

    def start_grpc_client(self):
        def grpc_loop():
            channel = grpc.insecure_channel("localhost:50051")
            stub = game_pb2_grpc.GameServiceStub(channel)

            player_id = f"jugador_{uuid.uuid4().hex[:6]}"
            total_players = 2
            self.local_player_id = player_id

            def action_stream():
                yield game_pb2.PlayerAction(
                    player_id=player_id,
                    action=game_pb2.MOVE,
                    direction=game_pb2.NONE,
                    total_players=total_players if total_players > 0 else None
                )
                while self.grpc_running:
                    if self.pending_actions:
                        args = self.pending_actions.pop(0)
                        action_type, direction = args[0], args[1]
                        kwargs = dict(
                            player_id=player_id,
                            action=action_type,
                            direction=direction
                        )
                        # Agrega los campos opcionales SOLO si no son None y son string
                        if len(args) > 2 and args[2] is not None:
                            kwargs["pickup_trash_id"] = str(args[2])
                        if len(args) > 3 and args[3] is not None:
                            kwargs["deposit_trash_id"] = str(args[3])
                        if len(args) > 4 and args[4] is not None:
                            kwargs["deposit_bin_type"] = str(args[4])
                        print(f"[DEBUG] kwargs enviados: {kwargs}")
                        action = game_pb2.PlayerAction(**kwargs)
                        print(f"[DEBUG] Enviando acción al servidor: {action}")
                        yield action
                    else:
                        time.sleep(0.05)

            try:
                for game_state in stub.Connect(action_stream()):
                    tick = getattr(game_state, 'tick', None)
                    # print(f"[gRPC] Tick recibido: {tick if tick is not None else 'N/A'}")
                    # Actualiza las posiciones de todos los jugadores
                    with self.players_positions_lock:
                        current_ids = set(p.player_id for p in game_state.players if p.player_id)
                        for pid in list(self.players_dict.keys()):
                            if pid not in current_ids:
                                del self.players_dict[pid]
                        self.players_positions = {
                            p.player_id: (p.x, p.y)
                            for p in game_state.players if p.player_id
                        }
                        for p in game_state.players:
                            if p.player_id and p.player_id not in self.players_dict:
                                self.players_dict[p.player_id] = Player(
                                    (p.x, p.y),
                                    self.all_sprites, self.collision_sprites, self.trash_group
                                )
                                self.players_dict[p.player_id].interp_pos = pygame.Vector2(p.x, p.y)
                                self.players_dict[p.player_id].target_pos = pygame.Vector2(p.x, p.y)
                            elif p.player_id:
                                new_rect = self.players_dict[p.player_id].rect.copy()
                                new_rect.topleft = (round(p.x), round(p.y))
                                collision = pygame.sprite.spritecollideany(
                                    type('TempSprite', (pygame.sprite.Sprite,), {'rect': new_rect})(),
                                    self.collision_sprites
                                )
                                if not collision:
                                    self.players_dict[p.player_id].target_pos = pygame.Vector2(p.x, p.y)

                    # LOG: crear/eliminar basura
                    trash_list = getattr(game_state, "trash", [])
                    server_trash_ids = set()
                    for t in trash_list:
                        server_trash_ids.add(t.id)
                        if t.id not in self.trash_dict:
                            print(f"[TRASH] Creando basura {t.id} tipo {t.type} en ({t.x},{t.y}) imagen={getattr(t, 'image', None)}")
                            trash = Trash((t.x, t.y), (self.all_sprites, self.trash_group), t.type, image_name=getattr(t, "image", None))
                            trash.id = t.id
                            self.trash_dict[t.id] = trash
                        else:
                            self.trash_dict[t.id].rect.topleft = (t.x, t.y)
                    # Elimina basura local de forma segura
                    for tid in [tid for tid in list(self.trash_dict.keys()) if tid not in server_trash_ids]:
                        print(f"[TRASH] Eliminando basura local {tid}")
                        self.trash_dict[tid].kill()
                        del self.trash_dict[tid]

                    # Sincroniza el puntaje y estado de basura cargada de cada jugador
                    scores = getattr(game_state, "scores", {})
                    for pid, player in self.players_dict.items():
                        # Actualiza el puntaje si está en el estado
                        if hasattr(game_state, "scores") and pid in game_state.scores:
                            prev_score = getattr(player, "score", 0)
                            player.score = game_state.scores[pid]
                            # Si el score del jugador local subió, muestra mensaje
                            if pid == self.local_player_id and player.score > self.last_score:
                                self.score_message = f"+{player.score - self.last_score} puntos!"
                                self.score_message_time = time.time()
                                self.last_score = player.score
                                # Limpiar atributos de basura cargada al depositar y ganar puntos
                                player.carrying_trash = False
                                player.carrying_trash_type = None
                                player.carrying_trash_id = None
                                player.carrying_trash_image = None
                        # Si el jugador tiene una basura cargada (no está en trash_dict pero tiene carrying_trash_id)
                        if hasattr(player, "carrying_trash_id") and player.carrying_trash_id:
                            if player.carrying_trash_id not in self.trash_dict:
                                player.carrying_trash = True
                            else:
                                player.carrying_trash = False
                        else:
                            player.carrying_trash = False

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
            return
        self.pending_actions.append((action, direction, None))

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
                    if event.key == pygame.K_SPACE:
                        if self.local_player_id and self.local_player_id in self.players_dict:
                            player = self.players_dict[self.local_player_id]
                            # Solo permite recoger si NO está cargando basura
                            if not getattr(player, "carrying_trash", False):
                                found = False
                                for trash in list(self.trash_dict.values()):
                                    print(f"[DEBUG] Player hitbox: {player.hitbox_rect} Trash hitbox: {trash.hitbox_rect}")
                                    if player.hitbox_rect.colliderect(trash.hitbox_rect):
                                        dx = player.rect.centerx - trash.rect.centerx
                                        dy = player.rect.centery - trash.rect.centery
                                        dist = (dx**2 + dy**2) ** 0.5
                                        print(f"[TRASH] Intentando recoger basura {trash.id} tipo {trash.type} en {trash.rect.topleft} (jugador en {player.rect.topleft}) dist={dist:.1f}")
                                        print(f"[TRASH] ¡Colisión detectada con basura {trash.id}!")
                                        print(f"[TRASH] Enviando pickup_trash_id={trash.id} al servidor")
                                        # SIEMPRE envía la petición al servidor
                                        self.pending_actions.append((
                                            game_pb2.MOVE, game_pb2.NONE, trash.id
                                        ))
                                        # Marca el intento de cargar, pero solo muestra el ícono si la basura ya no está en trash_dict
                                        player.carrying_trash_id = trash.id
                                        player.carrying_trash_type = trash.type
                                        player.carrying_trash_image = trash.image
                                        found = True
                                        break
                                if not found:
                                    print("[TRASH] No hay colisión con ninguna basura.")
                                # No marques carrying_trash aquí, solo cuando la basura desaparezca
                            else:
                                print("[TRASH] Ya estás cargando basura, deposítala antes de recoger otra.")
                    if event.key == pygame.K_e:
                        if self.local_player_id and self.local_player_id in self.players_dict:
                            player = self.players_dict[self.local_player_id]
                            # Permite depositar si tiene un id de basura cargada
                            trash_id = getattr(player, "carrying_trash_id", None)
                            trash_type = getattr(player, "carrying_trash_type", None)
                            if trash_id and trash_type:
                                for bin in self.trash_bins:
                                    if player.hitbox_rect.colliderect(bin.hitbox_rect):
                                        if bin.type == trash_type:
                                            self.pending_actions.append((
                                                game_pb2.MOVE, game_pb2.NONE, None, trash_id, bin.type
                                            ))
                                            print(f"[TRASH] Depositando basura tipo {trash_type} en bin {bin.type}")
                                            # Solo borra los datos después de enviar la acción
                                            player.carrying_trash = False
                                            player.carrying_trash_type = None
                                            player.carrying_trash_id = None
                                        break
                elif event.type == pygame.KEYUP:
                    if event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
                        self.keys_pressed.discard(event.key)

            # Limpiar superficie del mapa sin zoom
            self.map_surface.fill((30, 30, 30))

            # Dibujar todos los sprites (mapa, basura, bins, etc) en la superficie sin zoom
            sprites_with_image = [spr for spr in self.all_sprites if hasattr(spr, "image")]
            if sprites_with_image:
                pygame.sprite.Group(sprites_with_image).draw(self.map_surface)

            # Actualizar y dibujar jugadores
            with self.players_positions_lock:
                for player_id, pos in self.players_positions.items():
                    if player_id in self.players_dict:
                        player = self.players_dict[player_id]
                        new_rect = player.rect.copy()
                        new_rect.topleft = (round(pos[0]), round(pos[1]))
                        collision = pygame.sprite.spritecollideany(
                            type('TempSprite', (pygame.sprite.Sprite,), {'rect': new_rect})(),
                            self.collision_sprites
                        )
                        if not collision:
                            player.target_pos = pygame.Vector2(pos)
                        if not hasattr(player, "interp_pos"):
                            player.interp_pos = pygame.Vector2(player.rect.topleft)
                        speed = 200  # píxeles por segundo (ajusta a gusto)
                        direction = player.target_pos - player.interp_pos
                        distance = direction.length()
                        if distance > 0:
                            move_dist = min(speed * dt, distance)
                            if direction.length_squared() > 0:
                                direction = direction.normalize()
                            new_interp_pos = player.interp_pos + direction * move_dist
                            new_rect = player.rect.copy()
                            new_rect.topleft = (round(new_interp_pos.x), round(new_interp_pos.y))
                            collision = pygame.sprite.spritecollideany(
                                type('TempSprite', (pygame.sprite.Sprite,), {'rect': new_rect})(),
                                self.collision_sprites
                            )
                            if not collision:
                                player.interp_pos = new_interp_pos
                        player.rect.topleft = (round(player.interp_pos.x), round(player.interp_pos.y))
                        player.hitbox_rect.center = player.rect.center

                        # Solo marca carrying_trash=True si la basura ya no está en trash_dict
                        if hasattr(player, "carrying_trash_id"):
                            if player.carrying_trash_id not in self.trash_dict:
                                player.carrying_trash = True
                            else:
                                player.carrying_trash = False

                        if direction.length_squared() > 0:
                            player.direction = direction.normalize()
                        else:
                            player.direction = pygame.Vector2(0, 0)
                        player.animate(dt)
                        self.map_surface.blit(player.image, player.rect)
                        # Dibuja el ícono de basura para todos los jugadores que estén cargando
                        if player.carrying_trash:
                            player.draw_trash_icon(self.map_surface)

            # Dibuja hitboxes para depuración
            if DEBUG_DRAW_HITBOX:
                # Dibuja hitbox del jugador local en rojo
                if self.local_player_id and self.local_player_id in self.players_dict:
                    player = self.players_dict[self.local_player_id]
                    pygame.draw.rect(self.map_surface, (255, 0, 0), player.hitbox_rect, 2)
                # Dibuja hitboxes de todas las basuras en azul
                for trash in self.trash_dict.values():
                    pygame.draw.rect(self.map_surface, (0, 0, 255), trash.hitbox_rect, 2)

            # Escalar superficie para zoom
            scaled_surface = pygame.transform.scale(
                self.map_surface,
                (int(self.map_surface.get_width() * ZOOM), int(self.map_surface.get_height() * ZOOM))
            )
            self.display_surface.blit(scaled_surface, (0, 0))

            # Dibuja los puntajes de todos los jugadores en la pantalla
            font = pygame.font.SysFont(None, 32)
            y = 10
            score_texts = []
            max_width = 0
            for pid, player in self.players_dict.items():
                score_text = f"{pid}: {getattr(player, 'score', 0)}"
                color = (255, 255, 0) if pid == self.local_player_id else (200, 200, 200)
                text_surf = font.render(score_text, True, color)
                score_texts.append((text_surf, color, score_text))
                if text_surf.get_width() > max_width:
                    max_width = text_surf.get_width()
            # Calcula el alto total del fondo
            bg_height = len(score_texts) * 30 + 10
            bg_width = max_width + 20
            # Dibuja fondo semitransparente
            score_bg = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
            score_bg.fill((0, 0, 0, 180))  # negro con alpha
            self.display_surface.blit(score_bg, (5, 5))
            # Dibuja los textos encima del fondo
            y_offset = 10
            for text_surf, color, score_text in score_texts:
                self.display_surface.blit(text_surf, (15, y_offset))
                y_offset += 30

            # Dibuja mensaje de puntos si corresponde
            if self.score_message and (time.time() - self.score_message_time < 2):
                msg_font = pygame.font.SysFont(None, 48)
                msg_surf = msg_font.render(self.score_message, True, (0, 255, 0))
                rect = msg_surf.get_rect(center=(WINDOW_WIDTH // 2, 60))
                self.display_surface.blit(msg_surf, rect)
            elif self.score_message and (time.time() - self.score_message_time >= 2):
                self.score_message = ""

            pygame.display.flip()

        pygame.quit()


if __name__ == '__main__':
    game = Game()
    game.run()
