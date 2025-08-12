package main

import (
	"fmt"
	"github.com/joho/godotenv"
	"log"
	"os"
)

func main() {
	err := godotenv.Load()
	if err != nil {
		log.Fatal("Error loading .env file")
	}
	config := LoadConfig()
	if err := RunCleanup(config); err != nil {
		fmt.Println("Cleanup failed", err)
		os.Exit(1)
	}

}
