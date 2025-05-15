package main

import (
	pb "arcade_racing/server/protos"
	"io"
	"log"
	"net"
	"sync"
	"time"
	"fmt"
	
	"google.golang.org/grpc"
)

// server representa el servidor del juego.
// Implementa la interfaz GameServiceServer generada desde el .proto.
// players es un mapa en memoria que guarda los jugadores conectados por su ID.

type playerConn struct {
    id       string
    stream   pb.GameService_ConnectServer
    actions  chan *pb.PlayerAction
    position *pb.PlayerState
}

type server struct {
    pb.UnimplementedGameServiceServer
    mu            sync.Mutex
    players       map[string]*playerConn
    totalPlayers  int32
    gameStarted   bool
    tick          int32
    gameStartOnce sync.Once
    cond          *sync.Cond
}

func newServer() *server {
    s := &server{
        players: make(map[string]*playerConn),
    }
    s.cond = sync.NewCond(&s.mu)
    return s
}

func (s *server) Connect(stream pb.GameService_ConnectServer) error {
    firstMsg, err := stream.Recv()
    if err != nil {
        return err
    }

    playerID := firstMsg.PlayerId
    fmt.Printf("Jugador conectado: %s\n", playerID)

    s.mu.Lock()
    if len(s.players) == 0 && firstMsg.TotalPlayers != nil && *firstMsg.TotalPlayers > 0 {
        s.totalPlayers = *firstMsg.TotalPlayers
        fmt.Printf("Total de jugadores establecidos: %d\n", s.totalPlayers)
    }

    player := &playerConn{
        id:       playerID,
        stream:   stream,
        actions:  make(chan *pb.PlayerAction, 10),
        position: &pb.PlayerState{PlayerId: playerID, X: 0, Y: 0},
    }
    s.players[playerID] = player
    s.cond.Broadcast()
    s.mu.Unlock()

    // Goroutine que escucha las acciones del jugador
    go func() {
        for {
            action, err := stream.Recv()
            if err == io.EOF || err != nil {
                fmt.Printf("Jugador %s desconectado.\n", playerID)
                break
            }
            player.actions <- action
        }
    }()

    // Esperar hasta que el juego comience
    s.mu.Lock()
    for !s.gameStarted {
        if int32(len(s.players)) == s.totalPlayers {
            s.gameStartOnce.Do(func() {
                fmt.Println("🎮 ¡Comenzando juego!")
                s.gameStarted = true
                go s.gameLoop()
            })
        } else {
            s.cond.Wait()
        }
    }
    s.mu.Unlock()

    // Enviar estados del juego
    for {
        state := s.buildGameState()
        if err := stream.Send(state); err != nil {
            return err
        }
        time.Sleep(200 * time.Millisecond)
    }
}

func (s *server) gameLoop() {
    ticker := time.NewTicker(200 * time.Millisecond)
    defer ticker.Stop()

    for range ticker.C {
        s.mu.Lock()
        s.tick++
        for _, player := range s.players {
            select {
            case action := <-player.actions:
                s.applyAction(player, action)
            default:
                // no-op
            }
        }
        s.mu.Unlock()
    }
}

func (s *server) applyAction(p *playerConn, action *pb.PlayerAction) {
    switch action.Action {
    case pb.ActionType_MOVE:
        switch action.Direction {
        case pb.Direction_UP:
            p.position.Y += 1
        case pb.Direction_DOWN:
            p.position.Y -= 1
        case pb.Direction_LEFT:
            p.position.X -= 1
        case pb.Direction_RIGHT:
            p.position.X += 1
        }
    case pb.ActionType_JUMP:
        p.position.Y += 2
    case pb.ActionType_ATTACK:
        // solo ejemplo, sin lógica aún
        fmt.Printf("%s atacó hacia %v\n", p.id, action.Direction)
    }
}

func (s *server) buildGameState() *pb.GameState {
    players := make([]*pb.PlayerState, 0, len(s.players))
    for _, p := range s.players {
        players = append(players, p.position)
    }

    return &pb.GameState{
        Tick:        s.tick,
        Players:     players,
        GameStarted: true,
    }
}

func main() {
    lis, err := net.Listen("tcp", ":50051")
    if err != nil {
        log.Fatalf("Fallo al escuchar: %v", err)
    }

    grpcServer := grpc.NewServer()
    pb.RegisterGameServiceServer(grpcServer, newServer())

    fmt.Println("Servidor escuchando en puerto 50051...")
    if err := grpcServer.Serve(lis); err != nil {
        log.Fatalf("Error en el servidor: %v", err)
    }
}