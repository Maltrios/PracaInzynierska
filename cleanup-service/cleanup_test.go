package main

import (
	"database/sql"
	"fmt"
	"github.com/joho/godotenv"
	_ "github.com/lib/pq"
	"os"
	"path/filepath"
	"testing"
)

func setupTempTable(t *testing.T, tableName string, createSQL string) *sql.DB {
	err := godotenv.Load()

	db, err := sql.Open("postgres", os.Getenv("DBTest"))
	if err != nil {
		t.Fatal(err)
	}

	_, _ = db.Exec(fmt.Sprintf("CREATE TEMP TABLE IF NOT EXISTS %s (%s)", tableName, createSQL))
	_, _ = db.Exec(fmt.Sprintf("TRUNCATE %s", tableName))

	t.Cleanup(func() {
		err := db.Close()
		if err != nil {
			t.Errorf("Problem with closing the database")
		}
	})

	return db
}

func TestCleanExpiredTokens(t *testing.T) {
	db := setupTempTable(t, "blacklisted_tokens", "id SERIAL PRIMARY KEY, expires_at TIMESTAMP")

	_, _ = db.Exec("INSERT INTO blacklisted_tokens (expires_at) VALUES (NOW() - INTERVAL '1 day')")
	_, _ = db.Exec("INSERT INTO blacklisted_tokens (expires_at) VALUES (NOW() + INTERVAL '1 day')")

	err := CleanExpiredTokens(db, "blacklisted_tokens", false)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	row := db.QueryRow("SELECT COUNT(*) FROM blacklisted_tokens")
	var count int
	err = row.Scan(&count)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if count != 1 {
		t.Errorf("expected 1 row remaining, got %d", count)
	}
}

func TestCleanInactiveUsers(t *testing.T) {
	db := setupTempTable(t, "users", "id SERIAL PRIMARY KEY, last_login TIMESTAMP")

	_, _ = db.Exec("INSERT INTO users (last_login) VALUES (NOW() - INTERVAL '6 Months')")
	_, _ = db.Exec("INSERT INTO users (last_login) VALUES (NOW() + INTERVAL '5 day')")

	err := CleanInactiveUsers(db)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	row := db.QueryRow("SELECT COUNT(*) FROM users")
	var count int
	err = row.Scan(&count)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if count != 1 {
		t.Errorf("expected 1 row remaining, got %d", count)
	}
}

func TestCleanExpiredFile(t *testing.T) {
	db := setupTempTable(t, "user_files", "id SERIAL PRIMARY KEY,storage_path TEXT,  expires_at TIMESTAMP, user_id INTEGER")
	tempDir := t.TempDir()
	err := os.Setenv("StorageDirectory", tempDir)
	if err != nil {
		t.Errorf("error setting StorageDirectory: %v", err)
	}

	subDir := filepath.Join(tempDir, "tempFolder")
	err = os.Mkdir(subDir, 0755)
	if err != nil {
		t.Fatalf("error creating tempFolder: %v", err)
	}

	expiredFile := filepath.Join(subDir, "expired.txt")
	futureFile := filepath.Join(subDir, "future.txt")
	err = os.WriteFile(expiredFile, []byte("expired"), 0644)
	if err != nil {
		t.Errorf("error writing expired file: %v", err)
	}
	err = os.WriteFile(futureFile, []byte("future"), 0644)
	if err != nil {
		t.Errorf("error writing future file: %v", err)
	}

	_, _ = db.Exec("INSERT INTO user_files (expires_at, storage_path, user_id) VALUES (NOW() - INTERVAL '1 day', $1, $2)", "tempFolder/expired.txt", 123)
	_, _ = db.Exec("INSERT INTO user_files (expires_at, storage_path, user_id) VALUES (NOW() + INTERVAL '5 day', $1, $2)", "tempFolder/future.txt", 123)

	err = CleanExpiredFile(db)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	row := db.QueryRow("SELECT COUNT(*) FROM user_files")
	var count int
	err = row.Scan(&count)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if count != 1 {
		t.Errorf("expected 1 row remaining, got %d", count)
	}
	_, _ = db.Exec("UPDATE user_files SET expires_at = NOW() - INTERVAL '1 day' "+
		"WHERE storage_path = $1", "tempFolder/future.txt")
	err = CleanExpiredFile(db)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	row = db.QueryRow("SELECT COUNT(*) FROM user_files")
	err = row.Scan(&count)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if count != 0 {
		t.Errorf("expected 0 row remaining, got %d", count)
	}
	if _, err := os.Stat(subDir); !os.IsNotExist(err) {
		t.Errorf("expected empty directory to be deleted")
	}
}

func TestRunCleanup(t *testing.T) {
	db, err := sql.Open("postgres", os.Getenv("DBTest"))
	if err != nil {
		t.Fatal(err)
	}
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			t.Errorf("problem with closing the database")
		}
	}(db)

	_, _ = db.Exec("CREATE TEMP TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, last_login TIMESTAMP)")
	_, _ = db.Exec("CREATE TEMP TABLE IF NOT EXISTS user_files (id SERIAL PRIMARY KEY, storage_path TEXT, expires_at TIMESTAMP, user_id INTEGER)")
	_, _ = db.Exec("CREATE TEMP TABLE IF NOT EXISTS blacklist_tokens (id SERIAL PRIMARY KEY, expires_at TIMESTAMP)")
	_, _ = db.Exec("CREATE TEMP TABLE IF NOT EXISTS refresh_tokens (id SERIAL PRIMARY KEY, expires_at TIMESTAMP, user_id INTEGER)")
	_, _ = db.Exec("CREATE TEMP TABLE IF NOT EXISTS temp_files (id SERIAL PRIMARY KEY, created_at timestamptz, user_id INTEGER)")

	_, _ = db.Exec("TRUNCATE users, user_files, blacklist_tokens, refresh_tokens, temp_files")

	tempDir := t.TempDir()
	err = os.Setenv("StorageDirectory", tempDir)
	if err != nil {
		t.Errorf("error setting StorageDirectory: %v", err)
	}

	expiredFile := filepath.Join(tempDir, "expired.txt")
	err = os.WriteFile(expiredFile, []byte("expired"), 0644)
	if err != nil {
		t.Errorf("error writing expired file: %v", err)
	}
	futureFile := filepath.Join(tempDir, "future.txt")
	err = os.WriteFile(futureFile, []byte("future"), 0644)
	if err != nil {
		t.Errorf("error writing future file: %v", err)
	}

	_, _ = db.Exec("INSERT INTO users (last_login) VALUES (NOW() - INTERVAL '7 months')")
	_, _ = db.Exec("INSERT INTO users (last_login) VALUES (NOW())")
	_, _ = db.Exec("INSERT INTO user_files (expires_at, storage_path, user_id) VALUES (NOW() - INTERVAL '1 day', 'expired.txt', 123)")
	_, _ = db.Exec("INSERT INTO user_files (expires_at, storage_path, user_id) VALUES (NOW() + INTERVAL '1 day', 'future.txt', 123)")
	_, _ = db.Exec("INSERT INTO blacklist_tokens (expires_at) VALUES (NOW() - INTERVAL '1 day')")
	_, _ = db.Exec("INSERT INTO refresh_tokens (expires_at) VALUES (NOW() - INTERVAL '1 day')")
	_, _ = db.Exec("INSERT INTO temp_files (created_at, user_id) VALUES (NOW() - INTERVAL '1 hour', 123)")
	_, _ = db.Exec("INSERT INTO temp_files (created_at, user_id) VALUES (NOW(), 123)")

	err = os.Setenv("BLACKLIST_TOKEN_DB_TABLE", "blacklist_tokens")
	if err != nil {
		t.Errorf("error setting BLACKLIST_TOKEN_DB_TABLE: %v", err)
	}
	err = os.Setenv("REFRESH_TOKEN_DB_TABLE", "refresh_tokens")
	if err != nil {
		t.Errorf("error setting REFRESH_TOKEN_DB_TABLE: %v", err)
	}

	err = RunCleanup(db)
	if err != nil {
		t.Fatalf("unexpected error from RunCleanup: %v", err)
	}

	var userCount int
	row := db.QueryRow("SELECT COUNT(*) FROM users")
	err = row.Scan(&userCount)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if userCount != 1 {
		t.Errorf("expected 1 user remaining, got %d", userCount)
	}

	var fileCount int
	row = db.QueryRow("SELECT COUNT(*) FROM user_files")
	err = row.Scan(&fileCount)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if fileCount != 1 {
		t.Errorf("expected 1 file remaining, got %d", fileCount)
	}
	if _, err := os.Stat(futureFile); os.IsNotExist(err) {
		t.Errorf("expected file to exist")
	}
	if _, err := os.Stat(expiredFile); !os.IsNotExist(err) {
		t.Errorf("expected file to not exist")
	}

	var blacklistCount, refreshCount int
	_ = db.QueryRow("SELECT COUNT(*) FROM blacklist_tokens").Scan(&blacklistCount)
	_ = db.QueryRow("SELECT COUNT(*) FROM refresh_tokens").Scan(&refreshCount)
	if blacklistCount != 0 || refreshCount != 0 {
		t.Errorf("expected all tokens deleted, got blacklist: %d, refreshlist: %d", blacklistCount, refreshCount)
	}

	var tempFileCount int
	row = db.QueryRow("SELECT COUNT(*) FROM temp_files")
	err = row.Scan(&tempFileCount)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if tempFileCount != 1 {
		t.Errorf("expected 1 files, got %d", tempFileCount)
	}
}

func TestIsEmpty(t *testing.T) {
	dir := t.TempDir()

	empty, err := IsEmpty(dir)
	if err != nil {
		t.Fatal(err)
	}
	if !empty {
		t.Errorf("expected empty dir, got not empty")
	}

	file := filepath.Join(dir, "file.txt")
	err = os.WriteFile(file, []byte("content"), 0644)
	if err != nil {
		t.Errorf("error writing file: %v", err)
	}
	empty, err = IsEmpty(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if empty {
		t.Errorf("expected non-empty dir, got empty")
	}
}

func TestCleanExpiredFile_MissingFile(t *testing.T) {
	db := setupTempTable(t, "user_files", "id SERIAL PRIMARY KEY, storage_path TEXT, expires_at TIMESTAMP, user_id INTEGER")
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			t.Errorf("error closing db: %v", err)
		}
	}(db)
	tempDir := t.TempDir()
	err := os.Setenv("StorageDirectory", tempDir)
	if err != nil {
		t.Errorf("error setting StorageDirectory: %v", err)
	}
	_, _ = db.Exec("INSERT INTO user_files (expires_at, storage_path) VALUES (NOW() - INTERVAL '1 day', 'missing.txt')")

	err = CleanExpiredFile(db)
	if err == nil {
		t.Errorf("expected error when remove non existed file, got nil")
	}
}

func TestCleanTempFiles(t *testing.T) {
	db := setupTempTable(t, "temp_files", "id SERIAL PRIMARY KEY, created_at TIMESTAMP,  user_id INT")
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			t.Errorf("error closing db: %v", err)
		}
	}(db)
	_, _ = db.Exec("INSERT INTO temp_files (created_at, user_id) VALUES (NOW() - INTERVAL '1 hour', NULL)")
	_, _ = db.Exec("INSERT INTO temp_files (created_at, user_id) VALUES (NOW(), 123)")

	err := CleanTempFiles(db)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var fileCount int
	row := db.QueryRow("SELECT COUNT(*) FROM temp_files")
	err = row.Scan(&fileCount)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if fileCount != 1 {
		t.Errorf("expected 1 files, got %d", fileCount)
	}
}
