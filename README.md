## Arcade Racing 

Servidor Go grcp

```bash
protoc --go_out=server --go-grpc_out=server proto/game.proto

```

## Correr el servidor 

```bash
go run server/server.go
```

Cliente Python

```bash
python -m grpc_tools.protoc -I=proto --python_out=client --grpc_python_out=client proto/game.proto

```