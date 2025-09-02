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
