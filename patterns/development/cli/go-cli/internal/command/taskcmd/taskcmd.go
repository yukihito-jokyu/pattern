// Package taskcmd は task コマンド群を実装する。
package taskcmd

import (
	"example.com/go-cli/internal/cli"
	"example.com/go-cli/internal/domain/task"
)

// New は svc でユースケースを実行する task コマンド群を返す。
func New(svc *task.Service) *cli.Group {
	return &cli.Group{
		Name:    "task",
		Summary: "Manage tasks",
		Commands: []*cli.Command{
			newAdd(svc),
			newComplete(svc),
			newList(svc),
		},
	}
}
