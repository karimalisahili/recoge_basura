package main

import (
	pb "arcade_racing/server/protos"
	"context"
	"log"
	"net"
	"sync"
	"time"

	"github.com/google/uuid"
	"google.golang.org/grpc"
)

// server representa el servidor del juego.
// Implementa la interfaz GameServiceServer generada desde el .proto.
// players es un mapa en memoria que guarda los jugadores conectados por su ID.

type server struct {
	pb.UnimplementedGameServiceServer
	mu                    sync.Mutex
	players               map[string]string
	waitingPlayersStreams map[string]pb.GameService_WaitForGameStartServer
	totalPlayersNeeded    int32
	gameStarted           bool
}

// NewServer crea una nueva instancia del servidor con los valores iniciales.
func NewServer() *server {
	return &server{
		players:               make(map[string]string),
		waitingPlayersStreams: make(map[string]pb.GameService_WaitForGameStartServer),
		totalPlayersNeeded:    0,
		gameStarted:           false,
	}
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
	if s.totalPlayersNeeded == 0 {
		s.totalPlayersNeeded = req.RequestPlayers
	}

	//si ya estan todos los jugadores no recibas mas
	if s.totalPlayersNeeded == int32(len(s.players)) {
		player_joined = false
		return &pb.CreateOrJoinResponse{
			PlayerJoined: player_joined,
		}, nil
	}

	if s.totalPlayersNeeded == req.RequestPlayers {

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

	log.Printf("Cantidad de jugadores necesitada: %d ", s.totalPlayersNeeded)
	log.Printf("Cantidad de jugadores en sala %d: ", len(s.players))

	return &pb.CreateOrJoinResponse{
		PlayerId:           id,
		TotalPlayersNeeded: s.totalPlayersNeeded,
		PlayerJoined:       player_joined,
	}, nil
}

func (s *server) WaitForGameStart(req *pb.WaitRequest, stream pb.GameService_WaitForGameStartServer) error {
	//recibir el id del jugador
	var playerId string = req.PlayerId
	log.Printf("Jugador se unió al juego con ID %s", playerId)

	s.mu.Lock()
	s.waitingPlayersStreams[playerId] = stream
	totalPlayersNeeded := s.totalPlayersNeeded
	s.mu.Unlock()

	// iterar en los updates
	for {
		s.mu.Lock()
		gameStarted := s.gameStarted
		currentPlayers := int32(len(s.players))
		s.mu.Unlock()

		err := stream.Send(&pb.GameUpdate{
			Message:            "Esperando jugadores...",
			CurrentPlayers:     currentPlayers,
			TotalPlayersNeeded: totalPlayersNeeded,
			GameStarted:        gameStarted,
		})

		if err != nil {
			//sacar jugador
			s.removeWaitingPlayer(playerId)
			return err
		}

		if gameStarted {
			return nil //El juego ha comenzdo, finalizar el stream para este jugador
		}

		time.Sleep(2 * time.Second) //Actualizar cada 2 segundos
	}
}

// elimina el stream del jugador del mapa de streams
func (s *server) removeWaitingPlayer(playerId string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.waitingPlayersStreams, playerId)
}

// actualiza el estado del juego a iniciado y notifica a todos los jugadores en espera
func (s *server) startGame() {
	s.mu.Lock()
	defer s.mu.Unlock()

	if !s.gameStarted && s.totalPlayersNeeded > 0 && int32(len(s.players)) == s.totalPlayersNeeded {
		log.Println("Suficientes jugadores conectados, el juego comienza")
		s.gameStarted = true
		for _, stream := range s.waitingPlayersStreams {
			go func(st pb.GameService_WaitForGameStartServer) {
				st.Send(&pb.GameUpdate{
					Message:            "¡El juego ha comenzado!",
					CurrentPlayers:     s.totalPlayersNeeded,
					TotalPlayersNeeded: s.totalPlayersNeeded,
					GameStarted:        true,
				})
			}(stream) //se pasa como argumento el valor actual de stream a la funcion
		}
	}
}

// verificar periodicamente si el juego ha comenzado
func (s *server) checkGameStart() {
	for {
		time.Sleep(1 * time.Second)
		s.startGame()
	}
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

	//Instancio el servidor del juego
	gameServer := NewServer()

	//Registra el servicio con la implentación personalizada
	pb.RegisterGameServiceServer(s, gameServer)

	//Inicia una gorutine para verificar periodicamente si el juego puede comenzar
	go gameServer.checkGameStart()

	log.Println("Servidor gRPC escuchando en el puerto 50051...")

	//Inicia el servidor gRPC y maneja las conexiones entrantes
	if err := s.Serve(lis); err != nil {
		log.Fatalf("Error al servir: %v", err)
	}
}
