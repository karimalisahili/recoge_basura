# Recoge basura

## Servidor Go grcp

```bash
protoc --go_out=server --go-grpc_out=server proto/game.proto

```

### Correr el servidor 

Desde la raiz (arcade_racing) ejecutar.

```bash
go run server/server.go
```

### Dependencias

1. Cada vez que se agreguen dependencias externas nuevas se tiene que correr desde la raiz. 

```bash
go mod tidy
```

## Cliente Python

```bash
 python -m grpc_tools.protoc -I=proto --python_out=client/code --grpc_python_out=client/code proto/game.proto

```

### Correr el cliente 

#### Desde la raiz (arcade_racing) ejecutar.
```bash
python client/client.py
```

#### Desde la raiz (arcade_racing) ejecutar.
```bash
python client/code/main.py
```


### Dependencias

1. Para pasar nuevas dependencias

```bash
pip freeze > requirements.txt
```
2. Para instalar dependencias

```bash
cd client
```

```bash
pip install -r requirements.txt
```