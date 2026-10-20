package task

import "context"

// Repository は全 task を一括で読み書きする。
type Repository interface {
	// Load は保存した全タスクを ID 順で返す。
	// 保存したタスクが無ければ空のスライスを返す。
	Load(ctx context.Context) ([]Task, error)
	// Save は保存した全タスクを tasks で置き換える。
	Save(ctx context.Context, tasks []Task) error
}
