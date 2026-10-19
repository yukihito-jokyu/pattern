package main

import (
	"go/ast"
	"go/token"
	"path"
	"strings"
)

var numericTypes = map[string]bool{
	"int": true, "int8": true, "int16": true, "int32": true, "int64": true,
	"uint": true, "uint8": true, "uint16": true, "uint32": true, "uint64": true,
	"float32": true, "float64": true,
}

func (p *project) checkDomain() {
	for _, agg := range p.aggs {
		dir := "internal/domain/" + agg
		entity := exportName(agg)

		var (
			hasEntity, hasNew, hasRecon bool
			entityPath                  string
			entityLine                  int
			numeric                     []string
		)

		for _, f := range p.dirFiles(dir, false) {
			for _, decl := range f.ast.Decls {
				switch d := decl.(type) {
				case *ast.GenDecl:
					switch d.Tok {
					case token.TYPE:
						for _, spec := range d.Specs {
							ts := spec.(*ast.TypeSpec)
							st, ok := ts.Type.(*ast.StructType)
							if !ok {
								continue
							}
							if ts.Name.Name == entity {
								hasEntity, entityPath, entityLine = true, f.path, p.line(ts.Pos())
							}
							for _, field := range st.Fields.List {
								if field.Tag != nil {
									p.add("ERROR", "D02", f.path, p.line(field.Pos()), "domain の struct %s にタグ %s を付けている（json / db タグは handler の dto.go にだけ書く）", ts.Name.Name, field.Tag.Value)
								}
								for _, name := range field.Names {
									if ast.IsExported(name.Name) {
										p.add("ERROR", "D01", f.path, p.line(name.Pos()), "domain の struct %s のフィールド %s が公開されている（非公開にして getter で公開する）", ts.Name.Name, name.Name)
									}
								}
								if id, ok := field.Type.(*ast.Ident); ok && ts.Name.Name == entity && numericTypes[id.Name] {
									for _, name := range field.Names {
										numeric = append(numeric, name.Name)
									}
								}
							}
						}
					case token.VAR:
						for _, spec := range d.Specs {
							vs := spec.(*ast.ValueSpec)
							for i, name := range vs.Names {
								if !strings.HasPrefix(name.Name, "Err") {
									continue
								}
								switch {
								case path.Base(f.path) != "errors.go":
									p.add("WARN", "D04", f.path, p.line(name.Pos()), "ドメインエラー %s は errors.go に置く", name.Name)
								case !d.Lparen.IsValid():
									p.add("WARN", "D04", f.path, p.line(name.Pos()), "ドメインエラー %s は var ( ... ) のブロックで定義する（1 つだけでもブロックにする）", name.Name)
								}
								if i < len(vs.Values) {
									if call, ok := vs.Values[i].(*ast.CallExpr); ok && exprString(call.Fun) == "errors.New" && len(call.Args) == 1 {
										if lit, ok := call.Args[0].(*ast.BasicLit); ok && !strings.HasPrefix(unquote(lit), agg+": ") {
											p.add("WARN", "D04", f.path, p.line(lit.Pos()), "エラーメッセージは %q で始める（%s）", agg+": ", lit.Value)
										}
									}
								}
							}
						}
					}
				case *ast.FuncDecl:
					if d.Recv != nil && strings.HasPrefix(d.Name.Name, "Set") {
						p.add("ERROR", "D03", f.path, p.line(d.Pos()), "setter %s を作らない（操作の名前のメソッドにし、New と同じ規則で検証する）", d.Name.Name)
					}
					if d.Recv == nil && d.Name.Name == "New" {
						hasNew = true
					}
					if d.Recv == nil && d.Name.Name == "Reconstruct" {
						hasRecon = true
					}
				}
			}
		}

		if hasEntity && !hasNew {
			p.add("ERROR", "D06", entityPath, entityLine, "エンティティ %s を不変条件を検証して作る New がない", entity)
		}
		if hasEntity && !hasRecon {
			p.add("ERROR", "D06", entityPath, entityLine, "エンティティ %s を DB から復元する Reconstruct がない", entity)
		}

		p.checkIDFile(agg)

		for _, field := range numeric {
			if !p.hasUpperBound(dir, field) {
				p.add("WARN", "D07", entityPath, entityLine, "数値フィールド %s の上限を検証している箇所が見当たらない（New で下限と上限を検証する）", field)
			}
		}
	}
}

func (p *project) checkIDFile(agg string) {
	rel := "internal/domain/" + agg + "/id.go"
	f, ok := p.files[rel]
	if !ok {
		p.add("ERROR", "D05", "internal/domain/"+agg, 0, "id.go がない（rules 2.2 のひな形で作る）")
		return
	}
	for _, want := range []string{"type ID string", "uuid.New()", "uuid.Parse(", "u.String()", "ErrInvalidID"} {
		if !strings.Contains(f.src, want) {
			p.add("ERROR", "D05", rel, 0, "id.go が rules 2.2 のひな形と同じ形になっていない（%q がない）", want)
		}
	}
}

// hasUpperBound は、パッケージの中に field の上限を比べる式（field > x、x < field など）があるかを返す。
func (p *project) hasUpperBound(dir, field string) bool {
	match := func(e ast.Expr) bool {
		id, ok := e.(*ast.Ident)
		return ok && strings.EqualFold(id.Name, field)
	}
	found := false
	for _, f := range p.dirFiles(dir, false) {
		ast.Inspect(f.ast, func(n ast.Node) bool {
			be, ok := n.(*ast.BinaryExpr)
			if !ok {
				return !found
			}
			if (match(be.X) && (be.Op == token.GTR || be.Op == token.GEQ)) || (match(be.Y) && (be.Op == token.LSS || be.Op == token.LEQ)) {
				found = true
			}
			return !found
		})
	}
	return found
}
