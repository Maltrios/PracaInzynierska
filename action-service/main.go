package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"github.com/gorilla/mux"
	"github.com/joho/godotenv"
	_ "github.com/lib/pq"
	"github.com/robfig/cron/v3"
	"log"
	"net/http"
	"os"
	"strconv"
)

type ActionRequest struct {
	UserId     int    `json:"user_id"`
	ActionType string `json:"action_type"`
}

var db *sql.DB
var actionLimit int

func main() {
	err := godotenv.Load(".env")
	if err != nil {
		log.Fatal("Error loading .env file")
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8081"
	}

	conn, err := sql.Open("postgres", os.Getenv("DBConnectionString"))
	if err != nil {
		log.Fatal(err)
	}
	db = conn
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			log.Fatal(err)
		}
	}(db)

	myCron := cron.New()
	_, err = myCron.AddFunc("5 * * * *", func() {
		reset(db)
	})
	if err != nil {
		return
	}
	myCron.Start()

	r := mux.NewRouter()
	r.HandleFunc("/action", func(w http.ResponseWriter, r *http.Request) {
		handleAction(db, w, r)
	}).Methods("POST")
	fmt.Println("Listening on port 8081")
	err = http.ListenAndServe(":8081", r)
	if err != nil {
		return
	}
}

func handleAction(db *sql.DB, writer http.ResponseWriter, request *http.Request) {
	var actionRequest ActionRequest

	err := json.NewDecoder(request.Body).Decode(&actionRequest)
	if err != nil {
		http.Error(writer, err.Error(), http.StatusBadRequest)
		return
	}
	var isActive bool
	err = db.QueryRow("SELECT is_active FROM users WHERE id = $1", actionRequest.UserId).Scan(&isActive)
	if err != nil {
		http.Error(writer, err.Error(), http.StatusNotFound)
		return
	}
	if !isActive {
		http.Error(writer, "Uses is blocked for today. Please back tomorrow", http.StatusForbidden)
		return
	}
	var actionCount int
	err = db.QueryRow("SELECT count(*) FROM user_actions WHERE user_id = $1 ",
		actionRequest.UserId).Scan(&actionCount)
	if err != nil {
		http.Error(writer, "Error getting user action count.", http.StatusInternalServerError)
		return
	}
	userLimit := os.Getenv("ACTION_LIMIT")
	if userLimit == "" {
		actionLimit = 5
	} else {
		actionLimit, err = strconv.Atoi(userLimit)
		if err != nil {
			log.Fatal("Error converting ACTION_LIMIT to int")
		}
	}
	if actionCount >= actionLimit {
		_, err := db.Exec("UPDATE users SET is_active = $1 WHERE id = $2", false, actionRequest.UserId)
		if err != nil {
			http.Error(writer, "Error updating user status", http.StatusInternalServerError)
			return
		}
		http.Error(writer, "Action limit reached", http.StatusTooManyRequests)
		return
	}

	_, err = db.Exec("INSERT INTO user_actions (user_id, action_type) VALUES ($1, $2)",
		actionRequest.UserId, actionRequest.ActionType)
	if err != nil {
		http.Error(writer, "Error updating user_actions table status", http.StatusInternalServerError)
		return
	}
	writer.WriteHeader(http.StatusCreated)
	_, err = writer.Write([]byte("OK"))
	if err != nil {
		http.Error(writer, "Error writing response", http.StatusInternalServerError)
	}
}

func reset(db *sql.DB) {
	_, err := db.Exec("DELETE FROM user_actions")
	if err != nil {
		log.Println(err)
		return
	}
	_, err = db.Exec("UPDATE users SET is_active = true")
	if err != nil {
		log.Println(err)
		return
	}
	fmt.Println("Reset Completed")
}
