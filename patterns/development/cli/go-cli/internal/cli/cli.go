// Package cli は標準の flag パッケージで構築した2階層のコマンドを実行する。
//
// フラグと位置引数の解析・ヘルプ・--json・出力・エラーから終了コードへの変換を共通で担当する。
// 各コマンドは入力を宣言し、Output を返す。
package cli

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"

	"example.com/go-cli/internal/errkind"
)

// IO は App.Run の出力先を保持する。
type IO struct {
	// Out はコマンドの出力を受け取る。
	Out io.Writer
	// Err はエラーと使い方の案内を受け取る。
	Err io.Writer
}

// Output はコマンドの実行結果を表す。
// App.Run は --json 指定時は JSON、それ以外は文章で結果を書き出す。
type Output interface {
	// WriteText は人が読むための文章を書き出す。
	WriteText(w io.Writer) error
}

// Arg は必須の位置引数を表す。
// App.Run は Run を呼ぶ前に引数を Value に格納する。
type Arg struct {
	Name  string
	Value *string
}

// Command は task add のような末端のコマンドを表す。
type Command struct {
	// Name はコマンドを選ぶ動詞を表す。
	Name string
	// Summary はヘルプに表示する1行の説明を表す。
	Summary string
	// Args は必須の位置引数を順番に並べる。
	// App.Run は引数の数が一致しなければエラーにする。
	Args []Arg
	// Flags は fs にコマンドのフラグを登録する。
	// フラグが無いコマンドでは nil にする。
	Flags func(fs *flag.FlagSet)
	// Run は引数とフラグの格納後にコマンドを実行する。
	Run func(ctx context.Context) (Output, error)
}

// Group は task のようにコマンド群をまとめる名詞を表す。
type Group struct {
	Name     string
	Summary  string
	Commands []*Command
}

// App はコマンドツリーの根を表す。
type App struct {
	Name    string
	Version string
	Groups  []*Group
}

// runner は App を1回実行し、その出力先に書き出す。
type runner struct {
	app     *App
	streams IO
}

// Run は args を解析し、選ばれたコマンドの実行結果を書き出して終了コードを返す。
func (a *App) Run(ctx context.Context, args []string, streams IO) int {
	r := runner{app: a, streams: streams}
	if len(args) == 0 {
		return r.fail(a.Name, fmt.Errorf("%w: missing command", errkind.ErrInvalid))
	}
	switch args[0] {
	case "-h", "-help", "--help":
		return r.write(appUsage(a))
	case "-version", "--version":
		return r.write(a.Name + " version " + a.Version + "\n")
	}
	for _, g := range a.Groups {
		if g.Name == args[0] {
			return r.runGroup(ctx, g, args[1:])
		}
	}
	return r.fail(a.Name, fmt.Errorf("%w: unknown command %q", errkind.ErrInvalid, args[0]))
}

// runGroup は args で指定した g のコマンドを実行する。
func (r runner) runGroup(ctx context.Context, g *Group, args []string) int {
	path := r.app.Name + " " + g.Name
	if len(args) == 0 {
		return r.fail(path, fmt.Errorf("%w: missing subcommand", errkind.ErrInvalid))
	}
	switch args[0] {
	case "-h", "-help", "--help":
		return r.write(groupUsage(path, g))
	}
	for _, c := range g.Commands {
		if c.Name == args[0] {
			return r.runCommand(ctx, path+" "+c.Name, c, args[1:])
		}
	}
	return r.fail(path, fmt.Errorf("%w: unknown subcommand %q", errkind.ErrInvalid, args[0]))
}

// runCommand は c の args を解析して実行する。
func (r runner) runCommand(ctx context.Context, path string, c *Command, args []string) int {
	fs, asJSON := newFlagSet(path, c)
	positional, err := parse(fs, args)
	if errors.Is(err, flag.ErrHelp) {
		return r.write(commandUsage(path, c, fs))
	}
	if err != nil {
		return r.fail(path, err)
	}
	if len(positional) != len(c.Args) {
		return r.fail(path, fmt.Errorf("%w: want %d argument(s), got %d", errkind.ErrInvalid,
			len(c.Args), len(positional)))
	}
	for i, arg := range c.Args {
		*arg.Value = positional[i]
	}
	out, err := c.Run(ctx)
	if err != nil {
		return r.fail(path, err)
	}
	if *asJSON {
		err = writeJSON(r.streams.Out, out)
	} else {
		err = out.WriteText(r.streams.Out)
	}
	if err != nil {
		return r.fail(path, fmt.Errorf("write output: %w", err))
	}
	return ExitOK
}

// fail は Fail と同じ形式で err を表示し、入力の誤りには path のコマンドのヘルプを案内する。
func (r runner) fail(path string, err error) int {
	code := Fail(r.streams, r.app.Name, err)
	if code != ExitInvalid {
		return code
	}
	_, werr := io.WriteString(r.streams.Err, "Run '"+path+" --help' for usage.\n")
	if werr != nil {
		return ExitError
	}
	return code
}

// write は text を出力先に書き出し、終了コードを返す。
func (r runner) write(text string) int {
	_, err := io.WriteString(r.streams.Out, text)
	if err != nil {
		return ExitError
	}
	return ExitOK
}

// Fail は streams.Err に <name>: <err> の形式で err を書き出し、その終了コードを返す。
// app パッケージはコマンドツリーの構築前に起きたエラーにこの関数を使う。
func Fail(streams IO, name string, err error) int {
	code := exitCode(err)
	_, werr := io.WriteString(streams.Err, name+": "+err.Error()+"\n")
	if werr != nil {
		return ExitError
	}
	return code
}

// newFlagSet は --json フラグを加えた c のフラグ集合と、そのフラグの値を返す。
func newFlagSet(path string, c *Command) (*flag.FlagSet, *bool) {
	fs := flag.NewFlagSet(path, flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	asJSON := new(bool)
	fs.BoolVar(asJSON, "json", false, "Write the output as JSON")
	if c.Flags != nil {
		c.Flags(fs)
	}
	return fs, asJSON
}

// parse は args のどの位置にあるフラグも解析し、位置引数を返す。
// 標準の flag パッケージは最初の位置引数で止まるため、parse はその後から解析を再開する。
// -- より後の引数は常に位置引数として扱う。
func parse(fs *flag.FlagSet, args []string) ([]string, error) {
	positional := make([]string, 0, len(args))
	remaining := args
	for {
		err := fs.Parse(remaining)
		if err != nil {
			return nil, fmt.Errorf("%w: %w", errkind.ErrInvalid, err)
		}
		rest := fs.Args()
		if len(rest) == 0 {
			return positional, nil
		}
		consumed := remaining[:len(remaining)-len(rest)]
		if len(consumed) > 0 && consumed[len(consumed)-1] == "--" {
			return append(positional, rest...), nil
		}
		positional = append(positional, rest[0])
		remaining = rest[1:]
	}
}

// writeJSON は out を字下げした JSON で書き出す。
func writeJSON(w io.Writer, out Output) error {
	enc := json.NewEncoder(w)
	enc.SetIndent("", "  ")
	err := enc.Encode(out)
	if err != nil {
		return fmt.Errorf("encode JSON: %w", err)
	}
	return nil
}
