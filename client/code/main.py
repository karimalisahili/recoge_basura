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
from os.path import join, dirname

DEBUG_DRAW_HITBOX = False  # Activa el dibujo de hitboxes

SOUNDS_PATH = join(dirname(dirname(__file__)), 'sound')

ZOOM = 0.4  # Ajusta el zoom aquí (1 = normal, 2 = doble, etc)

SERVER_IP = "192.168.0.127"  # IP del servidor
SERVER_PORT = 50051

def show_menu(display_surface):
    try:
        recycle_img = pygame.image.load(join('images', 'reciclaje.png')).convert_alpha()
        garbage_img = pygame.image.load(join('images', 'trash.png')).convert_alpha()
        compost_img = pygame.image.load(join('images', 'compost.png')).convert_alpha()
        # Ajusta el tamaño si es necesario
        icon_size = (200, 200)
        recycle_img = pygame.transform.scale(recycle_img, icon_size)
        garbage_img = pygame.transform.scale(garbage_img, icon_size)
        compost_img = pygame.transform.scale(compost_img, icon_size)
    except Exception as e:
        print(f"No se pudieron cargar las imágenes de tipos de basura: {e}")
        recycle_img = garbage_img = compost_img = None

    pygame.mixer.music.load(join(SOUNDS_PATH, 'title music.mp3'))
    pygame.mixer.music.set_volume(0.5)  # Volumen (0.0 a 1.0)
    pygame.mixer.music.play(-1)
    font = pygame.font.SysFont(None, 60)
    small_font = pygame.font.SysFont(None, 36)
    menu_options = ["Jugar", "Cómo jugar"]
    selected = 0
    running = True
    show_instructions = False

    # Carga la imagen del logo (ajusta la ruta si es necesario)
    logo_path = join('images', 'recogebasura.png')
    try:
        logo_img = pygame.image.load(logo_path).convert_alpha()
        logo_img = pygame.transform.scale(logo_img, (220, 220))  # Ajusta el tamaño si quieres
    except Exception as e:
        print(f"No se pudo cargar la imagen del logo: {e}")
        logo_img = None

    instructions = [
        "Recoge la basura y llévala al bote correcto.",
        "Usa las flechas para moverte.",
        "Presiona ESPACIO para recoger la basura.",
        "Presiona E para desechar la basura.",
        "¡Clasifica correctamente para ganar puntos!",
        "",
        "Presiona ESC para volver."
    ]

    while running:
        display_surface.fill((30, 30, 30))
        if show_instructions:
            y = 120
            for line in instructions:
                text = small_font.render(line, True, (255, 255, 255))
                display_surface.blit(text, (80, y))
                y += 40
            if recycle_img and garbage_img and compost_img:
                total_width = recycle_img.get_width() + garbage_img.get_width() + compost_img.get_width() + 40  # 20px de espacio entre imágenes
                start_x = (display_surface.get_width() - total_width) // 2
                img_y = display_surface.get_height() - recycle_img.get_height() - 40  # 40px desde abajo

                display_surface.blit(recycle_img, (start_x, img_y))
                display_surface.blit(garbage_img, (start_x + recycle_img.get_width() + 20, img_y))
                display_surface.blit(compost_img, (start_x + recycle_img.get_width() + 20 + garbage_img.get_width() + 20, img_y))        
        else:
            # Centra el título en la parte superior
            title = font.render("Recoge Basura", True, (200, 255, 200))
            title_rect = title.get_rect()
            title_rect.centerx = display_surface.get_width() // 2
            title_rect.top = 40  # Puedes ajustar este valor para subir o bajar el título
            display_surface.blit(title, title_rect)

            # Dibuja la imagen centrada y un poco más arriba
            logo_y = 120  # Puedes ajustar este valor para subir o bajar el logo
            if logo_img:
                img_rect = logo_img.get_rect()
                img_rect.centerx = display_surface.get_width() // 2
                img_rect.top = logo_y
                display_surface.blit(logo_img, img_rect)
                options_start_y = img_rect.bottom + 40  # Opciones debajo del logo
            else:
                options_start_y = logo_y + 220 + 40  # Si no hay logo, deja el espacio igual

            # Dibuja las opciones debajo del logo
            for i, option in enumerate(menu_options):
                color = (255, 255, 0) if i == selected else (255, 255, 255)
                text = small_font.render(option, True, color)
                text_rect = text.get_rect()
                text_rect.centerx = display_surface.get_width() // 2
                text_rect.top = options_start_y + i * 50  # Espaciado entre opciones
                display_surface.blit(text, text_rect)

        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if show_instructions:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    show_instructions = False
            else:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        selected = (selected - 1) % len(menu_options)
                    elif event.key == pygame.K_DOWN:
                        selected = (selected + 1) % len(menu_options)
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        if selected == 0:
                            running = False  # Inicia el juego
                        elif selected == 1:
                            show_instructions = True

def show_game_over(display_surface, scores_dict):
    font = pygame.font.SysFont(None, 60)
    small_font = pygame.font.SysFont(None, 36)
    running = True

    # Ordena los puntajes de mayor a menor
    sorted_scores = sorted(scores_dict.items(), key=lambda x: x[1], reverse=True)
    if sorted_scores:
        max_score = sorted_scores[0][1]
        winners = [name for name, score in sorted_scores if score == max_score]
    else:
        winners = []
        max_score = 0

    options = ["Volver al menú principal"]
    selected = 0

    while running:
        display_surface.fill((30, 30, 30))
        title = font.render("¡Juego Terminado!", True, (255, 255, 255))
        title_rect = title.get_rect(center=(display_surface.get_width() // 2, 80))
        display_surface.blit(title, title_rect)

        y = 180
        for i, (name, score) in enumerate(sorted_scores):
            color = (0, 255, 0) if score == max_score else (255, 255, 255)
            text = small_font.render(f"{name}: {score}", True, color)
            text_rect = text.get_rect(center=(display_surface.get_width() // 2, y))
            display_surface.blit(text, text_rect)
            y += 50

        # Mostrar empate si hay más de un ganador
        if len(winners) > 1:
            winner_text = small_font.render(f"Empate entre: {', '.join(winners)}", True, (255, 215, 0))
        elif winners:
            winner_text = small_font.render(f"Ganador: {winners[0]}", True, (255, 215, 0))
        else:
            winner_text = small_font.render("Sin ganadores", True, (255, 215, 0))
        winner_rect = winner_text.get_rect(center=(display_surface.get_width() // 2, y + 30))
        display_surface.blit(winner_text, winner_rect)

        # Opciones de menú
        options_y = y + 80
        for i, option in enumerate(options):
            color = (255, 255, 0) if i == selected else (200, 200, 200)
            opt_text = small_font.render(option, True, color)
            opt_rect = opt_text.get_rect(center=(display_surface.get_width() // 2, options_y + i * 50))
            display_surface.blit(opt_text, opt_rect)

        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "exit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    if selected == 0:
                        return "menu"
                    elif selected == 1:
                        return "play_again"
                elif event.key == pygame.K_ESCAPE:
                    return "menu"

def show_waiting_room(display_surface, player_name, total_players, get_connected_count, player_list=None):
    font = pygame.font.SysFont(None, 48)
    small_font = pygame.font.SysFont(None, 36)
    running = True
    while running:
        display_surface.fill((30, 30, 30))
        title = font.render("Sala de espera", True, (255, 255, 255))
        title_rect = title.get_rect(center=(display_surface.get_width() // 2, 100))
        display_surface.blit(title, title_rect)
        name_text = small_font.render(f"Jugador: {player_name}", True, (255, 255, 0))
        name_rect = name_text.get_rect(center=(display_surface.get_width() // 2, 180))
        display_surface.blit(name_text, name_rect)
        connected = get_connected_count()
        info_text = small_font.render(f"Jugadores conectados: {connected}/{total_players}", True, (200, 255, 200))
        info_rect = info_text.get_rect(center=(display_surface.get_width() // 2, 250))
        display_surface.blit(info_text, info_rect)
        # Mostrar lista de jugadores conectados si está disponible
        if player_list:
            y = 290
            for pname in player_list:
                ptext = small_font.render(f"- {pname}", True, (255, 255, 255))
                prect = ptext.get_rect(center=(display_surface.get_width() // 2, y))
                display_surface.blit(ptext, prect)
                y += 30
        if connected < total_players:
            wait_text = small_font.render("Esperando a más jugadores...", True, (255, 255, 255))
            wait_rect = wait_text.get_rect(center=(display_surface.get_width() // 2, 320 + (len(player_list) if player_list else 0)*10))
            display_surface.blit(wait_text, wait_rect)
        pygame.display.update()
        if connected >= total_players:
            pygame.time.wait(1000)
            return
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

def show_error_message(display_surface, message):
    font = pygame.font.SysFont(None, 48)
    small_font = pygame.font.SysFont(None, 32)
    running = True
    while running:
        display_surface.fill((30, 30, 30))
        text = font.render("Error", True, (255, 80, 80))
        text_rect = text.get_rect(center=(display_surface.get_width() // 2, 160))
        display_surface.blit(text, text_rect)
        lines = message.split('\n')
        for i, line in enumerate(lines):
            msg = small_font.render(line, True, (255, 255, 255))
            msg_rect = msg.get_rect(center=(display_surface.get_width() // 2, 240 + i * 36))
            display_surface.blit(msg, msg_rect)
        ok_text = small_font.render("[ OK ]", True, (255, 255, 0))
        ok_rect = ok_text.get_rect(center=(display_surface.get_width() // 2, 340 + len(lines)*10))
        display_surface.blit(ok_text, ok_rect)
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                return

def ask_player_name(display_surface):
    font = pygame.font.SysFont(None, 48)
    small_font = pygame.font.SysFont(None, 36)
    name = ""
    running = True
    while running:
        display_surface.fill((30, 30, 30))
        title = font.render("Ingresa tu nombre:", True, (255, 255, 255))
        title_rect = title.get_rect(center=(display_surface.get_width() // 2, 120))
        display_surface.blit(title, title_rect)
        name_text = small_font.render(name + "|", True, (255, 255, 0))
        name_rect = name_text.get_rect(center=(display_surface.get_width() // 2, 200))
        display_surface.blit(name_text, name_rect)
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and name.strip():
                    return name.strip()
                elif event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif event.key == pygame.K_ESCAPE:
                    return None
                elif event.unicode and len(name) < 16 and event.unicode.isprintable():
                    name += event.unicode

def ask_total_players(display_surface):
    font = pygame.font.SysFont(None, 48)
    small_font = pygame.font.SysFont(None, 36)
    options = [2, 3, 4]
    selected = 0
    running = True
    while running:
        display_surface.fill((30, 30, 30))
        title = font.render("¿Cuántos jugadores?", True, (255, 255, 255))
        title_rect = title.get_rect(center=(display_surface.get_width() // 2, 120))
        display_surface.blit(title, title_rect)
        for i, num in enumerate(options):
            color = (255, 255, 0) if i == selected else (255, 255, 255)
            text = small_font.render(str(num), True, color)
            text_rect = text.get_rect(center=(display_surface.get_width() // 2, 220 + i * 60))
            display_surface.blit(text, text_rect)
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    return options[selected]

class Game:
    def __init__(self, player_name, total_players=None, join_existing=False):
        pygame.init()
        pygame.mixer.init()
        self.pickup_sound = pygame.mixer.Sound(join(SOUNDS_PATH, 'switch.wav'))
        self.deposit_sound = pygame.mixer.Sound(join(SOUNDS_PATH, 'positive.wav'))
        self.game_started = False
        self.game_finished = False
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

        self.map_width = 40
        self.map_height = 40
        self.map_surface = pygame.Surface((self.map_width * TILE_SIZE, self.map_height * TILE_SIZE))

        self.keys_pressed = set()
        self.last_score = 0
        self.score_message_time = 0
        self.score_message = ""

        self.player_name = player_name
        self.total_players = total_players
        self.join_existing = join_existing

        self.grpc_error = None
        self.connected_players_count = 1
        self.connected_player_names = [player_name]

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

    def start_grpc_client(self):
        def grpc_loop():
            channel = grpc.insecure_channel(f"{SERVER_IP}:{SERVER_PORT}")
            stub = game_pb2_grpc.GameServiceStub(channel)
            player_id = self.player_name
            total_players = self.total_players if not self.join_existing else 0
            self.local_player_id = player_id
            def action_stream():
                yield game_pb2.PlayerAction(
                    player_id=player_id,
                    action=game_pb2.MOVE,
                    direction=game_pb2.NONE,
                    total_players=total_players if total_players else None
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
                        if len(args) > 2 and args[2] is not None:
                            kwargs["pickup_trash_id"] = str(args[2])
                        if len(args) > 3 and args[3] is not None:
                            kwargs["deposit_trash_id"] = str(args[3])
                        if len(args) > 4 and args[4] is not None:
                            kwargs["deposit_bin_type"] = str(args[4])
                        action = game_pb2.PlayerAction(**kwargs)
                        yield action
                    else:
                        time.sleep(0.05)
            try:
                for game_state in stub.Connect(action_stream()):
                    if not self.grpc_running:
                        break
                    self.game_started = getattr(game_state, "game_started", False)
                    self.game_finished = getattr(game_state, "game_finished", False)
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
                        # Actualiza lista de nombres conectados para la sala de espera
                        self.connected_players_count = len(game_state.players)
                        self.connected_player_names = [p.player_id for p in game_state.players]
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

                    trash_list = getattr(game_state, "trash", [])
                    server_trash_ids = set()
                    for t in trash_list:
                        server_trash_ids.add(t.id)
                        if t.id not in self.trash_dict:
                            trash = Trash((t.x, t.y), (self.all_sprites, self.trash_group), t.type, image_name=getattr(t, "image", None))
                            trash.id = t.id
                            self.trash_dict[t.id] = trash
                        else:
                            self.trash_dict[t.id].rect.topleft = (t.x, t.y)
                    # Fix: avoid changing dict size during iteration
                    tids_to_remove = [tid for tid in self.trash_dict.keys() if tid not in server_trash_ids]
                    for tid in tids_to_remove:
                        self.trash_dict[tid].kill()
                        del self.trash_dict[tid]

                    scores = getattr(game_state, "scores", {})
                    for pid, player in self.players_dict.items():
                        if hasattr(game_state, "scores") and pid in game_state.scores:
                            prev_score = getattr(player, "score", 0)
                            player.score = game_state.scores[pid]
                            if pid == self.local_player_id and player.score > self.last_score:
                                self.score_message = f"+{player.score - self.last_score} puntos!"
                                self.score_message_time = time.time()
                                self.last_score = player.score
                                player.carrying_trash = False
                                player.carrying_trash_type = None
                                player.carrying_trash_id = None
                                player.carrying_trash_image = None
                        if hasattr(player, "carrying_trash_id") and player.carrying_trash_id:
                            if player.carrying_trash_id not in self.trash_dict:
                                player.carrying_trash = True
                            else:
                                player.carrying_trash = False
                        else:
                            player.carrying_trash = False

            except grpc.RpcError as e:
                print("Error de conexión gRPC:", e)
                self.grpc_error = str(e)
        self.grpc_running = True
        self.grpc_thread = threading.Thread(target=grpc_loop, daemon=True)
        self.grpc_thread.start()

    def stop_grpc_client(self):
        self.grpc_running = False
        if self.grpc_thread and self.grpc_thread.is_alive():
            self.grpc_thread.join(timeout=1)

    def get_connected_players_count(self):
        return getattr(self, "connected_players_count", 1)

    def get_connected_player_names(self):
        return getattr(self, "connected_player_names", [self.player_name])

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
        if self.total_players:
            while not getattr(self, "game_started", False):
                if self.grpc_error:
                    result = self.grpc_error
                    if "details =" in result:
                        import re
                        m = re.search(r'details = "(.*?)"', result)
                        if m:
                            result = m.group(1)
                    show_error_message(self.display_surface, result)
                    return "grpc_error"
                show_waiting_room(
                    self.display_surface,
                    self.player_name,
                    self.total_players,
                    self.get_connected_players_count,
                    self.get_connected_player_names()
                )
                pygame.time.wait(500)

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
                            if not getattr(player, "carrying_trash", False):
                                found = False
                                for trash in list(self.trash_dict.values()):
                                    if player.hitbox_rect.colliderect(trash.hitbox_rect):
                                        dx = player.rect.centerx - trash.rect.centerx
                                        dy = player.rect.centery - trash.rect.centery
                                        dist = (dx**2 + dy**2) ** 0.5
                                        self.pending_actions.append((
                                            game_pb2.MOVE, game_pb2.NONE, trash.id
                                        ))
                                        player.carrying_trash_id = trash.id
                                        player.carrying_trash_type = trash.type
                                        player.carrying_trash_image = trash.image
                                        found = True
                                        self.pickup_sound.play()
                                        break
                                if not found:
                                    print("[TRASH] No hay colisión con ninguna basura.")
                            else:
                                print("[TRASH] Ya estás cargando basura, deposítala antes de recoger otra.")
                    if event.key == pygame.K_e:
                        if self.local_player_id and self.local_player_id in self.players_dict:
                            player = self.players_dict[self.local_player_id]
                            trash_id = getattr(player, "carrying_trash_id", None)
                            trash_type = getattr(player, "carrying_trash_type", None)
                            if trash_id and trash_type:
                                for bin in self.trash_bins:
                                    if player.hitbox_rect.colliderect(bin.hitbox_rect):
                                        if bin.type == trash_type:
                                            self.pending_actions.append((
                                                game_pb2.MOVE, game_pb2.NONE, None, trash_id, bin.type
                                            ))
                                            player.carrying_trash = False
                                            player.carrying_trash_type = None
                                            player.carrying_trash_id = None
                                            # Sonido positivo
                                            try:
                                                pygame.mixer.Sound(join(SOUNDS_PATH, "positive.wav")).play()
                                            except Exception as e:
                                                print(f"Error al reproducir positive.wav: {e}")
                                        else:
                                            # Sonido negativo
                                            try:
                                                sound = pygame.mixer.Sound(join(SOUNDS_PATH, "negative.wav"))
                                                sound.set_volume(1.0)
                                                sound.play()
                                                
                                            except Exception as e:
                                                print(f"Error al reproducir negative.wav: {e}")
                                        break
                elif event.type == pygame.KEYUP:
                    if event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
                        self.keys_pressed.discard(event.key)

            self.map_surface.fill((30, 30, 30))

            sprites_with_image = [spr for spr in self.all_sprites if hasattr(spr, "image")]
            if sprites_with_image:
                pygame.sprite.Group(sprites_with_image).draw(self.map_surface)

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
                        speed = 200
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
                        if player.carrying_trash:
                            player.draw_trash_icon(self.map_surface)

            if DEBUG_DRAW_HITBOX:
                if self.local_player_id and self.local_player_id in self.players_dict:
                    player = self.players_dict[self.local_player_id]
                    pygame.draw.rect(self.map_surface, (255, 0, 0), player.hitbox_rect, 2)
                for trash in self.trash_dict.values():
                    pygame.draw.rect(self.map_surface, (0, 0, 255), trash.hitbox_rect, 2)

            scaled_surface = pygame.transform.scale(
                self.map_surface,
                (int(self.map_surface.get_width() * ZOOM), int(self.map_surface.get_height() * ZOOM))
            )
            self.display_surface.blit(scaled_surface, (-300, -300))

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
            bg_height = len(score_texts) * 30 + 10
            bg_width = max_width + 20
            score_bg = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
            score_bg.fill((0, 0, 0, 180))
            self.display_surface.blit(score_bg, (5, 5))
            y_offset = 10
            for text_surf, color, score_text in score_texts:
                self.display_surface.blit(text_surf, (15, y_offset))
                y_offset += 30

            if self.score_message and (time.time() - self.score_message_time < 2):
                msg_font = pygame.font.SysFont(None, 48)
                msg_surf = msg_font.render(self.score_message, True, (0, 255, 0))
                rect = msg_surf.get_rect(center=(WINDOW_WIDTH // 2, 60))
                self.display_surface.blit(msg_surf, rect)
            elif self.score_message and (time.time() - self.score_message_time >= 2):
                self.score_message = ""

            if getattr(self, "game_finished", False):
                scores = {pid: getattr(player, "score", 0) for pid, player in self.players_dict.items()}
                self.stop_grpc_client()
                return scores

            pygame.display.flip()

        self.stop_grpc_client()
        pygame.quit()

if __name__ == '__main__':
    pygame.init()
    pygame.mixer.init()
    display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    while True:
        show_menu(display_surface)
        player_name = None
        while not player_name:
            player_name = ask_player_name(display_surface)
        total_players = None
        while not total_players:
            total_players = ask_total_players(display_surface)
        pygame.mixer.music.load(join(SOUNDS_PATH, 'game music.mp3'))
        pygame.mixer.music.play(-1)
        game = Game(player_name, total_players=total_players, join_existing=False)
        result = game.run()
        if result == "grpc_error":
            continue
        if isinstance(result, str) and ("ya existe una sala creada" in result or "llena" in result or "el primer jugador debe definir" in result or "no hay salas disponibles" in result):
            if "details =" in result:
                import re
                m = re.search(r'details = "(.*?)"', result)
                if m:
                    result = m.group(1)
            show_error_message(display_surface, result)
            continue
        if isinstance(result, dict):
            action = show_game_over(display_surface, result)
            if action == "menu":
                continue
            elif action == "play_again":
                continue
            else:
                break
