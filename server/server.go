package main

import (
	pb "arcade_racing/server/protos"
	"fmt"
	"io"
	"log"
	"math/rand"
	"net"
	"sync"
	"time"

	"google.golang.org/grpc"
)

const (
	TILE_SIZE = 64 // Usa el mismo valor que en el cliente

	// Límites de la colina en tiles
	COLINA_MIN_X_TILE = 19
	COLINA_MAX_X_TILE = 35
	COLINA_MIN_Y_TILE = 17
	COLINA_MAX_Y_TILE = 35

	// Límites de la colina en píxeles
	COLINA_MIN_X = COLINA_MIN_X_TILE * TILE_SIZE
	COLINA_MAX_X = COLINA_MAX_X_TILE*TILE_SIZE - TILE_SIZE
	COLINA_MIN_Y = COLINA_MIN_Y_TILE * TILE_SIZE
	COLINA_MAX_Y = COLINA_MAX_Y_TILE*TILE_SIZE - TILE_SIZE

	INITIAL_TRASH_COUNT = 10 // <--- Cambia este valor para la cantidad de basura inicial
)

// IP del servidor (modificable)
var serverIP = "192.168.0.127"

type TrashState struct {
	ID    string
	X     int32
	Y     int32
	Type  string
	Image string // Nuevo: nombre de la imagen
}

// server representa el servidor del juego.
// Implementa la interfaz GameServiceServer generada desde el .proto.
// players es un mapa en memoria que guarda los jugadores conectados por su ID.

type playerConn struct {
	id                string
	stream            pb.GameService_ConnectServer
	actions           chan *pb.PlayerAction
	position          *pb.PlayerState
	carryingTrashID   string
	carryingTrashType string
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
	trash         map[string]*TrashState // Nuevo: mapa de basura activa
	scores        map[string]int32       // Nuevo: puntaje por jugador
}

func newServer() *server {
	s := &server{
		players: make(map[string]*playerConn),
		trash:   make(map[string]*TrashState), // Inicializa el mapa de basura
		scores:  make(map[string]int32),       // Inicializa el mapa de puntajes
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
	// Si no hay jugadores, este es el primero y define totalPlayers
	if len(s.players) == 0 {
		if firstMsg.TotalPlayers == nil || *firstMsg.TotalPlayers <= 0 {
			s.mu.Unlock()
			return fmt.Errorf("el primer jugador debe definir totalPlayers > 0")
		}
		s.totalPlayers = *firstMsg.TotalPlayers
		fmt.Printf("Total de jugadores establecidos: %d\n", s.totalPlayers)
	} else {
		// No es el primero, validar que totalPlayers coincida o sea cero (indica que no quiere cambiar)
		requestedTotal := int32(0)
		if firstMsg.TotalPlayers != nil {
			requestedTotal = *firstMsg.TotalPlayers
		}
		// Si la sala ya está llena, rechazar cualquier conexión nueva
		if int32(len(s.players)) >= s.totalPlayers {
			s.mu.Unlock()
			return fmt.Errorf("la sala ya está llena (%d jugadores), espera a que termine la partida", s.totalPlayers)
		}
		// Si intenta crear una nueva sala cuando ya hay una creada, rechazar
		if requestedTotal != 0 && requestedTotal != s.totalPlayers {
			s.mu.Unlock()
			return fmt.Errorf("no hay salas disponibles para %d jugadores, intente con %d", requestedTotal, s.totalPlayers)
		}
	}

	player := &playerConn{
		id:       playerID,
		stream:   stream,
		actions:  make(chan *pb.PlayerAction, 10),
		position: &pb.PlayerState{PlayerId: playerID, X: 22 * TILE_SIZE, Y: 17 * TILE_SIZE},
	}
	s.players[playerID] = player

	// Inicializa la basura solo una vez al inicio de la partida
	if len(s.players) == 1 && len(s.trash) == 0 {
		// Crea INITIAL_TRASH_COUNT basuras aleatorias
		trashTypes := []string{"recycle", "garbage", "compost"}
		trashImages := map[string][]string{
			"recycle": {"botella.png", "lata.png", "vidrio.png", "marcadores.png"},
			"garbage": {"caja-pizza.png", "curita.png", "hueso.png", "utensilios.png"},
			"compost": {"manzana.png", "cascara.png", "huevo.png", "carton.png"},
		}
		// Calcula los rangos válidos para x e y en tiles
		xTileMin := COLINA_MIN_X_TILE + 1
		xTileMax := COLINA_MAX_X_TILE
		yTileMin := COLINA_MIN_Y_TILE + 3
		yTileMax := COLINA_MAX_Y_TILE
		for i := 0; i < INITIAL_TRASH_COUNT; i++ {
			typ := trashTypes[rand.Intn(len(trashTypes))]
			imgs := trashImages[typ]
			img := imgs[rand.Intn(len(imgs))]
			xTile := int32(xTileMin + rand.Intn(int(xTileMax-xTileMin+1))) // Incluye ambos extremos
			yTile := int32(yTileMin + rand.Intn(int(yTileMax-yTileMin+1)))
			x := xTile * TILE_SIZE
			y := yTile * TILE_SIZE
			id := fmt.Sprintf("trash_%d", i)
			s.trash[id] = &TrashState{
				ID:    id,
				X:     x,
				Y:     y,
				Type:  typ,
				Image: img,
			}
			fmt.Printf("[TRASH] Creada basura %s tipo %s imagen %s en (%d,%d)\n", id, typ, img, x, y)
		}
	}

	s.cond.Broadcast()
	s.mu.Unlock()

	// Goroutine que escucha las acciones del jugador
	go func() {
		for {
			action, err := stream.Recv()
			if err == io.EOF || err != nil {
				fmt.Printf("Jugador %s desconectado.\n", playerID)
				// Eliminar jugador desconectado
				s.mu.Lock()
				delete(s.players, playerID)
				// Si ya no quedan jugadores, resetea el estado del juego
				if len(s.players) == 0 {
					fmt.Println("Todos los jugadores se han desconectado. Reiniciando estado del juego.")
					s.totalPlayers = 0
					s.gameStarted = false
					s.tick = 0
					s.gameStartOnce = sync.Once{}
					s.trash = make(map[string]*TrashState) // Reinicia la basura
					s.scores = make(map[string]int32)      // Reinicia los puntajes
				}
				s.mu.Unlock()
				s.cond.Broadcast()
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
			s.mu.Unlock()
			// Enviar actualización del estado antes de esperar para que el cliente vea progreso
			err := stream.Send(&pb.GameState{
				Tick:        s.tick,
				Players:     s.getPlayersState(),
				GameStarted: false,
			})
			if err != nil {
				return err
			}
			s.mu.Lock()
			s.cond.Wait()
		}
	}
	s.mu.Unlock()

	// Juego iniciado, enviar estados periódicos
	for {
		state := s.buildGameState()
		if err := stream.Send(state); err != nil {
			return err
		}
		time.Sleep(16 * time.Millisecond)
	}
}

func (s *server) getPlayersState() []*pb.PlayerState {
	players := make([]*pb.PlayerState, 0, len(s.players))
	for _, p := range s.players {
		players = append(players, p.position)
	}
	return players
}

func (s *server) gameLoop() {
	ticker := time.NewTicker(16 * time.Millisecond)
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

func clamp(val, min, max int32) int32 {
	if val < min {
		return min
	}
	if val > max {
		return max
	}
	return val
}

func (s *server) applyAction(p *playerConn, action *pb.PlayerAction) {
	fmt.Printf("[DEBUG] Acción recibida de %s: %+v\n", p.id, action) // <-- LOG de toda acción recibida
	if action.PickupTrashId != nil {
		fmt.Printf("[DEBUG] PickupTrashId recibido: %v\n", *action.PickupTrashId)
	}
	if action.DepositTrashId != nil {
		fmt.Printf("[DEBUG] DepositTrashId recibido: %v\n", *action.DepositTrashId)
	}
	if action.DepositBinType != nil {
		fmt.Printf("[DEBUG] DepositBinType recibido: %v\n", *action.DepositBinType)
	}
	switch action.Action {
	case pb.ActionType_MOVE:
		switch action.Direction {
		case pb.Direction_UP:
			p.position.Y += TILE_SIZE
		case pb.Direction_DOWN:
			p.position.Y -= TILE_SIZE
		case pb.Direction_LEFT:
			p.position.X -= TILE_SIZE
		case pb.Direction_RIGHT:
			p.position.X += TILE_SIZE
		}
	case pb.ActionType_JUMP:
		p.position.Y += 2 * TILE_SIZE
	case pb.ActionType_ATTACK:
		fmt.Printf("%s atacó hacia %v\n", p.id, action.Direction)
	}

	// Recoger basura
	if action.PickupTrashId != nil && *action.PickupTrashId != "" {
		trashID := *action.PickupTrashId
		fmt.Printf("[DEBUG] PickupTrashId recibido: %s\n", trashID) // <-- LOG del id recibido
		if trash, ok := s.trash[trashID]; ok {
			delete(s.trash, trashID)
			p.carryingTrashID = trashID
			p.carryingTrashType = trash.Type
			fmt.Printf("[TRASH] Jugador %s recogió basura %s tipo %s\n", p.id, trashID, trash.Type)
		}
	}

	// Depositar basura
	if action.DepositTrashId != nil && *action.DepositTrashId != "" && action.DepositBinType != nil && *action.DepositBinType != "" {
		trashID := *action.DepositTrashId
		binType := *action.DepositBinType
		fmt.Printf("[DEBUG] DepositTrashId recibido: %s, binType: %s\n", trashID, binType)
		// Permite depositar si el jugador está cargando esa basura y el tipo coincide
		if p.carryingTrashID == trashID && p.carryingTrashType == binType {
			// Suma el puntaje ANTES de limpiar el estado
			s.scores[p.id] += 100
			fmt.Printf("[TRASH] Jugador %s depositó basura %s en bin %s (+100 puntos, total=%d)\n", p.id, trashID, binType, s.scores[p.id])
			p.carryingTrashID = ""
			p.carryingTrashType = ""
		} else {
			fmt.Printf("[TRASH] Jugador %s intentó depositar basura %s en bin %s, pero no la está cargando o el tipo no coincide\n", p.id, trashID, binType)
		}
	}

	// Limita la posición para que no salga de la colina
	p.position.X = clamp(p.position.X, COLINA_MIN_X, COLINA_MAX_X)
	p.position.Y = clamp(p.position.Y, COLINA_MIN_Y, COLINA_MAX_Y)
}

func (s *server) buildGameState() *pb.GameState {
	players := make([]*pb.PlayerState, 0, len(s.players))
	anyCarrying := false
	for _, p := range s.players {
		players = append(players, p.position)
		if p.carryingTrashID != "" {
			anyCarrying = true
		}
	}
	trashList := make([]*pb.TrashState, 0, len(s.trash))
	for _, t := range s.trash {
		trashList = append(trashList, &pb.TrashState{
			Id:    t.ID,
			X:     t.X,
			Y:     t.Y,
			Type:  t.Type,
			Image: t.Image,
		})
	}
	scores := make(map[string]int32)
	for pid, score := range s.scores {
		scores[pid] = score
	}

	gameFinished := false
	// Si no hay basura y nadie está cargando, pero algún jugador acaba de depositar la última basura,
	// asegúrate de sumar el puntaje antes de terminar el juego.
	if len(s.trash) == 0 && !anyCarrying && s.gameStarted {
		gameFinished = true
	}

	return &pb.GameState{
		Tick:         s.tick,
		Players:      players,
		GameStarted:  true,
		Trash:        trashList,
		Scores:       scores,
		GameFinished: gameFinished,
	}
}

func main() {
	rand.Seed(time.Now().UnixNano()) // Inicializa el generador de números aleatorios

	addr := fmt.Sprintf("%s:50051", serverIP)
	lis, err := net.Listen("tcp", addr) // Usa la IP definida arriba
	if err != nil {
		log.Fatalf("Fallo al escuchar: %v", err)
	}

	grpcServer := grpc.NewServer()
	pb.RegisterGameServiceServer(grpcServer, newServer())

	fmt.Printf("Servidor escuchando en %s...\n", addr)
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("Error en el servidor: %v", err)
	}
}

func abs(x int32) int32 {
	if x < 0 {
		return -x
	}
	return x
}
