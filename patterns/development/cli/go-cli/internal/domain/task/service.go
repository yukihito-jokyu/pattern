package task

import (
	"context"
	"fmt"
	"slices"
	"strings"
	"time"

	"example.com/go-cli/internal/errkind"
)

// Service は task のユースケースを実行する。
type Service struct {
	repo Repository
	now  func() time.Time
}

// NewService は repo にタスクを保存し、now から現在時刻を得る Service を返す。
func NewService(repo Repository, now func() time.Time) *Service {
	return &Service{repo: repo, now: now}
}

// Add は指定したタイトルの未完了タスクを作る。
func (s *Service) Add(ctx context.Context, title string) (Task, error) {
	trimmed := strings.TrimSpace(title)
	err := validateTitle(trimmed)
	if err != nil {
		return Task{}, err
	}
	tasks, err := s.repo.Load(ctx)
	if err != nil {
		return Task{}, err
	}
	created := Task{ID: nextID(tasks), Title: trimmed, CreatedAt: s.now().UTC().Truncate(time.Second)}
	err = s.repo.Save(ctx, append(tasks, created))
	if err != nil {
		return Task{}, err
	}
	return created, nil
}

// Complete は指定した ID のタスクを完了にする。
// 完了済みのタスクを指定しても状態は変わらない。
func (s *Service) Complete(ctx context.Context, id int) (Task, error) {
	tasks, err := s.repo.Load(ctx)
	if err != nil {
		return Task{}, err
	}
	i, err := indexOf(tasks, id)
	if err != nil {
		return Task{}, err
	}
	tasks[i].Done = true
	err = s.repo.Save(ctx, tasks)
	if err != nil {
		return Task{}, err
	}
	return tasks[i], nil
}

// List は filter に一致するタスクを ID 順で返す。
func (s *Service) List(ctx context.Context, filter Filter) ([]Task, error) {
	tasks, err := s.repo.Load(ctx)
	if err != nil {
		return nil, err
	}
	matched := make([]Task, 0, len(tasks))
	for _, t := range tasks {
		if t.Done && !filter.IncludeDone {
			continue
		}
		matched = append(matched, t)
	}
	return matched, nil
}

// indexOf は tasks 内で指定した ID の task の位置を返す。
func indexOf(tasks []Task, id int) (int, error) {
	i := slices.IndexFunc(tasks, func(t Task) bool { return t.ID == id })
	if i < 0 {
		return 0, fmt.Errorf("%w: task %d", errkind.ErrNotFound, id)
	}
	return i, nil
}

// nextID は tasks 内の最大 ID に1を足した新しい task の ID を返す。
func nextID(tasks []Task) int {
	maxID := 0
	for _, t := range tasks {
		maxID = max(maxID, t.ID)
	}
	return maxID + 1
}
