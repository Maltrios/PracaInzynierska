package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"github.com/joho/godotenv"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

type Payload struct {
	UserID     int    `json:"user_id"`
	ActionType string `json:"action_type"`
}

func setupTestDB(t *testing.T) *sql.DB {
	t.Helper()
	err := godotenv.Load()

	db, err := sql.Open("postgres", os.Getenv("DBTest"))
	if err != nil {
		t.Fatal(err)
	}

	_, _ = db.Exec("DROP TABLE IF EXISTS user_actions CASCADE")
	_, _ = db.Exec("DROP TABLE IF EXISTS users CASCADE")
	_, _ = db.Exec("CREATE TEMP TABLE users (id SERIAL PRIMARY KEY, is_active BOOLEAN)")
	_, _ = db.Exec("CREATE TEMP TABLE user_actions (id SERIAL PRIMARY KEY, user_id INT, action_type TEXT)")

	_, _ = db.Exec("TRUNCATE users")
	_, _ = db.Exec("TRUNCATE user_actions")

	return db
}

func TestAddUserAction(t *testing.T) {
	db := setupTestDB(t)
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			t.Fatal("error closing db", err)
		}
	}(db)
	_, _ = db.Exec("INSERT INTO users (is_active) VALUES (true)")

	jsonBody := Payload{UserID: 1, ActionType: "test"}
	b, _ := json.Marshal(jsonBody)

	for i := 0; i < 6; i++ {
		req := httptest.NewRequest("POST", "/action", bytes.NewBuffer(b))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		handleAction(db, w, req)
		resp := w.Result()
		if i < 5 && resp.StatusCode != 201 {
			t.Errorf("expected 201 Created, got %d at iteration %d", resp.StatusCode, i)
		}
		if i == 5 && resp.StatusCode != 429 {
			t.Errorf("expected 429 Too Many Requests, got %d at iteration %d", resp.StatusCode, i)
		}
	}
	var count int
	err := db.QueryRow("SELECT COUNT(*) FROM user_actions").Scan(&count)
	if err != nil {
		t.Fatal(err)
	}
	if count != 5 {
		t.Errorf("expected 5 actions in user_actions, got %d", count)
	}

	var isActive bool
	err = db.QueryRow("SELECT is_active FROM users WHERE id = 1").Scan(&isActive)
	if err != nil {
		t.Fatal(err)
	}
	if isActive {
		t.Errorf("expected user to be inactive after limit reached")
	}
}

func TestReset(t *testing.T) {
	db := setupTestDB(t)
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			t.Fatal("error closing db", err)
		}
	}(db)

	_, _ = db.Exec("INSERT INTO users (is_active) VALUES (true)")

	jsonBody := Payload{UserID: 1, ActionType: "test"}
	b, _ := json.Marshal(jsonBody)

	for i := 0; i < 6; i++ {
		req := httptest.NewRequest("POST", "/action", bytes.NewBuffer(b))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		handleAction(db, w, req)
	}
	var count int
	err := db.QueryRow("SELECT COUNT(*) FROM user_actions").Scan(&count)
	if err != nil {
		t.Fatal(err)
	}
	if count != 5 {
		t.Errorf("expected 5 actions in user_actions, got %d", count)
	}

	var isActive bool
	err = db.QueryRow("SELECT is_active FROM users WHERE id = 1").Scan(&isActive)
	if err != nil {
		t.Fatal(err)
	}
	if isActive {
		t.Errorf("expected user to be inactive after limit reached")
	}

	reset(db)

	err = db.QueryRow("SELECT COUNT(*) FROM user_actions").Scan(&count)
	if err != nil {
		t.Fatal(err)
	}
	if count != 0 {
		t.Errorf("expected 0 actions in user_actions, got %d", count)
	}

	err = db.QueryRow("SELECT is_active FROM users WHERE id = 1").Scan(&isActive)
	if err != nil {
		t.Fatal(err)
	}
	if !isActive {
		t.Errorf("expected user to be active after reset")
	}
}

func TestHandleActionUserNotFound(t *testing.T) {
	db := setupTestDB(t)
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			t.Fatal("error closing db", err)
		}
	}(db)

	jsonBody := Payload{UserID: 99, ActionType: "test"}
	b, _ := json.Marshal(jsonBody)
	req := httptest.NewRequest("POST", "/action", bytes.NewBuffer(b))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	handleAction(db, w, req)
	resp := w.Result()
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("expected 404, got %d", resp.StatusCode)
	}
}

func TestHandleAction_BlockedUser(t *testing.T) {
	db := setupTestDB(t)
	_, _ = db.Exec("INSERT INTO users (is_active) VALUES (false)")
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			t.Fatal("error closing db", err)
		}
	}(db)

	jsonBody := Payload{UserID: 1, ActionType: "test"}
	b, _ := json.Marshal(jsonBody)
	req := httptest.NewRequest("POST", "/action", bytes.NewBuffer(b))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	handleAction(db, w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusForbidden {
		t.Errorf("expected 403, got %d", resp.StatusCode)
	}
}
func TestBadJSON(t *testing.T) {
	db := setupTestDB(t)
	_, _ = db.Exec("INSERT INTO users (is_active) VALUES (true)")

	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			t.Fatal("error closing db", err)
		}
	}(db)
	req := httptest.NewRequest("POST", "/action", bytes.NewBuffer([]byte("{bad json}")))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	handleAction(db, w, req)
	resp := w.Result()
	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", resp.StatusCode)
	}
}
