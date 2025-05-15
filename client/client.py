import grpc 
import game_pb2
import game_pb2_grpc
import sys
import threading
import time
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


"""
Espera a que el juego comience, imprimiendo actualizaciones del servidor.

Args:
    stub (GameServiceStub): El cliente gRPC generado para el servicio GameService.
    player_id (str): El ID del jugador que espera el inicio del juego.
Returns:
    None
""" 
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

"""
Recibe la entrada del usuario y envía actualizaciones al servidor.
Args:
    player_id (str): El ID del jugador que envía la actualización.
    send_queue (list): Cola de actualizaciones a enviar al servidor.
    stop_event (threading.Event): Evento para detener el hilo de entrada.
Returns:
    None
""" 

def input_loop(player_id, send_queue, stop_event):
    #Mientras no se cierre la conexion
    while not stop_event.is_set():
        try:
            x_input = input("X (Enter vacío para salir): ")
            if x_input.strip() == "":
                print("[Cliente] Saliendo del juego.")
                stop_event.set()
                break
            x = float(x_input)
            y = float(input("Y: "))
            action = input("Acción (pickup, attack, etc): ")

            # Crear posicion tipo coordenadas del .proto
            position = game_pb2.Position(x=x, y=y)

            # Crear el mensaje de solicitud de actualización del juego
            update = game_pb2.GameUpdateRequest(
                player_id=player_id,
                position=position,
                action=action
            )
            # Agregar la actualización a la cola de envío
            send_queue.append(update)
        except ValueError:
            print("[Cliente] Coordenadas inválidas. Intente de nuevo.")


"""
Envía actualizaciones del juego al servidor.
Args:
    send_queue (list): Cola de actualizaciones a enviar al servidor.
    stop_event (threading.Event): Evento para detener el hilo de envío.
Returns:
    None
"""
def game_update_sender(send_queue, stop_event):
    while not stop_event.is_set() or send_queue:
        if send_queue:
            yield send_queue.pop(0)
        else:
            time.sleep(0.1)  # Evita alto uso de CPU
"""
Recibe actualizaciones del servidor y las imprime en la consola.
Args:
    responses (list): Lista de respuestas del servidor.
    player_id (str): El ID del jugador que recibe las actualizaciones.
    stop_event (threading.Event): Evento para detener el hilo de recepción.
Returns:
    None
"""
def receive_loop(responses, player_id, stop_event):
    try:
        for response in responses:
            print(f"\n[{player_id}] Update del servidor:")
            print(f"Mensaje: {response.message}")
            print(f"Jugadores: {len(response.players_positions)}")
            for p in response.players_positions:
                print(f"  Jugador {p.player_id}: ({p.position.x}, {p.position.y})")
    except grpc.RpcError as e:
        print(f"[{player_id}] Error en la recepción: {e.code()} - {e.details()}")
    #esto es si hay un error
    finally:
        stop_event.set()

"""
Maneja la actualización del juego, creando hilos para enviar y recibir mensajes.
Args:
    stub (GameServiceStub): El cliente gRPC generado para el servicio GameService.
    player_id (str): El ID del jugador que está actualizando el juego.
Returns:
    None
"""
def game_update(stub, player_id):
    # lista compartida donde el hilo de entrada agrega mensajes y el hilo de salida los envía
    send_queue = []
    # evento para detener los hilos
    stop_event = threading.Event()

    # Aquí se pasa el generador a la llamada gRPC
    responses = stub.GameUpdate(game_update_sender(send_queue, stop_event))

    # Hilos para manejar la entrada y salida
    input_thread = threading.Thread(target=input_loop, args=(player_id, send_queue, stop_event))
    receive_thread = threading.Thread(target=receive_loop, args=(responses, player_id, stop_event))

    input_thread.start()
    receive_thread.start()

    input_thread.join()
    receive_thread.join()



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
