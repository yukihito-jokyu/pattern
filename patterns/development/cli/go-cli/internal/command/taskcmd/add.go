package taskcmd

import (
	"context"
	"fmt"
	"io"

	"example.com/go-cli/internal/cli"
	"example.com/go-cli/internal/domain/task"
)

// addOptions は task add の引数とフラグを保持する。
type addOptions struct {
	title string
}

// addOutput は task add の実行結果を表す。
type addOutput struct {
	Task taskView `json:"task"`
}

// newAdd は task add コマンドを返す。
func newAdd(svc *task.Service) *cli.Command {
	var opts addOptions
	return &cli.Command{
		Name:    "add",
		Summary: "Add a task",
		Args:    []cli.Arg{{Name: "title", Value: &opts.title}},
		Run: func(ctx context.Context) (cli.Output, error) {
			return runAdd(ctx, svc, opts)
		},
	}
}

// runAdd は task add を実行する。
func runAdd(ctx context.Context, svc *task.Service, opts addOptions) (addOutput, error) {
	added, err := svc.Add(ctx, opts.title)
	if err != nil {
		return addOutput{}, err
	}
	return addOutput{Task: toTaskView(added)}, nil
}

// WriteText は cli.Output を実装する。
func (o addOutput) WriteText(w io.Writer) error {
	_, err := fmt.Fprintf(w, "Added task %d: %s\n", o.Task.ID, o.Task.Title)
	return err
}
