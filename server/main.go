package main

import (
	"arcade_racing/server/protos"
	"fmt"
)

func main() {
	message := protos.Hello("Karim")
	fmt.Println(message)
}
