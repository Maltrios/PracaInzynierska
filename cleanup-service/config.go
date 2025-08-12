package main

import (
	"os"
)

type Config struct {
	DBConnectionString string
	StorageDirectory   string
}

func LoadConfig() Config {
	return Config{
		DBConnectionString: os.Getenv("DBConnectionString"),
		StorageDirectory:   os.Getenv("StorageDirectory"),
	}
}

func getEnv(key string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return "Environment variable " + key + " not set."
}
