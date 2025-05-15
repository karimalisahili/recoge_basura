import grpc 
import game_pb2
import game_pb2_grpc
import sys


"""
Envia una solicitud de union al servidor gRPC con el nombre del jugador.

Args:
    stub (GameServiceStub): El cliete gRPC generado para el servicio GameService.
    name (str): El nombre del jugador que se unirá al juego.
    
Returns:
    None
"""

def create_or_join_game(stub, name, request_players):
    request_players_int = int(request_players)
    request = game_pb2.CreateOrJoinRequest(name=name, request_players=request_players_int)
    response = stub.CreateOrJoinGame(request)
    print(response)
    if response.player_joined:
        player_id = response.player_id
        print(f"[Cliente] ID asignado: {player_id}")
        print(f"[Cliente] Se unió, cantidad de jugadores necesarios: {response.total_players_needed}")
        return player_id  # Devuelve el player_id si la unión fue exitosa
    else:
        print(f"[Cliente] No se unió porque la sala está llena o la cantidad de jugadores es incorrecta: {response.total_players_needed}")
        return None  # Devuelve None si la unión falló



def wait_for_game(stub, player_id):

    request = game_pb2.WaitRequest(player_id=player_id)
    try:
        for update in stub.WaitForGameStart(request):
            print(f"[{player_id}] Actualización: Mensaje='{update.message}', Jugadores={update.current_players}/{update.total_players_needed}, Juego Iniciado={update.game_started}")
            if update.game_started:
                print(f"[{player_id}] El juego ha comenzado!")
                break
    except grpc.RpcError as e:
        print(f"[{player_id}] Error al esperar el juego: {e.code()} - {e.details()}")
    

def game_update_sender(player_id):
    """
    Generador que envía mensajes al servidor en tiempo real.
    Permite enviar múltiples posiciones sucesivamente.
    """
    while True:
        try:
            x_input = input("X (Enter para reintentar o salir con 'exit'): ").strip()
            if x_input == "":
                print("[Cliente] Entrada vacía. No se enviará posición. Intenta de nuevo.")
                continue  # No termina, solo reintenta
            if x_input.lower() == "exit":
                print("[Cliente] Saliendo del juego.")
                break

            x = float(x_input)
            y_input = input("Y: ").strip()
            if y_input == "":
                print("[Cliente] Y no puede estar vacío. Intenta de nuevo.")
                continue
            y = float(y_input)

            action = input("Acción (pickup, attack, etc): ").strip()

            position = game_pb2.Position(x=x, y=y)

            yield game_pb2.GameUpdateRequest(
                player_id=player_id,
                position=position,
                action=action
            )
        except ValueError:
            print("[Cliente] Error: coordenadas inválidas. Intenta de nuevo.")



def game_update(stub, player_id):
    try:
        responses = stub.GameUpdate(game_update_sender(player_id))  # recibe flujo de respuestas
        for response in responses:
            print(f"[{player_id}] Update recibido del servidor:")
            print(f"Mensaje del servidor: {response.message}")
            print("Otros jugadores conectados:")
            for p in response.players_positions:
                print(f"  ID: {p.player_id} | Posición: ({p.position.x}, {p.position.y})")
    except grpc.RpcError as e:
        print(f"[{player_id}] Error en GameUpdate: {e.code()} - {e.details()}")



"""
Crea un canal gRPC hacia el servidor, construye el stub, 
solicita el nombre del usuario por consola  y lo conecta al juego. 

Returns:
    None
"""

def main():
    
    channel = grpc.insecure_channel('localhost:50051')
    stub = game_pb2_grpc.GameServiceStub(channel)
    name = input("Ingrese su nombre: ")
    request_players = input("Ingrese la cantidad de jugadores 2, 3 o 4: ")
    playerId = create_or_join_game(stub, name, request_players)
    
    if playerId is not None:
        wait_for_game(stub, playerId)
        game_update(stub, playerId)
    else:
        print(f"[Cliente] No se pudo unir al juego. Asegúrese de que la sala no esté llena o que la cantidad de jugadores sea correcta.")
        sys.exit()
    
if __name__ == "__main__":
    main()
