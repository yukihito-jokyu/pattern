package main

import (
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

const migrationDir = "db/migrations"

type column struct {
	name     string
	typ      string
	notNull  bool
	pk       bool
	unique   bool
	fk       string // 参照先テーブル
	onDelete bool
	check    string
	varchar  int // VARCHAR(n) の n
	min, max *int
	line     int
}

type table struct {
	name    string
	file    string
	cols    []*column
	indexed map[string]bool
}

func (t *table) hasUnique() bool {
	for _, c := range t.cols {
		if c.unique {
			return true
		}
	}
	return false
}

func (t *table) hasFK() bool {
	for _, c := range t.cols {
		if c.fk != "" {
			return true
		}
	}
	return false
}

var (
	migFileRe     = regexp.MustCompile(`^(\d+)_(\w+)\.(up|down)\.sql$`)
	createTableRe = regexp.MustCompile(`(?i)CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\(`)
	createIndexRe = regexp.MustCompile(`(?is)CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s+ON\s+(\w+)\s*\(([^)]*)\)`)
	colHeadRe     = regexp.MustCompile(`^\s*(\w+)\s+([A-Za-z]+(?:\s*\(\s*\d+(?:\s*,\s*\d+)?\s*\))?)`)
	referencesRe  = regexp.MustCompile(`(?i)REFERENCES\s+(\w+)`)
	checkRe       = regexp.MustCompile(`(?is)CHECK\s*\((.*)\)`)
	varcharRe     = regexp.MustCompile(`^VARCHAR\((\d+)\)$`)
	dropTableRe   = regexp.MustCompile(`(?i)^DROP\s+TABLE\s+IF\s+EXISTS\s+(\w+)$`)
	uniqueRe      = regexp.MustCompile(`(?i)\bUNIQUE\b`)
	allowedTypes  = map[string]bool{"UUID": true, "TIMESTAMPTZ": true, "INTEGER": true, "BOOLEAN": true}
)

func (p *project) checkMigrations() {
	entries, err := os.ReadDir(filepath.Join(p.root, migrationDir))
	if err != nil {
		return
	}
	pairs := map[string]map[string]string{} // 番号_名前 → up/down → ファイル名
	var keys []string
	for _, e := range entries {
		m := migFileRe.FindStringSubmatch(e.Name())
		if m == nil {
			continue
		}
		key := m[1] + "_" + m[2]
		if pairs[key] == nil {
			pairs[key] = map[string]string{}
			keys = append(keys, key)
		}
		pairs[key][m[3]] = e.Name()
	}
	sort.Strings(keys)

	for _, key := range keys {
		for _, dir := range []string{"up", "down"} {
			if pairs[key][dir] == "" {
				p.add("ERROR", "M01", migrationDir+"/"+key+"."+dir+".sql", 0, "%s の %s がない（up と down は必ず対で作る）", key, dir)
			}
		}
		if pairs[key]["up"] == "" {
			continue
		}
		created := p.parseUp(migrationDir+"/"+pairs[key]["up"], key)
		if pairs[key]["down"] != "" && len(created) > 0 {
			p.checkDown(migrationDir+"/"+pairs[key]["down"], created)
		}
	}
}

func lineAt(s string, off int) int { return strings.Count(s[:off], "\n") + 1 }

func stripSQLComments(s string) string {
	var b strings.Builder
	for _, l := range strings.Split(s, "\n") {
		if i := strings.Index(l, "--"); i >= 0 {
			l = l[:i] + strings.Repeat(" ", len(l)-i)
		}
		b.WriteString(l)
		b.WriteString("\n")
	}
	return strings.TrimSuffix(b.String(), "\n")
}

func (p *project) parseUp(rel, key string) []string {
	raw, ok := p.readText(rel)
	if !ok {
		return nil
	}
	src := stripSQLComments(raw)
	var created []string

	for _, loc := range createTableRe.FindAllStringSubmatchIndex(src, -1) {
		name := strings.ToLower(src[loc[2]:loc[3]])
		open := loc[1] - 1
		end := matchParen(src, open)
		if end < 0 {
			continue
		}
		t := &table{name: name, file: rel, indexed: map[string]bool{}}
		for _, item := range splitTopLevel(src, open+1, end) {
			p.parseColumn(t, src, item[0], item[1])
		}
		p.tables[name] = t
		created = append(created, name)
	}

	for _, m := range createIndexRe.FindAllStringSubmatch(src, -1) {
		if t := p.tables[strings.ToLower(m[2])]; t != nil {
			first := strings.ToLower(strings.TrimSpace(strings.Split(m[3], ",")[0]))
			t.indexed[first] = true
			if want := t.name + "_" + first + "_idx"; m[1] != want {
				p.add("WARN", "M06", rel, 0, "インデックス名 %s は %s にする", m[1], want)
			}
		}
	}

	if len(created) > 1 {
		p.add("WARN", "M03", rel, 0, "1 つのマイグレーションで 1 つのテーブルを作る（%s）", strings.Join(created, ", "))
	}
	if len(created) == 1 {
		if name := key[strings.Index(key, "_")+1:]; name != "create_"+created[0] {
			p.add("WARN", "M03", rel, 0, "マイグレーション名は create_%s にする（今は %s）", created[0], name)
		}
	}

	for _, name := range created {
		p.checkTable(p.tables[name])
	}
	return created
}

func matchParen(s string, open int) int {
	depth := 0
	for i := open; i < len(s); i++ {
		switch s[i] {
		case '(':
			depth++
		case ')':
			depth--
			if depth == 0 {
				return i
			}
		}
	}
	return -1
}

// splitTopLevel は s[from:to] を括弧の外のカンマで区切り、各要素の [開始, 終了) を返す。
func splitTopLevel(s string, from, to int) [][2]int {
	var out [][2]int
	depth, start := 0, from
	for i := from; i < to; i++ {
		switch s[i] {
		case '(':
			depth++
		case ')':
			depth--
		case ',':
			if depth == 0 {
				out = append(out, [2]int{start, i})
				start = i + 1
			}
		}
	}
	return append(out, [2]int{start, to})
}

func (p *project) parseColumn(t *table, src string, from, to int) {
	item := src[from:to]
	trimmed := strings.TrimSpace(item)
	if trimmed == "" {
		return
	}
	line := lineAt(src, from+strings.Index(item, trimmed))
	upper := strings.ToUpper(trimmed)
	for _, kw := range []string{"CONSTRAINT", "PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CHECK"} {
		if strings.HasPrefix(upper, kw) {
			if kw == "FOREIGN KEY" || (kw == "CONSTRAINT" && strings.Contains(upper, "FOREIGN KEY")) {
				p.add("WARN", "M05", t.file, line, "外部キーは列の定義に REFERENCES <テーブル> (id) ON DELETE ... で書く")
			}
			if strings.Contains(upper, "UNIQUE") {
				// 表制約の UNIQUE も一意制約として数える
				t.cols = append(t.cols, &column{name: "(" + trimmed + ")", unique: true, notNull: true, typ: "CONSTRAINT", line: line})
			}
			return
		}
	}
	m := colHeadRe.FindStringSubmatch(trimmed)
	if m == nil {
		return
	}
	c := &column{
		name:    strings.ToLower(m[1]),
		typ:     strings.ToUpper(strings.Join(strings.Fields(m[2]), "")),
		notNull: strings.Contains(upper, "NOT NULL"),
		pk:      strings.Contains(upper, "PRIMARY KEY"),
		unique:  uniqueRe.MatchString(upper),
		line:    line,
	}
	if r := referencesRe.FindStringSubmatch(trimmed); r != nil {
		c.fk = strings.ToLower(r[1])
		c.onDelete = strings.Contains(upper, "ON DELETE")
	}
	if ck := checkRe.FindStringSubmatch(trimmed); ck != nil {
		c.check = ck[1]
		c.min, c.max = checkBounds(ck[1], c.name)
	}
	if v := varcharRe.FindStringSubmatch(c.typ); v != nil {
		c.varchar, _ = strconv.Atoi(v[1])
	}
	t.cols = append(t.cols, c)
}

func checkBounds(expr, col string) (minV, maxV *int) {
	q := regexp.QuoteMeta(col)
	if m := regexp.MustCompile(`(?i)\b` + q + `\s*>=\s*(-?\d+)`).FindStringSubmatch(expr); m != nil {
		v, _ := strconv.Atoi(m[1])
		minV = &v
	} else if m := regexp.MustCompile(`(?i)\b` + q + `\s*>\s*(-?\d+)`).FindStringSubmatch(expr); m != nil {
		v, _ := strconv.Atoi(m[1])
		v++
		minV = &v
	}
	if m := regexp.MustCompile(`(?i)\b` + q + `\s*<=\s*(-?\d+)`).FindStringSubmatch(expr); m != nil {
		v, _ := strconv.Atoi(m[1])
		maxV = &v
	} else if m := regexp.MustCompile(`(?i)\b` + q + `\s*<\s*(-?\d+)`).FindStringSubmatch(expr); m != nil {
		v, _ := strconv.Atoi(m[1])
		v--
		maxV = &v
	}
	return minV, maxV
}

func (p *project) checkTable(t *table) {
	agg := p.aggForTable(t.name)
	consts := map[string]int{}
	if agg != "" {
		consts = p.domainConsts(agg)
	}
	for _, c := range t.cols {
		if c.typ == "CONSTRAINT" {
			continue
		}
		if !c.notNull && !c.pk {
			p.add("ERROR", "M04", t.file, c.line, "列 %s に NOT NULL がない（列はすべて NOT NULL にする）", c.name)
		}
		if !allowedTypes[c.typ] && c.varchar == 0 {
			p.add("WARN", "M07", t.file, c.line, "列 %s の型 %s は決まりの型（UUID / VARCHAR(n) / INTEGER / TIMESTAMPTZ）ではない", c.name, c.typ)
		}
		if c.fk != "" {
			if !c.onDelete {
				p.add("ERROR", "M05", t.file, c.line, "外部キー %s に ON DELETE がない（省略せず RESTRICT か CASCADE を書く）", c.name)
			}
			if !t.indexed[c.name] {
				p.add("ERROR", "M06", t.file, c.line, "外部キー %s にインデックスがない（CREATE INDEX %s_%s_idx ON %s (%s);）", c.name, t.name, c.name, t.name, c.name)
			}
		}
		if c.typ == "INTEGER" {
			switch {
			case c.check == "":
				p.add("ERROR", "M08", t.file, c.line, "INTEGER 列 %s に CHECK がない（domain の範囲を CHECK でも書く）", c.name)
			case c.max == nil:
				p.add("ERROR", "M08", t.file, c.line, "INTEGER 列 %s の CHECK に上限がない", c.name)
			}
			if v, ok := consts["max"+camel(c.name)]; ok && c.max != nil && v != *c.max {
				p.add("ERROR", "M09", t.file, c.line, "%s の上限が domain（max%s = %d）と CHECK（%d）で違う", c.name, camel(c.name), v, *c.max)
			}
			if v, ok := consts["min"+camel(c.name)]; ok && c.min != nil && v != *c.min {
				p.add("ERROR", "M09", t.file, c.line, "%s の下限が domain（min%s = %d）と CHECK（%d）で違う", c.name, camel(c.name), v, *c.min)
			}
		}
		if c.varchar > 0 {
			if v, ok := consts["max"+camel(c.name)+"Length"]; ok && v != c.varchar {
				p.add("ERROR", "M09", t.file, c.line, "%s の長さが domain（max%sLength = %d）と VARCHAR(%d) で違う", c.name, camel(c.name), v, c.varchar)
			}
		}
	}
}

func (p *project) checkDown(rel string, created []string) {
	raw, ok := p.readText(rel)
	if !ok {
		return
	}
	src := stripSQLComments(raw)
	dropped := map[string]bool{}
	for _, stmt := range strings.Split(src, ";") {
		s := strings.Join(strings.Fields(stmt), " ")
		if s == "" {
			continue
		}
		m := dropTableRe.FindStringSubmatch(s)
		if m == nil {
			p.add("ERROR", "M02", rel, 0, "down は DROP TABLE IF EXISTS <テーブル>; だけを書く（%q）", s)
			continue
		}
		dropped[strings.ToLower(m[1])] = true
	}
	for _, t := range created {
		if !dropped[t] {
			p.add("ERROR", "M02", rel, 0, "up で作った %s を down で DROP TABLE IF EXISTS %s; していない", t, t)
		}
	}
}
