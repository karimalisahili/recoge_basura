import grpc 
import game_pb2
import game_pb2_grpc

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
    if(response.player_joined):
        print(f"[Cliente] ID asignado: {response.player_id}")
        print(f"[Cliente] se unio, cantidad de jugadores: {response.total_players_needed}")
    else:
        print(f"[Cliente] no se unio porque la sala esta llena o la , cantidad de jugadores o sala llena: {response.total_players_needed}")

    

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
    create_or_join_game(stub, name, request_players)
    
if __name__ == "__main__":
    main()
