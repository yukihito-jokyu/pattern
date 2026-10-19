package main

import (
	"go/ast"
	"go/token"
	"path"
	"regexp"
	"sort"
	"strings"
)

const adapterDir = "internal/adapter"

var (
	sqlLowerRe     = regexp.MustCompile(`\b(select|from|where|insert into|update|delete from|values|order by|group by|limit|offset|returning|join|set)\b`)
	sqlClauseRe    = regexp.MustCompile(`^(SELECT|FROM|WHERE|ORDER BY|GROUP BY|SET|RETURNING)\s+(\S.*)$`)
	sqlInsertRe    = regexp.MustCompile(`(?i)INSERT\s+INTO\s+(\w+)`)
	sqlOrderByRe   = regexp.MustCompile(`(?is)ORDER\s+BY\s+(.*?)(\bLIMIT\b|\bOFFSET\b|\bFOR\b|\)|$)`)
	sqlLeadWordRe  = regexp.MustCompile(`(?i)^\s*(\w+)`)
	queryMethodSet = map[string]bool{"ExecContext": true, "QueryContext": true, "QueryRowContext": true}
)

// checkAdapters は repository と外部サービスの adapter を検査する。
func (p *project) checkAdapters() {
	dirs := map[string]bool{}
	for rel := range p.files {
		if strings.HasPrefix(rel, adapterDir+"/") && !strings.HasPrefix(rel, handlerDir+"/") && !isTestPath(rel) {
			dirs[path.Dir(rel)] = true
		}
	}
	var sorted []string
	for d := range dirs {
		sorted = append(sorted, d)
	}
	sort.Strings(sorted)

	for _, dir := range sorted {
		p.checkPortAssertions(dir)
		for _, f := range p.dirFiles(dir, false) {
			for _, fd := range funcDecls(f.ast) {
				if fd.Body != nil {
					p.checkSQLFunc(f, fd)
				}
			}
		}
	}
}

// checkPortAssertions は、コンストラクタを持つ公開型に var _ usecase.X = (*T)(nil) があるかを見る（R01）。
func (p *project) checkPortAssertions(dir string) {
	asserted := map[string]bool{}
	types := map[string]int{}
	var typeFile = map[string]string{}
	ctors := map[string]bool{}
	for _, f := range p.dirFiles(dir, false) {
		for _, decl := range f.ast.Decls {
			switch d := decl.(type) {
			case *ast.GenDecl:
				for _, spec := range d.Specs {
					switch s := spec.(type) {
					case *ast.TypeSpec:
						if _, ok := s.Type.(*ast.StructType); ok && ast.IsExported(s.Name.Name) {
							types[s.Name.Name] = p.line(s.Pos())
							typeFile[s.Name.Name] = f.path
						}
					case *ast.ValueSpec:
						if len(s.Names) == 1 && s.Names[0].Name == "_" && s.Type != nil && strings.HasPrefix(exprString(s.Type), "usecase.") && len(s.Values) == 1 {
							v := exprString(s.Values[0])
							v = strings.TrimSuffix(strings.TrimPrefix(v, "(*"), ")(nil)")
							asserted[v] = true
						}
					}
				}
			case *ast.FuncDecl:
				if d.Recv == nil && strings.HasPrefix(d.Name.Name, "New") {
					ctors[strings.TrimPrefix(d.Name.Name, "New")] = true
				}
			}
		}
	}
	for t, line := range types {
		if ctors[t] && !asserted[t] {
			p.add("ERROR", "R01", typeFile[t], line, "var _ usecase.Xxx = (*%s)(nil) で port を実装していることを保証する", t)
		}
	}
}

type sqlText struct {
	text string
	line int
}

func (p *project) checkSQLFunc(f *goFile, fd *ast.FuncDecl) {
	var sqls []sqlText
	ast.Inspect(fd.Body, func(n ast.Node) bool {
		switch x := n.(type) {
		case *ast.GenDecl:
			if x.Tok != token.CONST {
				return true
			}
			for _, spec := range x.Specs {
				for _, v := range spec.(*ast.ValueSpec).Values {
					if lit, ok := v.(*ast.BasicLit); ok && lit.Kind == token.STRING && looksLikeSQL(unquote(lit)) {
						sqls = append(sqls, sqlText{unquote(lit), p.line(lit.Pos())})
					}
				}
			}
		case *ast.CallExpr:
			sel, ok := x.Fun.(*ast.SelectorExpr)
			if !ok || !queryMethodSet[sel.Sel.Name] || len(x.Args) < 2 {
				return true
			}
			if lit, ok := x.Args[1].(*ast.BasicLit); ok && lit.Kind == token.STRING {
				p.add("WARN", "R04", f.path, p.line(lit.Pos()), "SQL は const q = ... としてメソッド内に書く")
				sqls = append(sqls, sqlText{unquote(lit), p.line(lit.Pos())})
			}
		}
		return true
	})
	if len(sqls) == 0 {
		return
	}

	body := f.src[p.fset.Position(fd.Body.Pos()).Offset:p.fset.Position(fd.Body.End()).Offset]

	for _, q := range sqls {
		p.checkSQLStyle(f, q)

		lead := strings.ToUpper(firstWord(q.text))
		upper := strings.ToUpper(q.text)

		if (lead == "UPDATE" || lead == "DELETE") && !strings.Contains(body, "RowsAffected") {
			p.add("ERROR", "R02", f.path, q.line, "%s の後で RowsAffected() を確かめ、0 件なら <集約>.ErrNotFound を返す", lead)
		}

		if m := sqlOrderByRe.FindStringSubmatch(q.text); m != nil {
			items := strings.Split(m[1], ",")
			last := strings.Fields(strings.TrimSpace(items[len(items)-1]))
			if len(last) == 0 || (last[0] != "id" && !strings.HasSuffix(last[0], ".id")) {
				p.add("ERROR", "R03", f.path, q.line, "ORDER BY の最後に一意な列 id を足して順序を確定させる")
			}
		}

		if lead == "SELECT" && strings.Contains(body, "QueryRowContext") && !strings.Contains(upper, "EXISTS") && !strings.Contains(upper, "COUNT(") {
			if !strings.Contains(body, "sql.ErrNoRows") || !strings.Contains(body, "ErrNotFound") {
				p.add("ERROR", "R05", f.path, q.line, "1 行取得で sql.ErrNoRows を <集約>.ErrNotFound に変換していない")
			}
		}

		if m := sqlInsertRe.FindStringSubmatch(q.text); m != nil {
			if t := p.tables[strings.ToLower(m[1])]; t != nil {
				if t.hasUnique() && !strings.Contains(body, "isUniqueViolation") {
					p.add("ERROR", "R06", f.path, q.line, "%s には一意制約があるのに、isUniqueViolation で対応するドメインエラーに変換していない", t.name)
				}
				if t.hasFK() && !strings.Contains(body, "isForeignKeyViolation") {
					p.add("ERROR", "R06", f.path, q.line, "%s には外部キーがあるのに、isForeignKeyViolation で参照先の ErrNotFound に変換していない", t.name)
				}
			}
		}
	}
}

func looksLikeSQL(s string) bool {
	switch strings.ToUpper(firstWord(s)) {
	case "SELECT", "INSERT", "UPDATE", "DELETE", "WITH":
		return true
	}
	return false
}

func firstWord(s string) string {
	m := sqlLeadWordRe.FindStringSubmatch(s)
	if m == nil {
		return ""
	}
	return m[1]
}

func (p *project) checkSQLStyle(f *goFile, q sqlText) {
	if m := sqlLowerRe.FindString(q.text); m != "" {
		p.add("WARN", "R04", f.path, q.line, "SQL のキーワード %q は大文字で書く", m)
	}
	for _, raw := range strings.Split(q.text, "\n") {
		l := strings.TrimSpace(raw)
		if m := sqlClauseRe.FindStringSubmatch(l); m != nil && !strings.HasPrefix(m[2], "EXISTS") {
			p.add("WARN", "R04", f.path, q.line, "句と列は 1 行に 1 つずつ書く（%q）", l)
			continue
		}
		if i := strings.Index(l, ","); i >= 0 && strings.TrimSpace(l[i+1:]) != "" && !strings.Contains(l, "(") {
			p.add("WARN", "R04", f.path, q.line, "列は 1 行に 1 つずつ書く（%q）", l)
		}
	}
}
