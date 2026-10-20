package taskcmd

import (
	"context"
	"flag"
	"io"
	"strconv"

	"example.com/go-cli/internal/cli"
	"example.com/go-cli/internal/domain/task"
)

// listOptions は task list の引数とフラグを保持する。
type listOptions struct {
	all bool
}

// listOutput は task list の実行結果を表す。
type listOutput struct {
	Tasks []taskView `json:"tasks"`
}

// newList は task list コマンドを返す。
func newList(svc *task.Service) *cli.Command {
	var opts listOptions
	return &cli.Command{
		Name:    "list",
		Summary: "List open tasks",
		Flags: func(fs *flag.FlagSet) {
			fs.BoolVar(&opts.all, "all", false, "Include completed tasks")
		},
		Run: func(ctx context.Context) (cli.Output, error) {
			return runList(ctx, svc, opts)
		},
	}
}

// runList は task list を実行する。
func runList(ctx context.Context, svc *task.Service, opts listOptions) (listOutput, error) {
	tasks, err := svc.List(ctx, task.Filter{IncludeDone: opts.all})
	if err != nil {
		return listOutput{}, err
	}
	views := make([]taskView, 0, len(tasks))
	for _, t := range tasks {
		views = append(views, toTaskView(t))
	}
	return listOutput{Tasks: views}, nil
}

// WriteText は cli.Output を実装する。
func (o listOutput) WriteText(w io.Writer) error {
	rows := make([][]string, 0, len(o.Tasks))
	for _, v := range o.Tasks {
		rows = append(rows, []string{strconv.Itoa(v.ID), v.status(), v.Title})
	}
	return cli.WriteTable(w, []string{"ID", "STATUS", "TITLE"}, rows)
}
