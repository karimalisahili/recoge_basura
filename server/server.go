package main

import (
	pb "arcade_racing/server/protos"
	"context"
	"log"
	"net"

	"github.com/google/uuid"
	"google.golang.org/grpc"
)

// server representa el servidor del juego.
// Implementa la interfaz GameServiceServer generada desde el .proto.
// players es un mapa en memoria que guarda los jugadores conectados por su ID.

type server struct {
	pb.UnimplementedGameServiceServer
	players              map[string]string
	total_players_needed int32
}

// JoinGame es una RPC que permite a un jugador unirse al juego.
//
// @param ctx - contexto de la solicitud RPC
// @param req - solicitud que contiene el nombre del jugador
// @return JoinResponse con el ID generado y un mensaje de bienvenida
// @error si ocurre algún fallo interno
func (s *server) CreateOrJoinGame(ctx context.Context, req *pb.CreateOrJoinRequest) (*pb.CreateOrJoinResponse, error) {
	var player_joined bool
	var id string = ""

	//Guarda la cantidad de jugadores creada o necesitada
	if s.total_players_needed == 0 {
		s.total_players_needed = req.RequestPlayers
	}

	//si ya estan todos los jugadores no recibas mas
	if s.total_players_needed == int32(len(s.players)) {
		player_joined = false
		return &pb.CreateOrJoinResponse{
			PlayerJoined: player_joined,
		}, nil
	}

	if s.total_players_needed == req.RequestPlayers {

		player_joined = true

		//Genera un ID único para el jugador
		id = uuid.New().String()

		//Guarda el jugador en el mapa de jugadores
		s.players[id] = req.Name

	} else {
		player_joined = false
		log.Printf("cliente no se unio")
	}

	//Log del evento
	if id != "" {
		log.Printf("Jugador %s se unió al juego con ID %s", req.Name, id)
	}

	log.Printf("Cantidad de jugadores necesitada: %d ", s.total_players_needed)
	log.Printf("Cantidad de jugadores en sala %d: ", len(s.players))

	return &pb.CreateOrJoinResponse{
		PlayerId:           id,
		TotalPlayersNeeded: s.total_players_needed,
		PlayerJoined:       player_joined,
	}, nil
}

// main incializa y ejecuta el servidor gRPC del juego.
//
// @description Escucha en el puerto 50051 y registra el servicio del juego.
// Si ocurre un error en la conexión, o al servir, se detiene el servidor.

func main() {

	//Escucha en el puerto 50051 (puerto TCP local)
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatalf("Error al escuchar en el puerto: %v", err)
	}

	//Crea una nueva instancia del servidor gRPC
	s := grpc.NewServer()

	//Registra el servicio con la implentación personalizada
	pb.RegisterGameServiceServer(s, &server{players: make(map[string]string)})

	log.Println("Servidor gRPC escuchando en el puerto 50051...")

	//Inicia el servidor gRPC y maneja las conexiones entrantes
	if err := s.Serve(lis); err != nil {
		log.Fatalf("Error al servir: %v", err)
	}
}
