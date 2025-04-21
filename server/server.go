package main

import (
	pb "arcade_racing/server/protos"
	"context"
	"fmt"
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
	players map[string]string
}

// JoinGame es una RPC que permite a un jugador unirse al juego.
//
// @param ctx - contexto de la solicitud RPC
// @param req - solicitud que contiene el nombre del jugador
// @return JoinResponse con el ID generado y un mensaje de bienvenida
// @error si ocurre algún fallo interno
func (s *server) JoinGame(ctx context.Context, req *pb.JoinRequest) (*pb.JoinResponse, error) {

	//Genera un ID único para el jugador
	id := uuid.New().String()

	//Guarda el jugador en el mapa de jugadores
	s.players[id] = req.Name

	//Log del evento
	log.Printf("Jugador %s se unió al juego con ID %s", req.Name, id)

	return &pb.JoinResponse{
		Id:      id,
		Message: fmt.Sprintf("Bienvenido, %s!", req.Name),
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
