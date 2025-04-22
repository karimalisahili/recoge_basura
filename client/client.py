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

def join_game(stub, name):
    
    request = game_pb2.JoinRequest(name=name)
    response = stub.JoinGame(request)
    
    print(f"[Cliente] ID asignado: {response.id}")
    print(f"[Servidor] {response.message}")
    

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
    join_game(stub, name)
    
if __name__ == "__main__":
    main()
