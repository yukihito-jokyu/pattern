package cli

import (
	"flag"
	"fmt"
	"io"
	"strconv"
	"strings"
)

// WriteReference は a の全コマンドの使い方・フラグと全終了コードを Markdown で書き出す。
// tools/clidoc はこの関数で docs/cli.md を生成する。
func (a *App) WriteReference(w io.Writer) error {
	var b strings.Builder
	b.WriteString("# " + a.Name + " command reference\n")
	for _, g := range a.Groups {
		for _, c := range g.Commands {
			path := a.Name + " " + g.Name + " " + c.Name
			fs, _ := newFlagSet(path, c)
			b.WriteString("\n## " + path + "\n\n" + c.Summary + "\n\n")
			b.WriteString("```text\n" + usageLine(path, c) + "\n```\n\n")
			b.WriteString("| Flag | Description |\n|---|---|\n")
			fs.VisitAll(func(f *flag.Flag) {
				b.WriteString("| `" + flagName(f) + "` | " + flagUsage(f) + " |\n")
			})
		}
	}
	b.WriteString("\n## Exit codes\n\n| Code | Meaning |\n|---|---|\n")
	for _, e := range ExitCodes() {
		b.WriteString("| " + strconv.Itoa(e.Code) + " | " + e.Meaning + " |\n")
	}
	_, err := io.WriteString(w, b.String())
	return err
}

// appUsage は a のヘルプを返す。
func appUsage(a *App) string {
	rows := make([][]string, 0, len(a.Groups))
	for _, g := range a.Groups {
		rows = append(rows, []string{g.Name, g.Summary})
	}
	return "Usage:\n  " + a.Name + " <command> <subcommand> [flags] [arguments]\n\n" +
		"Commands:\n" + indentTable(rows) + "\n" +
		"Flags:\n" + indentTable([][]string{{"--help", "Show help"}, {"--version", "Show the version"}}) + "\n" +
		"Run '" + a.Name + " <command> --help' for the subcommands of a command.\n"
}

// groupUsage は g のヘルプを返す。
func groupUsage(path string, g *Group) string {
	rows := make([][]string, 0, len(g.Commands))
	for _, c := range g.Commands {
		rows = append(rows, []string{c.Name, c.Summary})
	}
	return g.Summary + "\n\nUsage:\n  " + path + " <subcommand> [flags] [arguments]\n\n" +
		"Subcommands:\n" + indentTable(rows) + "\n" +
		"Run '" + path + " <subcommand> --help' for the flags of a subcommand.\n"
}

// commandUsage は c のヘルプを返す。
func commandUsage(path string, c *Command, fs *flag.FlagSet) string {
	rows := [][]string{{"--help", "Show help"}}
	fs.VisitAll(func(f *flag.Flag) {
		rows = append(rows, []string{flagName(f), flagUsage(f)})
	})
	return c.Summary + "\n\nUsage:\n  " + usageLine(path, c) + "\n\nFlags:\n" + indentTable(rows)
}

// usageLine は go-cli task add [flags] <title> のような c の使い方を返す。
func usageLine(path string, c *Command) string {
	words := make([]string, 0, len(c.Args)+1)
	words = append(words, path+" [flags]")
	for _, arg := range c.Args {
		words = append(words, "<"+arg.Name+">")
	}
	return strings.Join(words, " ")
}

// flagName は値のプレースホルダーを含むコマンドライン形式のフラグ名を返す。
func flagName(f *flag.Flag) string {
	name, _ := flag.UnquoteUsage(f)
	if name == "" {
		return "--" + f.Name
	}
	return "--" + f.Name + " <" + name + ">"
}

// flagUsage は既定値を含む f の使い方を返す。
func flagUsage(f *flag.Flag) string {
	_, usage := flag.UnquoteUsage(f)
	switch f.DefValue {
	case "", "false", "0":
		return usage
	default:
		return usage + " (default: " + f.DefValue + ")"
	}
}

// indentTable は rows をヘルプ用に字下げした表として返す。
func indentTable(rows [][]string) string {
	var b strings.Builder
	width := 0
	for _, row := range rows {
		width = max(width, len(row[0]))
	}
	for _, row := range rows {
		fmt.Fprintf(&b, "  %-*s  %s\n", width, row[0], row[1])
	}
	return b.String()
}
