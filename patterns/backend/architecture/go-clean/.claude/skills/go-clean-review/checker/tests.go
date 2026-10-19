package main

import (
	"go/ast"
	"go/token"
	"path"
	"regexp"
	"strings"
)

var (
	usecaseGotCmpRe = regexp.MustCompile(`\bgot\.\w+\s*!=`)
	domainGetterRe  = regexp.MustCompile(`\w+\.\w+\(\)\s*!=\s*tt\.want`)
)

func (p *project) checkTests() {
	for _, agg := range p.aggs {
		dir := "internal/domain/" + agg
		tests := p.dirFiles(dir, true)
		if len(tests) == 0 && len(p.dirFiles(dir, false)) > 0 {
			p.add("ERROR", "T01", dir, 0, "domain %s のテストがない（domain と usecase は必ずテストを書く）", agg)
		}
		for _, f := range tests {
			if f.ast.Name.Name != agg+"_test" {
				p.add("WARN", "T08", f.path, 1, "domain のテストは package %s_test から書く", agg)
			}
			p.checkTestFile(f, dir, false)
		}
	}

	for _, f := range p.dirFiles(usecaseDir, false) {
		base := path.Base(f.path)
		if base == "port.go" {
			continue
		}
		if _, ok := p.files[strings.TrimSuffix(f.path, ".go")+"_test.go"]; !ok {
			p.add("ERROR", "T01", f.path, 0, "%s のテスト %s がない", base, strings.TrimSuffix(base, ".go")+"_test.go")
		}
	}
	for _, f := range p.dirFiles(usecaseDir, true) {
		if f.ast.Name.Name != "usecase" {
			p.add("WARN", "T08", f.path, 1, "usecase のテストは package usecase から書く（now を差し替えるため）")
		}
		p.checkTestFile(f, usecaseDir, true)
	}
}

// targetNames は、テスト対象のパッケージの公開関数と「型_メソッド」の一覧を返す。
func (p *project) targetNames(dir string) map[string]bool {
	out := map[string]bool{}
	for _, f := range p.dirFiles(dir, false) {
		for _, fd := range funcDecls(f.ast) {
			if t := recvTypeName(fd); t != "" {
				out[t+"_"+fd.Name.Name] = true
			} else {
				out[fd.Name.Name] = true
			}
		}
	}
	return out
}

func (p *project) checkTestFile(f *goFile, dir string, isUsecase bool) {
	names := p.targetNames(dir)
	for _, fd := range funcDecls(f.ast) {
		if !strings.HasPrefix(fd.Name.Name, "Test") || fd.Body == nil || fd.Recv != nil {
			continue
		}
		target := strings.TrimPrefix(fd.Name.Name, "Test")
		// TestUser_Rename_Errors のように、観点で分けて後ろに名前を足したものも許す
		ok := names[target]
		for i := 0; !ok && i < len(target); i++ {
			ok = target[i] == '_' && names[target[:i]]
		}
		if !ok {
			p.add("WARN", "T02", f.path, p.line(fd.Pos()), "%s は Test<関数> か Test<型>_<メソッド> の名前にする（対象が見つからない）", fd.Name.Name)
		}
		p.checkTestFunc(f, fd, isUsecase)
	}
}

func (p *project) checkTestFunc(f *goFile, fd *ast.FuncDecl, isUsecase bool) {
	var (
		table  *ast.CompositeLit
		fields []string
	)
	shared := map[string]int{}

	for _, stmt := range fd.Body.List {
		as, ok := stmt.(*ast.AssignStmt)
		if !ok {
			continue
		}
		for i, rhs := range as.Rhs {
			if i >= len(as.Lhs) {
				break
			}
			lhs := exprString(as.Lhs[i])
			if call, ok := rhs.(*ast.CallExpr); ok && p.isEntityCtor(exprString(call.Fun)) {
				shared[lhs] = p.line(as.Pos())
			}
			if cl, ok := rhs.(*ast.CompositeLit); ok && lhs == "tests" {
				if at, ok := cl.Type.(*ast.ArrayType); ok {
					if st, ok := at.Elt.(*ast.StructType); ok {
						table = cl
						for _, field := range st.Fields.List {
							for _, n := range field.Names {
								fields = append(fields, n.Name)
							}
						}
					}
				}
			}
		}
	}

	if table != nil {
		p.checkTableFields(f, fd, fields, table.Pos())
	}

	// テーブルの外で 1 つだけ作ったエンティティや fake を、テーブルか t.Run の中で使っていないか
	for name, line := range shared {
		used := false
		ast.Inspect(fd.Body, func(n ast.Node) bool {
			switch x := n.(type) {
			case *ast.CompositeLit:
				if x == table {
					used = used || refersTo(x, name)
					return false
				}
			case *ast.CallExpr:
				if exprString(x.Fun) == "t.Run" {
					used = used || refersTo(x, name)
					return false
				}
			}
			return !used
		})
		if used {
			p.add("WARN", "T06", f.path, line, "%s をテーブルの外で 1 つだけ作り、複数のケースで使っている（エンティティや fake はケースごとに Reconstruct で作る。t.Parallel でデータ競合になる）", name)
		}
	}

	hasWantErr := false
	for _, n := range fields {
		if n == "wantErr" {
			hasWantErr = true
		}
	}

	ast.Inspect(fd.Body, func(n ast.Node) bool {
		call, ok := n.(*ast.CallExpr)
		if !ok || exprString(call.Fun) != "t.Run" || len(call.Args) != 2 {
			return true
		}
		fl, ok := call.Args[1].(*ast.FuncLit)
		if !ok {
			return true
		}
		p.checkRunBody(f, fl, hasWantErr, isUsecase)
		return false
	})
}

func (p *project) checkTableFields(f *goFile, fd *ast.FuncDecl, fields []string, pos token.Pos) {
	if len(fields) == 0 {
		return
	}
	line := p.line(pos)
	if fields[0] != "name" {
		p.add("WARN", "T05", f.path, line, "%s のテーブルの最初のフィールドは name にする（今は %s）", fd.Name.Name, strings.Join(fields, ", "))
	}
	for i, n := range fields {
		if n == "wantErr" && i != len(fields)-1 {
			p.add("WARN", "T05", f.path, line, "%s のテーブルの wantErr は最後に置く（今は %s）", fd.Name.Name, strings.Join(fields, ", "))
		}
	}
	seenWant := false
	for _, n := range fields {
		if strings.HasPrefix(n, "want") {
			seenWant = true
		} else if seenWant {
			p.add("WARN", "T05", f.path, line, "%s のテーブルは name → 準備 → 入力 → want... → wantErr の順にする（今は %s）", fd.Name.Name, strings.Join(fields, ", "))
			break
		}
	}
}

func (p *project) checkRunBody(f *goFile, fl *ast.FuncLit, hasWantErr, isUsecase bool) {
	var errIf *ast.IfStmt
	cmpIfs := 0
	for _, stmt := range fl.Body.List {
		is, ok := stmt.(*ast.IfStmt)
		if !ok {
			continue
		}
		cond := exprString(is.Cond)
		if errIf == nil && strings.Contains(cond, "tt.wantErr") && !strings.Contains(cond, "!= nil") {
			errIf = is
		}
		if isUsecase && usecaseGotCmpRe.MatchString(cond) {
			cmpIfs++
		}
		if !isUsecase && domainGetterRe.MatchString(cond) {
			cmpIfs++
		}
	}
	line := p.line(fl.Pos())
	if hasWantErr {
		switch {
		case errIf == nil:
			p.add("WARN", "T04", f.path, line, "t.Run の中で最初に errors.Is(err, tt.wantErr) を確かめる")
		case !strings.Contains(exprString(errIf.Cond), "errors.Is("):
			p.add("WARN", "T04", f.path, p.line(errIf.Pos()), "エラーは errors.Is(err, tt.wantErr) で比べる（== で比べない）")
		default:
			fatal := false
			ast.Inspect(errIf.Body, func(n ast.Node) bool {
				if c, ok := n.(*ast.CallExpr); ok && exprString(c.Fun) == "t.Fatalf" {
					fatal = true
				}
				return !fatal
			})
			if !fatal {
				p.add("WARN", "T04", f.path, p.line(errIf.Pos()), "errors.Is の確認は t.Fatalf で止める")
			}
		}
	}
	if cmpIfs >= 2 {
		if isUsecase {
			p.add("WARN", "T07", f.path, line, "Output のフィールドを 1 つずつ比べている（期待する Output を struct で作り *got != want で 1 回で比べる）")
		} else {
			p.add("WARN", "T07", f.path, line, "getter の比較を別々の if に分けている（|| でつないだ 1 つの if にする）")
		}
	}
}

// isEntityCtor は、fn が集約のエンティティか fake を作る関数（user.Reconstruct、newFakeUserRepository など）かを返す。
func (p *project) isEntityCtor(fn string) bool {
	if strings.HasPrefix(fn, "newFake") {
		return true
	}
	for _, agg := range p.aggs {
		if fn == agg+".New" || fn == agg+".Reconstruct" {
			return true
		}
	}
	return false
}

func refersTo(n ast.Node, name string) bool {
	found := false
	ast.Inspect(n, func(n ast.Node) bool {
		if id, ok := n.(*ast.Ident); ok && id.Name == name {
			found = true
		}
		return !found
	})
	return found
}
