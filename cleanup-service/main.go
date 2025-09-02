package main

import (
	"database/sql"
	"github.com/joho/godotenv"
	"github.com/robfig/cron/v3"
	"log"
)

func main() {
	err := godotenv.Load()
	if err != nil {
		log.Fatal("Error loading .env file")
	}
	config := LoadConfig()

	c := cron.New(cron.WithSeconds())
	_, err = c.AddFunc("* * * * * *", func() {
		db, err := sql.Open("postgres", config.DBConnectionString)
		if err != nil {
			log.Fatal(err)
		}
		defer func(db *sql.DB) {
			err := db.Close()
			if err != nil {
				log.Fatal(err)
			}
		}(db)

		if err := RunCleanup(db); err != nil {
			log.Println("Cleanup error:", err)
		}
	})
	if err != nil {
		return
	}
	c.Start()

	select {}
}
