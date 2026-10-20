package taskcmd

import (
	"time"

	"example.com/go-cli/internal/domain/task"
)

// taskView は task コマンドの出力で1件の task を表す。
type taskView struct {
	ID        int       `json:"id"`
	Title     string    `json:"title"`
	Done      bool      `json:"done"`
	CreatedAt time.Time `json:"created_at"`
}

// toTaskView は Task を taskView に変換する。
func toTaskView(t task.Task) taskView {
	return taskView{ID: t.ID, Title: t.Title, Done: t.Done, CreatedAt: t.CreatedAt}
}

// status は STATUS 列に表示する文字列を返す。
func (v taskView) status() string {
	if v.Done {
		return "done"
	}
	return "open"
}
