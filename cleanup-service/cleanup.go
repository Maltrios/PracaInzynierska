package main

import (
	"database/sql"
	"fmt"
	_ "github.com/lib/pq"
	"io"
	"os"
	"path/filepath"
	"strings"
)

func CleanExpiredTokens(db *sql.DB, table string, hasID bool) error {
	var query string

	if hasID {
		query = fmt.Sprintf("DELETE FROM %s WHERE expires_at < NOW() OR user_id is NULL", table)
	} else {
		query = fmt.Sprintf("DELETE FROM %s WHERE expires_at < NOW()", table)
	}

	result, err := db.Exec(query)
	if err != nil {
		return fmt.Errorf("error cleaning %s: %w", table, err)
	}
	rowsAffected, err := result.RowsAffected()
	fmt.Println("Removed expired tokens:", rowsAffected, "from", table)
	return nil
}

func CleanExpiredFile(db *sql.DB) error {
	tx, err := db.Begin()
	if err != nil {
		return err
	}

	rows, err := tx.Query("SELECT id, storage_path from user_files WHERE expires_at < NOW() OR user_id IS NULL")
	if err != nil {
		tx.Rollback()
		return err
	}
	defer rows.Close()
	var fileIDs []int
	var paths []string

	for rows.Next() {
		var id int
		var storagePath string
		if err := rows.Scan(&id, &storagePath); err != nil {
			tx.Rollback()
			return err
		}
		fileIDs = append(fileIDs, id)
		paths = append(paths, storagePath)
	}
	for i, relativePath := range paths {
		relativePath = strings.ReplaceAll(relativePath, `\`, `/`)
		path := filepath.Join(os.Getenv("StorageDirectory"), relativePath)

		if err := os.Remove(path); err != nil {
			tx.Rollback()
			return fmt.Errorf("error removing file %s: %w", path, err)
		}

		_, err := tx.Exec("DELETE FROM user_files WHERE id = $1", fileIDs[i])
		if err != nil {
			tx.Rollback()
			return err
		}

		dir := filepath.Dir(path)
		empty, err := IsEmpty(dir)
		if err != nil {
			fmt.Printf("Error checking if file is empty: %s\n", err)
		} else if empty {
			if err := os.Remove(dir); err != nil {
				fmt.Printf("Error removing empty directory %s: %s\n", dir, err)
			} else {
				fmt.Printf("Removed empty directory %s\n", dir)
			}
		}
	}
	fmt.Println("Removed file:", len(paths))

	return tx.Commit()
}

func CleanInactiveUsers(db *sql.DB) error {
	rows, err := db.Exec("DELETE FROM users WHERE last_login < NOW() - INTERVAL '6 month'")
	if err != nil {
		return err
	}
	user, _ := rows.RowsAffected()
	fmt.Println("Removed inactive users:", user)
	return nil
}

func CleanTempFiles(db *sql.DB) error {
	rows, err := db.Exec("DELETE FROM temp_files WHERE created_at < NOW() - INTERVAL '1 hour' OR user_id IS NULL")
	if err != nil {
		return err
	}
	deletedCount, _ := rows.RowsAffected()
	fmt.Println("Removed not used files from table: temp_files:", deletedCount)
	return nil
}

func RunCleanup(db *sql.DB) error {
	if err := CleanExpiredFile(db); err != nil {

		return fmt.Errorf("error cleaning up expired files: %v", err)
	}
	if err := CleanInactiveUsers(db); err != nil {
		return fmt.Errorf("error cleaning up inactive users: %v", err)
	}
	if err := CleanExpiredTokens(db, os.Getenv("BLACKLIST_TOKEN_DB_TABLE"), false); err != nil {
		return fmt.Errorf("error cleaning up expired tokens (blacklist): %v", err)
	}
	if err := CleanExpiredTokens(db, os.Getenv("REFRESH_TOKEN_DB_TABLE"), true); err != nil {
		return fmt.Errorf("error cleaning up expired tokens (refreshtoken): %v", err)
	}
	if err := CleanTempFiles(db); err != nil {
		return fmt.Errorf("error cleaning up temp files: %v", err)
	}
	fmt.Println("Cleaned complete")
	return nil
}

func IsEmpty(name string) (bool, error) {
	f, err := os.Open(name)
	if err != nil {
		return false, err
	}
	defer f.Close()

	_, err = f.Readdirnames(1)
	if err == io.EOF {
		return true, nil
	}
	return false, err
}
