package taskcmd

import (
	"context"
	"fmt"
	"io"

	"example.com/go-cli/internal/cli"
	"example.com/go-cli/internal/domain/task"
)

// completeOptions は task complete の引数とフラグを保持する。
type completeOptions struct {
	id string
}

// completeOutput は task complete の実行結果を表す。
type completeOutput struct {
	Task taskView `json:"task"`
}

// newComplete は task complete コマンドを返す。
func newComplete(svc *task.Service) *cli.Command {
	var opts completeOptions
	return &cli.Command{
		Name:    "complete",
		Summary: "Mark a task as done",
		Args:    []cli.Arg{{Name: "id", Value: &opts.id}},
		Run: func(ctx context.Context) (cli.Output, error) {
			return runComplete(ctx, svc, opts)
		},
	}
}

// runComplete は task complete を実行する。
func runComplete(ctx context.Context, svc *task.Service, opts completeOptions) (completeOutput, error) {
	id, err := task.ParseID(opts.id)
	if err != nil {
		return completeOutput{}, err
	}
	completed, err := svc.Complete(ctx, id)
	if err != nil {
		return completeOutput{}, err
	}
	return completeOutput{Task: toTaskView(completed)}, nil
}

// WriteText は cli.Output を実装する。
func (o completeOutput) WriteText(w io.Writer) error {
	_, err := fmt.Fprintf(w, "Completed task %d: %s\n", o.Task.ID, o.Task.Title)
	return err
}
