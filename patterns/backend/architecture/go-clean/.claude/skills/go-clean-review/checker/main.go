// Command reviewchecker は go-clean のルールのうち、lint では止められないものを機械的に検査する。
//
// golangci-lint が 1 ファイルの中しか見ないのに対し、この検査はファイルをまたぐ整合性
// （ドメインエラーと errorMappings、router.go と openapi.yaml、マイグレーションと domain など）を見る。
// 判定は構文だけで行うので、ERROR はルール違反、WARN は人が読んで判断すべき箇所を表す。
package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"sort"
)

func main() {
	root := flag.String("root", ".", "検査するプロジェクトのルート（go.mod がある場所）")
	flag.Parse()

	abs, err := filepath.Abs(*root)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}

	p, err := load(abs)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}

	// マイグレーションの解析結果を repository と openapi の検査で使うので、最初に行う
	p.checkMigrations()
	p.checkDomain()
	p.checkUsecase()
	p.checkHandler()
	p.checkAdapters()
	p.checkOpenAPI()
	p.checkLintConfig()
	p.checkTests()
	p.checkDI()

	os.Exit(p.report())
}

type finding struct {
	sev  string
	id   string
	path string
	line int
	msg  string
}

func (p *project) add(sev, id, path string, line int, format string, args ...any) {
	p.found = append(p.found, finding{sev: sev, id: id, path: path, line: line, msg: fmt.Sprintf(format, args...)})
}

func (p *project) report() int {
	rank := map[string]int{"ERROR": 0, "WARN": 1}
	sort.SliceStable(p.found, func(i, j int) bool {
		a, b := p.found[i], p.found[j]
		if rank[a.sev] != rank[b.sev] {
			return rank[a.sev] < rank[b.sev]
		}
		if a.path != b.path {
			return a.path < b.path
		}
		return a.line < b.line
	})

	counts := map[string]int{}
	for _, f := range p.found {
		counts[f.sev]++
		loc := f.path
		if f.line > 0 {
			loc = fmt.Sprintf("%s:%d", f.path, f.line)
		}
		fmt.Printf("%-5s %s %s %s\n", f.sev, f.id, loc, f.msg)
	}

	fmt.Printf("\nERROR %d 件 / WARN %d 件（ルール ID の意味は references/checklist.md）\n", counts["ERROR"], counts["WARN"])

	if counts["ERROR"] > 0 {
		return 1
	}
	return 0
}
