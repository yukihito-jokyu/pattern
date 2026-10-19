package main

import (
	"regexp"
	"sort"
	"strings"
)

var nolintRe = regexp.MustCompile(`//\s*nolint`)

// nolintAllowed は、もともとテンプレートにある nolint（理由が docs に書かれているもの）。
var nolintAllowed = map[string]string{
	"internal/adapter/repository/db.go": "nolint:ireturn",
}

func (p *project) checkLintConfig() {
	cfg, ok := p.readText(".golangci.yml")
	if !ok {
		p.add("ERROR", "L01", ".golangci.yml", 0, ".golangci.yml がない")
		return
	}
	for _, agg := range p.aggs {
		entity := exportName(agg)
		if !strings.Contains(cfg, "^"+agg+`\.`+entity+"$") {
			p.add("ERROR", "L01", ".golangci.yml", 0, "forbidigo に集約 %s のパターン ^%s\\.%s$ がない（他の集約から ID だけで参照させる）", agg, agg, entity)
		}
		if !strings.Contains(cfg, "path: internal/domain/"+agg+"/") {
			p.add("ERROR", "L01", ".golangci.yml", 0, "exclusions に path: internal/domain/%s/ の除外がない（自分の集約のエンティティは使ってよい）", agg)
		}
	}

	var paths []string
	for rel := range p.files {
		paths = append(paths, rel)
	}
	sort.Strings(paths)
	for _, rel := range paths {
		f := p.files[rel]
		for _, cg := range f.ast.Comments {
			for _, c := range cg.List {
				if !nolintRe.MatchString(c.Text) {
					continue
				}
				if allow, ok := nolintAllowed[rel]; ok && strings.Contains(c.Text, allow) {
					continue
				}
				p.add("WARN", "L02", rel, p.line(c.Pos()), "%s で lint を黙らせている（設定や nolint で黙らせず、コードを直す）", strings.TrimSpace(c.Text))
			}
		}
	}
}
