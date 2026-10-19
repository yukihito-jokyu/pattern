package main

import (
	"go/ast"
	"reflect"
	"regexp"
	"strconv"
	"strings"

	"gopkg.in/yaml.v3"
)

const openapiPath = "api/openapi.yaml"

var ginParamRe = regexp.MustCompile(`:(\w+)`)

func mapGet(n *yaml.Node, key string) *yaml.Node {
	if n == nil || n.Kind != yaml.MappingNode {
		return nil
	}
	for i := 0; i+1 < len(n.Content); i += 2 {
		if n.Content[i].Value == key {
			return n.Content[i+1]
		}
	}
	return nil
}

func mapKeys(n *yaml.Node) []*yaml.Node {
	if n == nil || n.Kind != yaml.MappingNode {
		return nil
	}
	var out []*yaml.Node
	for i := 0; i+1 < len(n.Content); i += 2 {
		out = append(out, n.Content[i])
	}
	return out
}

func seqValues(n *yaml.Node) []string {
	if n == nil || n.Kind != yaml.SequenceNode {
		return nil
	}
	var out []string
	for _, c := range n.Content {
		out = append(out, c.Value)
	}
	return out
}

var successDesc = map[string][2]string{
	"post":   {"201", "作成成功"},
	"get":    {"200", "取得成功"},
	"patch":  {"200", "更新成功"},
	"put":    {"200", "更新成功"},
	"delete": {"204", "削除成功"},
}

func (p *project) checkOpenAPI() {
	raw, ok := p.readText(openapiPath)
	if !ok {
		p.add("ERROR", "O01", openapiPath, 0, "api/openapi.yaml がない")
		return
	}
	var doc yaml.Node
	if err := yaml.Unmarshal([]byte(raw), &doc); err != nil || len(doc.Content) == 0 {
		p.add("ERROR", "O01", openapiPath, 0, "openapi.yaml を読めない: %v", err)
		return
	}
	root := doc.Content[0]
	paths := mapGet(root, "paths")
	schemas := mapGet(mapGet(root, "components"), "schemas")

	p.checkOpenAPIPaths(paths)
	p.checkOpenAPISchemas(schemas)
	p.checkErrorCodes(schemas)
}

func (p *project) checkOpenAPIPaths(paths *yaml.Node) {
	routes := p.routes()
	inRouter := map[string]route{}
	var routerOrder []string
	seen := map[string]bool{}
	for _, r := range routes {
		op := ginParamRe.ReplaceAllString(r.path, "{$1}")
		inRouter[strings.ToLower(r.method)+" "+op] = r
		if !seen[op] {
			seen[op] = true
			routerOrder = append(routerOrder, op)
		}
	}

	inSpec := map[string]bool{}
	var specOrder []string
	for _, pk := range mapKeys(paths) {
		specOrder = append(specOrder, pk.Value)
		item := mapGet(paths, pk.Value)
		for _, mk := range mapKeys(item) {
			method := mk.Value
			if _, ok := successDesc[method]; !ok {
				continue
			}
			key := method + " " + pk.Value
			inSpec[key] = true
			if _, ok := inRouter[key]; !ok {
				p.add("ERROR", "O01", openapiPath, mk.Line, "%s %s は router.go にない", strings.ToUpper(method), pk.Value)
			}
			p.checkOperation(pk.Value, method, mapGet(item, method), mk.Line)
		}
	}
	for key, r := range inRouter {
		if !inSpec[key] {
			p.add("ERROR", "O01", handlerDir+"/router.go", r.line, "%s %s が openapi.yaml にない（API を足したら同じ変更で更新する）", r.method, r.path)
		}
	}

	var common []string
	for _, s := range routerOrder {
		for _, t := range specOrder {
			if s == t {
				common = append(common, s)
			}
		}
	}
	var specCommon []string
	for _, t := range specOrder {
		if seen[t] {
			specCommon = append(specCommon, t)
		}
	}
	if len(specOrder) > 0 && !reflect.DeepEqual(common, specCommon) {
		p.add("WARN", "O02", openapiPath, mapKeys(paths)[0].Line, "paths の順が router.go と違う（router.go: %s / openapi: %s）", strings.Join(common, ", "), strings.Join(specCommon, ", "))
	}
}

func (p *project) checkOperation(pathKey, method string, op *yaml.Node, line int) {
	if sm := mapGet(op, "summary"); sm == nil || strings.TrimSpace(sm.Value) == "" {
		p.add("WARN", "O09", openapiPath, line, "%s %s に summary がない（<集約の日本語名><操作>）", strings.ToUpper(method), pathKey)
	}
	if pathKey == "/healthz" {
		return
	}
	responses := mapGet(op, "responses")
	want := successDesc[method]
	codes := map[string]bool{}
	for _, ck := range mapKeys(responses) {
		code := ck.Value
		codes[code] = true
		resp := mapGet(responses, code)
		switch {
		case strings.HasPrefix(code, "4") || strings.HasPrefix(code, "5"):
			keys := mapKeys(resp)
			if len(keys) != 1 || keys[0].Value != "$ref" || mapGet(resp, "$ref").Value != "#/components/responses/Error" {
				p.add("ERROR", "O03", openapiPath, ck.Line, "%s %s の %s は $ref: \"#/components/responses/Error\" だけを書く", strings.ToUpper(method), pathKey, code)
			}
		case strings.HasPrefix(code, "2"):
			if code != want[0] {
				p.add("ERROR", "O04", openapiPath, ck.Line, "%s の成功レスポンスは %s にする（今は %s）", strings.ToUpper(method), want[0], code)
				continue
			}
			if d := mapGet(resp, "description"); d == nil || d.Value != want[1] {
				p.add("ERROR", "O04", openapiPath, ck.Line, "%s %s の description は %q にする", strings.ToUpper(method), code, want[1])
			}
			if code == "204" && mapGet(resp, "content") != nil {
				p.add("ERROR", "O04", openapiPath, ck.Line, "204 には content を書かない")
			}
		}
	}
	if !codes[want[0]] {
		p.add("ERROR", "O04", openapiPath, line, "%s %s に成功レスポンス %s がない", strings.ToUpper(method), pathKey, want[0])
	}

	hasPathParam := strings.Contains(pathKey, "{")
	if (hasPathParam || mapGet(op, "requestBody") != nil) && !codes["400"] {
		p.add("WARN", "O10", openapiPath, line, "%s %s は入力の誤りで 400 になりうるのに、400 を書いていない", strings.ToUpper(method), pathKey)
	}
	if hasPathParam && !codes["404"] {
		p.add("WARN", "O10", openapiPath, line, "%s %s は対象がなければ 404 になりうるのに、404 を書いていない", strings.ToUpper(method), pathKey)
	}

	params := mapGet(op, "parameters")
	if params != nil {
		for _, prm := range params.Content {
			if mapGet(prm, "in") == nil || mapGet(prm, "in").Value != "path" {
				continue
			}
			nm := mapGet(prm, "name")
			if nm == nil {
				continue
			}
			name := nm.Value
			if name != "id" && !strings.HasSuffix(name, "_id") && !strings.HasSuffix(name, "Id") {
				continue
			}
			schema := mapGet(prm, "schema")
			if t, f := mapGet(schema, "type"), mapGet(schema, "format"); t == nil || t.Value != "string" || f == nil || f.Value != "uuid" {
				p.add("ERROR", "O05", openapiPath, prm.Line, "path パラメータ %s は type: string / format: uuid にする", name)
			}
		}
	}
}

type dtoField struct {
	json  string
	typ   string
	line  int
	isPtr bool
}

type dto struct {
	name   string
	fields []dtoField
	line   int
}

func (p *project) dtos() []dto {
	f, ok := p.files[handlerDir+"/dto.go"]
	if !ok {
		return nil
	}
	var out []dto
	ast.Inspect(f.ast, func(n ast.Node) bool {
		ts, ok := n.(*ast.TypeSpec)
		if !ok {
			return true
		}
		st, ok := ts.Type.(*ast.StructType)
		if !ok {
			return true
		}
		name := ts.Name.Name
		if !strings.HasSuffix(name, "Request") && !strings.HasSuffix(name, "Response") || name == "errorResponse" {
			return true
		}
		d := dto{name: name, line: p.line(ts.Pos())}
		for _, field := range st.Fields.List {
			if field.Tag == nil {
				continue
			}
			tag, _ := strconv.Unquote(field.Tag.Value)
			j := strings.Split(reflect.StructTag(tag).Get("json"), ",")[0]
			if j == "" || j == "-" {
				continue
			}
			d.fields = append(d.fields, dtoField{json: j, typ: exprString(field.Type), line: p.line(field.Pos())})
		}
		out = append(out, d)
		return true
	})
	return out
}

func schemaNameFor(dtoName string) string {
	if strings.HasSuffix(dtoName, "Request") {
		return exportName(dtoName)
	}
	return exportName(strings.TrimSuffix(dtoName, "Response"))
}

func (p *project) checkOpenAPISchemas(schemas *yaml.Node) {
	keys := mapKeys(schemas)
	if len(keys) == 0 {
		return
	}
	if keys[len(keys)-1].Value != "Error" {
		p.add("ERROR", "O06", openapiPath, keys[len(keys)-1].Line, "components/schemas の最後は Error にする（新しい集約は Error の直前に足す）")
	}
	index := map[string]int{}
	for i, k := range keys {
		index[k.Value] = i
	}
	// <動詞><集約>Request は <集約> より前に置く
	for _, agg := range p.aggs {
		entity := exportName(agg)
		ei, ok := index[entity]
		if !ok {
			continue
		}
		for _, k := range keys {
			if strings.HasSuffix(k.Value, entity+"Request") && index[k.Value] > ei {
				p.add("WARN", "O06", openapiPath, k.Line, "%s は %s より前に置く（集約ごとに <動詞><集約>Request → <集約> の順）", k.Value, entity)
			}
		}
	}

	dtoFile := handlerDir + "/dto.go"
	for _, d := range p.dtos() {
		sname := schemaNameFor(d.name)
		schema := mapGet(schemas, sname)
		if schema == nil {
			p.add("ERROR", "O07", dtoFile, d.line, "%s に対応するスキーマ %s が openapi.yaml にない", d.name, sname)
			continue
		}
		props := mapGet(schema, "properties")
		propSet := map[string]bool{}
		for _, k := range mapKeys(props) {
			propSet[k.Value] = true
		}
		tagSet := map[string]bool{}
		for _, f := range d.fields {
			tagSet[f.json] = true
			if !propSet[f.json] {
				p.add("ERROR", "O07", dtoFile, f.line, "%s の json タグ %q がスキーマ %s の properties にない", d.name, f.json, sname)
			}
		}
		for _, k := range mapKeys(props) {
			if !tagSet[k.Value] {
				p.add("ERROR", "O07", openapiPath, k.Line, "スキーマ %s のプロパティ %q が %s の json タグにない", sname, k.Value, d.name)
			}
		}

		required := map[string]bool{}
		for _, r := range seqValues(mapGet(schema, "required")) {
			required[r] = true
		}
		isResponse := strings.HasSuffix(d.name, "Response")
		for _, f := range d.fields {
			prop := mapGet(props, f.json)
			if prop == nil {
				continue
			}
			if isResponse && !required[f.json] {
				p.add("ERROR", "O07", openapiPath, prop.Line, "レスポンス %s のプロパティ %q を required に入れる（レスポンスは全プロパティを required にする）", sname, f.json)
			}
			if strings.TrimPrefix(f.typ, "*") == "time.Time" {
				if fm := mapGet(prop, "format"); fm == nil || fm.Value != "date-time" {
					p.add("ERROR", "O07", openapiPath, prop.Line, "%s.%s は日時なので format: date-time にする", sname, f.json)
				}
			}
		}
		if !isResponse {
			p.checkRequestConstraints(sname, props)
		}
	}
}

// checkRequestConstraints は、リクエストのスキーマに domain と同じ制約が書かれているかを見る（O08）。
func (p *project) checkRequestConstraints(sname string, props *yaml.Node) {
	base := strings.TrimSuffix(sname, "Request")
	agg := ""
	for _, a := range p.aggs {
		if strings.HasSuffix(base, exportName(a)) && len(a) > len(agg) {
			agg = a
		}
	}
	consts := map[string]int{}
	if agg != "" {
		consts = p.domainConsts(agg)
	}
	for _, k := range mapKeys(props) {
		prop := mapGet(props, k.Value)
		typ := mapGet(prop, "type")
		if typ == nil {
			continue
		}
		c := camel(k.Value)
		switch typ.Value {
		case "string":
			if v, ok := consts["max"+c+"Length"]; ok {
				ml := mapGet(prop, "maxLength")
				if ml == nil {
					p.add("ERROR", "O08", openapiPath, k.Line, "%s.%s に maxLength: %d がない（domain の max%sLength と同じにする）", sname, k.Value, v, c)
				} else if ml.Value != strconv.Itoa(v) {
					p.add("ERROR", "O08", openapiPath, k.Line, "%s.%s の maxLength %s が domain の max%sLength（%d）と違う", sname, k.Value, ml.Value, c, v)
				}
			}
		case "integer", "number":
			for _, b := range []struct{ key, cname string }{{"minimum", "min" + c}, {"maximum", "max" + c}} {
				n := mapGet(prop, b.key)
				if n == nil {
					p.add("ERROR", "O08", openapiPath, k.Line, "%s.%s に %s がない（domain と同じ範囲を書く）", sname, k.Value, b.key)
					continue
				}
				if v, ok := consts[b.cname]; ok && n.Value != strconv.Itoa(v) {
					p.add("ERROR", "O08", openapiPath, k.Line, "%s.%s の %s %s が domain の %s（%d）と違う", sname, k.Value, b.key, n.Value, b.cname, v)
				}
			}
		}
	}
}

func (p *project) checkErrorCodes(schemas *yaml.Node) {
	code := mapGet(mapGet(mapGet(mapGet(mapGet(mapGet(schemas, "Error"), "properties"), "error"), "properties"), "code"), "enum")
	if code == nil {
		return
	}
	enum := map[string]bool{}
	for _, v := range seqValues(code) {
		enum[v] = true
	}
	used := map[string]bool{"internal": true}
	for _, m := range p.errorMappings() {
		used[m.code] = true
		if m.code != "" && !enum[m.code] {
			p.add("ERROR", "H02", handlerDir+"/error.go", m.line, "code %q が openapi.yaml の Error の code の enum にない", m.code)
		}
	}
	for v := range enum {
		if !used[v] {
			p.add("WARN", "H02", openapiPath, code.Line, "Error の code の enum %q は errorMappings で使われていない", v)
		}
	}
}
