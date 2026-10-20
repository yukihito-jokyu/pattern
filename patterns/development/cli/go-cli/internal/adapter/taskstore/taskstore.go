// Package taskstore はタスクを JSON ファイルに保存する。
package taskstore

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"time"

	"example.com/go-cli/internal/domain/task"
)

// Store は1つの JSON ファイルを使う task.Repository の実装である。
type Store struct {
	path string
}

// document はデータファイルの内容を表す。
type document struct {
	Version int      `json:"version"`
	Tasks   []record `json:"tasks"`
}

// record はデータファイルに保存する1件の task を表す。
type record struct {
	ID        int       `json:"id"`
	Title     string    `json:"title"`
	Done      bool      `json:"done"`
	CreatedAt time.Time `json:"created_at"`
}

// データファイルの設定値を定義する。
const (
	formatVersion = 1
	dirPerm       = 0o700
)

// New は path の JSON ファイルを読み書きする Store を返す。
func New(path string) *Store {
	return &Store{path: path}
}

// Load は task.Repository を実装する。
// ファイルが無い場合はタスクが無いものとする。
func (s *Store) Load(ctx context.Context) ([]task.Task, error) {
	err := ctx.Err()
	if err != nil {
		return nil, fmt.Errorf("load tasks: %w", err)
	}
	data, err := os.ReadFile(s.path)
	if errors.Is(err, fs.ErrNotExist) {
		return make([]task.Task, 0), nil
	}
	if err != nil {
		return nil, fmt.Errorf("load tasks: %w", err)
	}
	var doc document
	err = json.Unmarshal(data, &doc)
	if err != nil {
		return nil, fmt.Errorf("load tasks from %s: %w", s.path, err)
	}
	tasks := make([]task.Task, 0, len(doc.Tasks))
	for _, r := range doc.Tasks {
		tasks = append(tasks, toTask(r))
	}
	return tasks, nil
}

// Save は task.Repository を実装する。
// ファイルを不可分な操作で置き換える。
func (s *Store) Save(ctx context.Context, tasks []task.Task) error {
	err := ctx.Err()
	if err != nil {
		return fmt.Errorf("save tasks: %w", err)
	}
	doc := document{Version: formatVersion, Tasks: make([]record, 0, len(tasks))}
	for _, t := range tasks {
		doc.Tasks = append(doc.Tasks, toRecord(t))
	}
	data, err := json.MarshalIndent(doc, "", "  ")
	if err != nil {
		return fmt.Errorf("save tasks: %w", err)
	}
	err = writeFileAtomic(s.path, append(data, '\n'))
	if err != nil {
		return fmt.Errorf("save tasks: %w", err)
	}
	return nil
}

// toRecord は Task を record に変換する。
func toRecord(t task.Task) record {
	return record{ID: t.ID, Title: t.Title, Done: t.Done, CreatedAt: t.CreatedAt}
}

// toTask は record を Task に変換する。
func toTask(r record) task.Task {
	return task.Task{ID: r.ID, Title: r.Title, Done: r.Done, CreatedAt: r.CreatedAt}
}

// writeFileAtomic は同じディレクトリの一時ファイルに data を書いてから path に改名し、異常終了で書きかけのファイルが残ることを防ぐ。
func writeFileAtomic(path string, data []byte) error {
	dir := filepath.Dir(path)
	err := os.MkdirAll(dir, dirPerm)
	if err != nil {
		return fmt.Errorf("create %s: %w", dir, err)
	}
	tmp, err := os.CreateTemp(dir, ".tmp-*")
	if err != nil {
		return fmt.Errorf("create temporary file: %w", err)
	}
	_, err = tmp.Write(data)
	err = errors.Join(err, tmp.Close())
	if err != nil {
		return errors.Join(fmt.Errorf("write %s: %w", tmp.Name(), err), os.Remove(tmp.Name()))
	}
	err = os.Rename(tmp.Name(), path)
	if err != nil {
		return errors.Join(fmt.Errorf("rename to %s: %w", path, err), os.Remove(tmp.Name()))
	}
	return nil
}
