package main

import (
	"go/ast"
	"go/token"
	"path"
	"regexp"
	"strings"
)

const handlerDir = "internal/adapter/handler"

type route struct {
	method   string // GET など
	path     string // gin の形式（/users/:id）
	handler  string // ハンドラの型（UserHandler）。インラインの関数なら空
	function string // ハンドラのメソッド名
	line     int
}

type mapping struct {
	target string
	code   string
	line   int
}

var httpMethods = map[string]bool{"GET": true, "POST": true, "PUT": true, "PATCH": true, "DELETE": true}

// handlerConsts は handler パッケージの文字列定数を返す（codeInvalidArgument など）。
func (p *project) handlerConsts() map[string]string {
	out := map[string]string{}
	for _, f := range p.dirFiles(handlerDir, false) {
		for _, decl := range f.ast.Decls {
			gd, ok := decl.(*ast.GenDecl)
			if !ok || gd.Tok != token.CONST {
				continue
			}
			for _, spec := range gd.Specs {
				vs := spec.(*ast.ValueSpec)
				for i, n := range vs.Names {
					if i < len(vs.Values) {
						if lit, ok := vs.Values[i].(*ast.BasicLit); ok && lit.Kind == token.STRING {
							out[n.Name] = unquote(lit)
						}
					}
				}
			}
		}
	}
	return out
}

func (p *project) errorMappings() []mapping {
	f, ok := p.files[handlerDir+"/error.go"]
	if !ok {
		return nil
	}
	consts := p.handlerConsts()
	var out []mapping
	ast.Inspect(f.ast, func(n ast.Node) bool {
		vs, ok := n.(*ast.ValueSpec)
		if !ok || len(vs.Names) != 1 || vs.Names[0].Name != "errorMappings" || len(vs.Values) != 1 {
			return true
		}
		lit, ok := vs.Values[0].(*ast.CompositeLit)
		if !ok {
			return false
		}
		for _, e := range lit.Elts {
			row, ok := e.(*ast.CompositeLit)
			if !ok || len(row.Elts) != 3 {
				continue
			}
			m := mapping{target: exprString(row.Elts[0]), line: p.line(row.Pos())}
			switch c := row.Elts[2].(type) {
			case *ast.BasicLit:
				m.code = unquote(c)
			case *ast.Ident:
				m.code = consts[c.Name]
			}
			out = append(out, m)
		}
		return false
	})
	return out
}

func (p *project) routes() []route {
	f, ok := p.files[handlerDir+"/router.go"]
	if !ok {
		return nil
	}
	var out []route
	for _, fd := range funcDecls(f.ast) {
		if fd.Name.Name != "NewRouter" || fd.Body == nil {
			continue
		}
		params := map[string]string{}
		for _, field := range fd.Type.Params.List {
			t := field.Type
			if s, ok := t.(*ast.StarExpr); ok {
				t = s.X
			}
			for _, n := range field.Names {
				params[n.Name] = exprString(t)
			}
		}
		ast.Inspect(fd.Body, func(n ast.Node) bool {
			call, ok := n.(*ast.CallExpr)
			if !ok || len(call.Args) < 2 {
				return true
			}
			sel, ok := call.Fun.(*ast.SelectorExpr)
			if !ok || !httpMethods[sel.Sel.Name] {
				return true
			}
			lit, ok := call.Args[0].(*ast.BasicLit)
			if !ok {
				return true
			}
			r := route{method: sel.Sel.Name, path: unquote(lit), line: p.line(call.Pos())}
			if hs, ok := call.Args[len(call.Args)-1].(*ast.SelectorExpr); ok {
				if id, ok := hs.X.(*ast.Ident); ok {
					r.handler, r.function = params[id.Name], hs.Sel.Name
				}
			}
			out = append(out, r)
			return true
		})
	}
	return out
}

// handlerMethod は handler パッケージから型 typ のメソッド name を探す。
func (p *project) handlerMethod(typ, name string) (*goFile, *ast.FuncDecl) {
	for _, f := range p.dirFiles(handlerDir, false) {
		for _, fd := range funcDecls(f.ast) {
			if recvTypeName(fd) == typ && fd.Name.Name == name {
				return f, fd
			}
		}
	}
	return nil, nil
}

var successStatus = map[string]string{
	"POST":   "StatusCreated",
	"GET":    "StatusOK",
	"PATCH":  "StatusOK",
	"PUT":    "StatusOK",
	"DELETE": "StatusNoContent",
}

var successStatuses = map[string]bool{
	"StatusOK": true, "StatusCreated": true, "StatusAccepted": true, "StatusNoContent": true,
}

var errVarRe = regexp.MustCompile(`^err[A-Z]`)

func (p *project) checkHandler() {
	mappings := p.errorMappings()
	targets := map[string]bool{}
	for _, m := range mappings {
		targets[m.target] = true
	}

	// H01: ドメインエラーと HTTP だけのエラーは、すべて errorMappings にある
	for _, agg := range p.aggs {
		for _, f := range p.dirFiles("internal/domain/"+agg, false) {
			ast.Inspect(f.ast, func(n ast.Node) bool {
				vs, ok := n.(*ast.ValueSpec)
				if !ok {
					return true
				}
				for _, name := range vs.Names {
					if strings.HasPrefix(name.Name, "Err") && !targets[agg+"."+name.Name] {
						p.add("ERROR", "H01", f.path, p.line(name.Pos()), "%s.%s が handler/error.go の errorMappings にない（足し忘れると 500 になる）", agg, name.Name)
					}
				}
				return true
			})
		}
	}
	for _, f := range p.dirFiles(handlerDir, false) {
		for _, decl := range f.ast.Decls {
			gd, ok := decl.(*ast.GenDecl)
			if !ok || gd.Tok != token.VAR {
				continue
			}
			for _, spec := range gd.Specs {
				vs := spec.(*ast.ValueSpec)
				for _, name := range vs.Names {
					if errVarRe.MatchString(name.Name) && !targets[name.Name] {
						p.add("ERROR", "H01", f.path, p.line(name.Pos()), "%s が errorMappings にない（足し忘れると 500 になる）", name.Name)
					}
				}
			}
		}
	}

	// H04 / H03 / H06: ルートごとのハンドラの中身
	for _, r := range p.routes() {
		if r.handler == "" {
			continue
		}
		f, fd := p.handlerMethod(r.handler, r.function)
		if fd == nil || fd.Body == nil {
			continue
		}
		p.checkHandlerMethod(f, fd, r)
	}

	// H05: DTO の置き場所
	for _, f := range p.dirFiles(handlerDir, false) {
		isDTO := path.Base(f.path) == "dto.go"
		ast.Inspect(f.ast, func(n ast.Node) bool {
			ts, ok := n.(*ast.TypeSpec)
			if !ok {
				return true
			}
			st, ok := ts.Type.(*ast.StructType)
			if !ok {
				return true
			}
			if isDTO && ast.IsExported(ts.Name.Name) {
				p.add("WARN", "H05", f.path, p.line(ts.Pos()), "DTO %s は非公開の型にする", ts.Name.Name)
			}
			if !isDTO {
				for _, field := range st.Fields.List {
					if field.Tag != nil && strings.Contains(field.Tag.Value, "json:") {
						p.add("WARN", "H05", f.path, p.line(ts.Pos()), "json タグ付きの struct %s は dto.go に置く", ts.Name.Name)
						break
					}
				}
			}
			return true
		})
	}
}

func (p *project) checkHandlerMethod(f *goFile, fd *ast.FuncDecl, r route) {
	cname := ""
	for _, field := range fd.Type.Params.List {
		if exprString(field.Type) == "*gin.Context" && len(field.Names) > 0 {
			cname = field.Names[0].Name
		}
	}
	recv := recvName(fd)
	statuses := map[string]int{}

	ast.Inspect(fd.Body, func(n ast.Node) bool {
		switch x := n.(type) {
		case *ast.CallExpr:
			sel, ok := x.Fun.(*ast.SelectorExpr)
			if !ok {
				return true
			}
			// c.JSON(http.StatusXxx, ...) / c.Status(http.StatusXxx)
			if id, ok := sel.X.(*ast.Ident); ok && id.Name == cname && len(x.Args) > 0 {
				switch sel.Sel.Name {
				case "JSON", "Status", "AbortWithStatusJSON", "AbortWithStatus", "Data", "String":
					st := exprString(x.Args[0])
					st = strings.TrimPrefix(st, "http.")
					statuses[st] = p.line(x.Pos())
				}
			}
			// h.users.Create(c, ...) のように *gin.Context を usecase に渡していないか
			if inner, ok := sel.X.(*ast.SelectorExpr); ok {
				if id, ok := inner.X.(*ast.Ident); ok && id.Name == recv {
					for _, a := range x.Args {
						if ai, ok := a.(*ast.Ident); ok && ai.Name == cname {
							p.add("ERROR", "H03", f.path, p.line(x.Pos()), "*gin.Context を %s.%s に渡している（c.Request.Context() を渡す）", inner.Sel.Name, sel.Sel.Name)
						}
					}
				}
			}
		case *ast.IfStmt:
			if be, ok := x.Cond.(*ast.BinaryExpr); ok && be.Op == token.NEQ && exprString(be.X) == "err" && exprString(be.Y) == "nil" {
				calls := false
				ast.Inspect(x.Body, func(n ast.Node) bool {
					if c, ok := n.(*ast.CallExpr); ok && exprString(c.Fun) == "writeError" {
						calls = true
					}
					return !calls
				})
				if !calls {
					p.add("ERROR", "H06", f.path, p.line(x.Pos()), "%s のエラーを writeError に渡していない（ステータスは errorMappings で決める）", fd.Name.Name)
				}
			}
		}
		return true
	})

	want := successStatus[r.method]
	hasOther := false
	for st := range statuses {
		hasOther = hasOther || (st != want && successStatuses[st])
	}
	if _, ok := statuses[want]; !ok && want != "" && !hasOther {
		p.add("ERROR", "H04", f.path, p.line(fd.Pos()), "%s %s の成功時は %s を返す", r.method, r.path, want)
	}
	for st, line := range statuses {
		if st == want {
			continue
		}
		switch {
		case strings.HasPrefix(st, "Status2") || successStatuses[st]:
			p.add("ERROR", "H04", f.path, line, "%s %s の成功時は %s を返す（今は %s）", r.method, r.path, want, st)
		case strings.HasPrefix(st, "Status"):
			p.add("ERROR", "H06", f.path, line, "%s を直接返している（エラーは writeError に渡し、ステータスは errorMappings で決める）", st)
		default:
			p.add("WARN", "H04", f.path, line, "ステータス %s は http.StatusXxx の定数で書く", st)
		}
	}
}
