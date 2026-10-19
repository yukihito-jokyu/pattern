package main

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"go/types"
	"io/fs"
	"os"
	"path"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"unicode"
)

type goFile struct {
	path string // ルートからの相対パス（/ 区切り）
	ast  *ast.File
	src  string
}

type project struct {
	root   string
	module string
	fset   *token.FileSet
	files  map[string]*goFile
	aggs   []string          // internal/domain 直下のディレクトリ名
	tables map[string]*table // マイグレーションで作られるテーブル
	found  []finding
}

func load(root string) (*project, error) {
	p := &project{root: root, fset: token.NewFileSet(), files: map[string]*goFile{}, tables: map[string]*table{}}

	mod, err := os.ReadFile(filepath.Join(root, "go.mod"))
	if err != nil {
		return nil, fmt.Errorf("go.mod が読めない（-root にプロジェクトのルートを渡す）: %w", err)
	}
	for _, line := range strings.Split(string(mod), "\n") {
		if strings.HasPrefix(line, "module ") {
			p.module = strings.TrimSpace(strings.TrimPrefix(line, "module "))
		}
	}

	err = filepath.WalkDir(root, func(full string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		name := d.Name()
		if d.IsDir() {
			if full != root && (strings.HasPrefix(name, ".") || name == "bin" || name == "vendor" || name == "node_modules") {
				return filepath.SkipDir
			}
			return nil
		}
		if !strings.HasSuffix(name, ".go") {
			return nil
		}
		src, err := os.ReadFile(full)
		if err != nil {
			return err
		}
		f, err := parser.ParseFile(p.fset, full, src, parser.ParseComments)
		if err != nil {
			return fmt.Errorf("parse %s: %w", full, err)
		}
		rel, _ := filepath.Rel(root, full)
		rel = filepath.ToSlash(rel)
		p.files[rel] = &goFile{path: rel, ast: f, src: string(src)}
		return nil
	})
	if err != nil {
		return nil, err
	}

	entries, _ := os.ReadDir(filepath.Join(root, "internal", "domain"))
	for _, e := range entries {
		if e.IsDir() {
			p.aggs = append(p.aggs, e.Name())
		}
	}
	sort.Strings(p.aggs)

	return p, nil
}

func (p *project) line(pos token.Pos) int { return p.fset.Position(pos).Line }

func isTestPath(s string) bool { return strings.HasSuffix(s, "_test.go") }

// dirFiles は dir 直下の Go ファイルを返す。tests が true ならテストファイルだけ、false ならテスト以外だけ。
func (p *project) dirFiles(dir string, tests bool) []*goFile {
	var out []*goFile
	for rel, f := range p.files {
		if path.Dir(rel) == dir && isTestPath(rel) == tests {
			out = append(out, f)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].path < out[j].path })
	return out
}

func (p *project) readText(rel string) (string, bool) {
	b, err := os.ReadFile(filepath.Join(p.root, filepath.FromSlash(rel)))
	if err != nil {
		return "", false
	}
	return string(b), true
}

func exportName(s string) string {
	if s == "" {
		return s
	}
	r := []rune(s)
	r[0] = unicode.ToUpper(r[0])
	return string(r)
}

// camel は snake_case を CamelCase にする（created_at → CreatedAt）。
func camel(s string) string {
	var b strings.Builder
	for _, part := range strings.Split(s, "_") {
		b.WriteString(exportName(part))
	}
	return b.String()
}

func exprString(e ast.Expr) string { return types.ExprString(e) }

func recvTypeName(fd *ast.FuncDecl) string {
	if fd.Recv == nil || len(fd.Recv.List) == 0 {
		return ""
	}
	t := fd.Recv.List[0].Type
	if s, ok := t.(*ast.StarExpr); ok {
		t = s.X
	}
	if id, ok := t.(*ast.Ident); ok {
		return id.Name
	}
	return ""
}

func recvName(fd *ast.FuncDecl) string {
	if fd.Recv == nil || len(fd.Recv.List) == 0 || len(fd.Recv.List[0].Names) == 0 {
		return ""
	}
	return fd.Recv.List[0].Names[0].Name
}

// domainImports は f が import している domain パッケージの、ファイル内での名前を返す。
func (p *project) domainImports(f *ast.File) map[string]bool {
	out := map[string]bool{}
	for _, imp := range f.Imports {
		ip, _ := strconv.Unquote(imp.Path.Value)
		if !strings.HasPrefix(ip, p.module+"/internal/domain/") {
			continue
		}
		name := path.Base(ip)
		if imp.Name != nil {
			name = imp.Name.Name
		}
		out[name] = true
	}
	return out
}

func mentions(e ast.Node, pkgs map[string]bool) bool {
	found := false
	ast.Inspect(e, func(n ast.Node) bool {
		if sel, ok := n.(*ast.SelectorExpr); ok {
			if id, ok := sel.X.(*ast.Ident); ok && pkgs[id.Name] {
				found = true
			}
		}
		return !found
	})
	return found
}

// domainConsts は集約の domain にある整数の定数を返す（maxNameLength など）。
func (p *project) domainConsts(agg string) map[string]int {
	out := map[string]int{}
	for _, f := range p.dirFiles("internal/domain/"+agg, false) {
		for _, decl := range f.ast.Decls {
			gd, ok := decl.(*ast.GenDecl)
			if !ok || gd.Tok != token.CONST {
				continue
			}
			for _, spec := range gd.Specs {
				vs := spec.(*ast.ValueSpec)
				for i, name := range vs.Names {
					if i >= len(vs.Values) {
						continue
					}
					if lit, ok := vs.Values[i].(*ast.BasicLit); ok && lit.Kind == token.INT {
						if v, err := strconv.Atoi(lit.Value); err == nil {
							out[name.Name] = v
						}
					}
				}
			}
		}
	}
	return out
}

// aggForTable はテーブル名（複数形）から集約名を探す。
func (p *project) aggForTable(t string) string {
	for _, agg := range p.aggs {
		if t == agg+"s" || t == agg+"es" || (strings.HasSuffix(agg, "y") && t == strings.TrimSuffix(agg, "y")+"ies") {
			return agg
		}
	}
	return ""
}

func funcDecls(f *ast.File) []*ast.FuncDecl {
	var out []*ast.FuncDecl
	for _, d := range f.Decls {
		if fd, ok := d.(*ast.FuncDecl); ok {
			out = append(out, fd)
		}
	}
	return out
}

func unquote(lit *ast.BasicLit) string {
	s, err := strconv.Unquote(lit.Value)
	if err != nil {
		return lit.Value
	}
	return s
}
