package main

import (
	"go/ast"
	"go/token"
	"path"
	"strings"
)

const usecaseDir = "internal/usecase"

var writePrefixes = []string{"Create", "Update", "Delete", "Save", "Insert", "Remove", "Add", "Upsert", "Store"}

func isWrite(method string) bool {
	for _, w := range writePrefixes {
		if strings.HasPrefix(method, w) {
			return true
		}
	}
	return false
}

// portKinds は port.go の interface 名を repo / tx / external に分類する。
func (p *project) portKinds() map[string]string {
	kinds := map[string]string{}
	f, ok := p.files[usecaseDir+"/port.go"]
	if !ok {
		return kinds
	}
	ast.Inspect(f.ast, func(n ast.Node) bool {
		ts, ok := n.(*ast.TypeSpec)
		if !ok {
			return true
		}
		if _, ok := ts.Type.(*ast.InterfaceType); !ok {
			return true
		}
		switch {
		case ts.Name.Name == "TxManager":
			kinds[ts.Name.Name] = "tx"
		case strings.HasSuffix(ts.Name.Name, "Repository"):
			kinds[ts.Name.Name] = "repo"
		default:
			kinds[ts.Name.Name] = "external"
		}
		return true
	})
	return kinds
}

func (p *project) checkUsecase() {
	kinds := p.portKinds()
	structFields := map[string]map[string]string{} // Usecase struct → フィールド名 → 型名
	constructors := map[string]bool{}
	var methods []struct {
		f  *goFile
		fd *ast.FuncDecl
	}

	for _, f := range p.dirFiles(usecaseDir, false) {
		domain := p.domainImports(f.ast)
		for _, decl := range f.ast.Decls {
			switch d := decl.(type) {
			case *ast.GenDecl:
				if d.Tok != token.TYPE {
					continue
				}
				for _, spec := range d.Specs {
					ts := spec.(*ast.TypeSpec)
					switch t := ts.Type.(type) {
					case *ast.InterfaceType:
						if path.Base(f.path) != "port.go" {
							p.add("ERROR", "U01", f.path, p.line(ts.Pos()), "interface %s は port.go に置く", ts.Name.Name)
						}
					case *ast.StructType:
						name := ts.Name.Name
						if strings.HasSuffix(name, "Input") || strings.HasSuffix(name, "Output") {
							for _, field := range t.Fields.List {
								if mentions(field.Type, domain) {
									p.add("ERROR", "U03", f.path, p.line(field.Pos()), "%s が domain の型 %s を持っている（文字列などに詰め替える）", name, exprString(field.Type))
								}
							}
						}
						if strings.HasSuffix(name, "Usecase") {
							fields := map[string]string{}
							for _, field := range t.Fields.List {
								if id, ok := field.Type.(*ast.Ident); ok {
									for _, n := range field.Names {
										fields[n.Name] = id.Name
									}
								}
							}
							structFields[name] = fields
						}
					}
				}
			case *ast.FuncDecl:
				if ast.IsExported(d.Name.Name) && d.Type.Results != nil {
					for _, r := range d.Type.Results.List {
						if mentions(r.Type, domain) {
							p.add("ERROR", "U02", f.path, p.line(d.Pos()), "%s が domain の型 %s を返している（Output に詰め替える）", d.Name.Name, exprString(r.Type))
						}
					}
				}
				if d.Recv == nil && strings.HasPrefix(d.Name.Name, "New") && strings.HasSuffix(d.Name.Name, "Usecase") {
					res := ""
					if d.Type.Results != nil && len(d.Type.Results.List) == 1 {
						res = exprString(d.Type.Results.List[0].Type)
					}
					if res != "*"+strings.TrimPrefix(d.Name.Name, "New") {
						p.add("WARN", "U04", f.path, p.line(d.Pos()), "%s は *%s を返す", d.Name.Name, strings.TrimPrefix(d.Name.Name, "New"))
					}
					constructors[strings.TrimPrefix(d.Name.Name, "New")] = true
				}
				if strings.HasSuffix(recvTypeName(d), "Usecase") {
					methods = append(methods, struct {
						f  *goFile
						fd *ast.FuncDecl
					}{f, d})
				}
			}
		}

		ast.Inspect(f.ast, func(n ast.Node) bool {
			if call, ok := n.(*ast.CallExpr); ok && exprString(call.Fun) == "errors.New" {
				p.add("ERROR", "U10", f.path, p.line(call.Pos()), "usecase で独自のエラーを定義しない（ビジネスルールのエラーは domain の errors.go に置く）")
			}
			return true
		})
	}

	for name := range structFields {
		if !constructors[name] {
			p.add("WARN", "U04", usecaseDir, 0, "%s のコンストラクタ New%s がない", name, name)
		}
	}

	for _, m := range methods {
		p.checkUsecaseMethod(m.f, m.fd, structFields[recvTypeName(m.fd)], kinds)
	}
}

type portCall struct {
	field, method, kind string
	inTx                bool
	line                int
}

func (p *project) checkUsecaseMethod(f *goFile, fd *ast.FuncDecl, fields map[string]string, kinds map[string]string) {
	name := fd.Name.Name
	if ast.IsExported(name) {
		params := fd.Type.Params.List
		if len(params) >= 2 {
			in := exprString(params[1].Type)
			if !strings.HasPrefix(in, name) || !strings.HasSuffix(in, "Input") {
				p.add("WARN", "U04", f.path, p.line(fd.Pos()), "%s の入力は %s<集約>Input にする（今は %s）", name, name, in)
			}
		}
		if fd.Type.Results != nil && len(fd.Type.Results.List) == 2 {
			out := exprString(fd.Type.Results.List[0].Type)
			if !strings.HasPrefix(out, "*") || !strings.HasSuffix(out, "Output") {
				p.add("WARN", "U04", f.path, p.line(fd.Pos()), "%s の戻り値は *<集約>Output か *<集約>ListOutput にする（今は %s）", name, out)
			}
		}
	}
	if fd.Body == nil {
		return
	}

	recv := recvName(fd)
	var calls []portCall
	var walk func(n ast.Node, inTx bool)
	walk = func(n ast.Node, inTx bool) {
		ast.Inspect(n, func(n ast.Node) bool {
			call, ok := n.(*ast.CallExpr)
			if !ok {
				return true
			}
			sel, ok := call.Fun.(*ast.SelectorExpr)
			if !ok {
				return true
			}
			inner, ok := sel.X.(*ast.SelectorExpr)
			if !ok {
				return true
			}
			id, ok := inner.X.(*ast.Ident)
			if !ok || id.Name != recv {
				return true
			}
			kind := kinds[fields[inner.Sel.Name]]
			if kind == "" {
				return true
			}
			if kind == "tx" && sel.Sel.Name == "Do" {
				for _, a := range call.Args {
					walk(a, true)
				}
				return false
			}
			calls = append(calls, portCall{field: inner.Sel.Name, method: sel.Sel.Name, kind: kind, inTx: inTx, line: p.line(call.Pos())})
			return true
		})
	}
	walk(fd.Body, false)

	repoCalls := 0
	for _, c := range calls {
		if c.kind == "repo" {
			repoCalls++
		}
	}
	for _, c := range calls {
		if c.kind == "external" && c.inTx {
			p.add("ERROR", "U06", f.path, c.line, "%s.%s を TxManager.Do の中で呼んでいる（外部サービスはコミットの後に呼ぶ）", c.field, c.method)
		}
		if c.kind == "repo" && !c.inTx && isWrite(c.method) && repoCalls >= 2 {
			p.add("ERROR", "U05", f.path, c.line, "%s は複数の repository 呼び出しを含むのに、書き込み %s.%s が TxManager.Do の外にある", name, c.field, c.method)
		}
	}
}
