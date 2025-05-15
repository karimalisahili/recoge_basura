import grpc
import threading
import time
import game_pb2
import game_pb2_grpc

class ActionSender:
    def __init__(self, player_id, total_players=None):
        self.player_id = player_id
        self.total_players = total_players
        self.actions = []
        self.lock = threading.Lock()
        self.running = True
        self.first_send = True  # para enviar el total_players solo una vez

    def add_action(self, action_type, direction):
        with self.lock:
            self.actions.append((action_type, direction))

    def action_stream(self):
        while self.running:
            with self.lock:
                if self.first_send:
                    self.first_send = False
                    yield game_pb2.PlayerAction(
                        player_id=self.player_id,
                        action=game_pb2.MOVE,
                        direction=game_pb2.NONE,
                        total_players=self.total_players or 0
                    )
                elif self.actions:
                    action_type, direction = self.actions.pop(0)
                    yield game_pb2.PlayerAction(
                        player_id=self.player_id,
                        action=action_type,
                        direction=direction
                    )
            time.sleep(0.1)


def main():
    player_id = input("Ingresa tu nombre de jugador: ")
    total_players = None
    while True:
        try:
            total_input = input("¿Cuántos jugadores participarán? (solo el primero que conecte debe indicar, dejar vacío si ya está establecido): ")
            if total_input.strip() == "":
                total_players = 0  # No enviamos total_players en ese caso
            else:
                total_players = int(total_input)
                if total_players <= 0:
                    print("Debe ser un número positivo o dejar vacío.")
                    continue
            break
        except ValueError:
            print("Número inválido, intente de nuevo.")

    channel = grpc.insecure_channel("localhost:50051")
    stub = game_pb2_grpc.GameServiceStub(channel)

    sender = ActionSender(player_id, total_players if total_players > 0 else None)

    def receive_game_state(stream):
        game_started = False
        try:
            for state in stream:
                if not state.game_started:
                    print(f"Esperando a que se conecten todos los jugadores... ({len(state.players)}/{total_players if total_players else '?'})")
                    continue
                if not game_started:
                    print("🎮 ¡El juego ha comenzado!")
                    game_started = True
                print(f"\nTick: {state.tick}")
                for player in state.players:
                    print(f"{player.player_id} -> ({player.x}, {player.y})")
        except grpc.RpcError as e:
            print("Conexión cerrada:", e)

    # Intentamos conectar y escuchar estado, si falla por cantidad, pedir que vuelva a intentar
    while True:
        try:
            threading.Thread(target=lambda: receive_game_state(
                stub.Connect(sender.action_stream())
            ), daemon=True).start()
            break
        except grpc.RpcError as e:
            print(f"Error al conectar: {e.details()}")
            total_players = int(input(f"Intenta nuevamente con la cantidad actual de jugadores: "))
            sender.total_players = total_players

    # Entrada de acciones del jugador
    while True:
        cmd = input("> Acción (w/a/s/d, j=salto, k=ataque, q=salir): ").lower()
        if cmd == 'q':
            sender.running = False
            break
        elif cmd == 'w':
            sender.add_action(game_pb2.MOVE, game_pb2.UP)
        elif cmd == 's':
            sender.add_action(game_pb2.MOVE, game_pb2.DOWN)
        elif cmd == 'a':
            sender.add_action(game_pb2.MOVE, game_pb2.LEFT)
        elif cmd == 'd':
            sender.add_action(game_pb2.MOVE, game_pb2.RIGHT)
        elif cmd == 'j':
            sender.add_action(game_pb2.JUMP, game_pb2.UP)
        elif cmd == 'k':
            sender.add_action(game_pb2.ATTACK, game_pb2.RIGHT)
        else:
            print("Comando inválido.")


if __name__ == "__main__":
    main()
