// Command archcheck は golangci-lint で表せない go-cli の規則を検査する。
//
// カレントディレクトリ以下の Go ファイルを解析し、違反を <rule ID> <path>:<line> <message> で表示して終了コード1で終了する。
// 規則は docs/design/rules.md にあり、このファイルの表は規約と docs/design/architecture.md の表に対応する。
package main

import (
	"cmp"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"io/fs"
	"os"
	"path"
	"regexp"
	"slices"
	"strconv"
	"strings"
	"unicode"
)

// sourceFile は解析済みの Go ファイルを表す。
type sourceFile struct {
	path   string
	dir    string
	name   string
	place  place
	test   bool
	syntax *ast.File
	src    []byte
}

// place はディレクトリが属する層と名詞を表す。
type place struct {
	layer string
	noun  string
}

// nounDir はディレクトリのパターンと層を対応付ける。
type nounDir struct {
	layer  string
	prefix string
	suffix string
}

// violation は1件の規約違反を表す。
type violation struct {
	rule string
	path string
	line int
	msg  string
}

// fieldList は構造体のフィールド名を保持する。
type fieldList struct {
	file  *sourceFile
	pos   token.Pos
	names []string
}

// envConst は GOCLI_ 環境変数の名前を値に持つ定数を表す。
type envConst struct {
	name    string
	value   string
	pos     token.Pos
	doc     bool
	grouped bool
	late    bool
}

// declDoc はトップレベルの宣言名と説明を保持する。
type declDoc struct {
	name string
	doc  string
	pos  token.Pos
}

// checker は解析済みのモジュールと検出した違反を保持する。
type checker struct {
	fsys   fs.FS
	fset   *token.FileSet
	files  []*sourceFile
	others []string
	found  []violation
}

const (
	modulePath = "example.com/go-cli"
	maxASCII   = 0x7f
	goMod      = "go.mod"
	lintMod    = "golangci-lint.mod"
)

const (
	layerMain    = "main"
	layerApp     = "app"
	layerAppTest = "apptest"
	layerCLI     = "cli"
	layerCommand = "command"
	layerDomain  = "domain"
	layerAdapter = "adapter"
	layerErrKind = "errkind"
	layerTools   = "tools"
)

func main() {
	c := &checker{fsys: os.DirFS("."), fset: token.NewFileSet()}
	err := fs.WalkDir(c.fsys, ".", c.visit)
	if err != nil {
		fmt.Fprintln(os.Stderr, "archcheck:", err)
		os.Exit(1)
	}
	for _, check := range checks() {
		check(c)
	}
	fmt.Print(c.report())
	if len(c.found) > 0 {
		os.Exit(1)
	}
}

func (c *checker) visit(p string, d fs.DirEntry, err error) error {
	if err != nil {
		return err
	}
	if d.IsDir() {
		return skipDir(p, d.Name())
	}
	if !strings.HasSuffix(p, ".go") {
		if strings.HasPrefix(p, "internal/") || strings.HasPrefix(p, "tools/") {
			c.others = append(c.others, p)
		}
		return nil
	}
	return c.parse(p)
}

func (c *checker) parse(p string) error {
	src, err := fs.ReadFile(c.fsys, p)
	if err != nil {
		return fmt.Errorf("read %s: %w", p, err)
	}
	syntax, err := parser.ParseFile(c.fset, p, src, parser.ParseComments)
	if err != nil {
		return fmt.Errorf("parse %s: %w", p, err)
	}
	dir := path.Dir(p)
	c.files = append(c.files, &sourceFile{
		path:   p,
		dir:    dir,
		name:   path.Base(p),
		place:  placeOf(dir),
		test:   strings.HasSuffix(p, "_test.go"),
		syntax: syntax,
		src:    src,
	})
	return nil
}

// report は違反をパス順で1行ずつ返す。
func (c *checker) report() string {
	slices.SortFunc(c.found, func(a, b violation) int {
		return strings.Compare(fmt.Sprintf("%s:%06d %s", a.path, a.line, a.rule),
			fmt.Sprintf("%s:%06d %s", b.path, b.line, b.rule))
	})
	var b strings.Builder
	for _, v := range c.found {
		fmt.Fprintf(&b, "%s %s:%d %s\n", v.rule, v.path, v.line, v.msg)
	}
	return b.String()
}

func (c *checker) at(rule string, f *sourceFile, pos token.Pos, msg string) {
	line := 1
	if pos.IsValid() {
		line = c.fset.Position(pos).Line
	}
	c.found = append(c.found, violation{rule: rule, path: f.path, line: line, msg: msg})
}

func (c *checker) atLine(rule, p string, line int, msg string) {
	c.found = append(c.found, violation{rule: rule, path: p, line: line, msg: msg})
}

// sources は指定した層のテスト以外のファイルを返す。
func (c *checker) sources(layer string) []*sourceFile {
	var files []*sourceFile
	for _, f := range c.files {
		if f.place.layer == layer && !f.test {
			files = append(files, f)
		}
	}
	return files
}

func (c *checker) file(p string) *sourceFile {
	for _, f := range c.files {
		if f.path == p {
			return f
		}
	}
	return nil
}

// nouns は指定した層にファイルがある名詞をソートして返す。
func (c *checker) nouns(layer string) []string {
	var nouns []string
	for _, f := range c.files {
		if f.place.layer == layer && !slices.Contains(nouns, f.place.noun) {
			nouns = append(nouns, f.place.noun)
		}
	}
	slices.Sort(nouns)
	return nouns
}

func checks() []func(*checker) {
	return []func(*checker){
		(*checker).checkLayout,
		(*checker).checkNounSets,
		(*checker).checkFileNames,
		(*checker).checkTests,
		(*checker).checkMain,
		(*checker).checkImports,
		(*checker).checkExports,
		(*checker).checkModFiles,
		(*checker).checkCommandFiles,
		(*checker).checkDomainAndAdapter,
		(*checker).checkFieldsMatch,
		(*checker).checkApp,
		(*checker).checkDocs,
		(*checker).checkSyntax,
	}
}

// checkLayout は STR-01 と NAM-01 を検査する。
func (c *checker) checkLayout() {
	for _, f := range c.files {
		if !isLowerPath(f.dir) {
			c.at("NAM-01", f, token.NoPos, "directory names must be lowercase letters and digits: "+f.dir)
		}
		if f.place.layer == "" {
			c.at("STR-01", f, token.NoPos, "Go files must be in one of the directories of STR-01, not "+f.dir)
			continue
		}
		if f.place.layer == layerMain && f.name != "main.go" {
			c.at("STR-01", f, token.NoPos, "the root directory holds only main.go")
		}
	}
	for _, p := range c.others {
		c.atLine("STR-01", p, 1, "only Go files may be under internal/ and tools/")
	}
}

// checkNounSets は名詞ごとに domain・adapter・command がそろうことを検査する（STR-02）。
func (c *checker) checkNounSets() {
	layers := []string{layerDomain, layerAdapter, layerCommand}
	all := slices.Concat(c.nouns(layerDomain), c.nouns(layerAdapter), c.nouns(layerCommand))
	slices.Sort(all)
	for _, noun := range slices.Compact(all) {
		for _, layer := range layers {
			if !slices.Contains(c.nouns(layer), noun) {
				c.atLine("STR-02", nounDirOf(layer, noun), 1, "noun "+strconv.Quote(noun)+" has no package here")
			}
		}
	}
}

// checkFileNames はディレクトリ内のテスト以外のファイル名を検査する（STR-03）。
func (c *checker) checkFileNames() {
	present := make(map[string][]string)
	for _, f := range c.files {
		if f.test || f.place.layer == "" {
			continue
		}
		present[f.dir] = append(present[f.dir], f.name)
		allowed := allowedFileNames(f.place)
		if allowed != nil && !slices.Contains(allowed, f.name) {
			c.at("STR-03", f, token.NoPos, "files here must be named one of "+strings.Join(allowed, ", "))
		}
	}
	for dir, names := range present {
		for _, want := range requiredFileNames(placeOf(dir)) {
			if !slices.Contains(names, want) {
				c.atLine("STR-03", dir+"/"+want, 1, "this file is missing")
			}
		}
	}
}

// checkTests は STR-06・TEST-01・TEST-02・TEST-03・TEST-05 を検査する。
func (c *checker) checkTests() {
	for _, f := range c.files {
		if !f.test {
			continue
		}
		subject := strings.TrimSuffix(f.name, "_test.go") + ".go"
		if c.file(path.Join(f.dir, subject)) == nil {
			c.at("STR-06", f, token.NoPos, "a test file must be named after a file in the same directory")
		}
		c.checkTestSyntax(f)
		switch f.place.layer {
		case layerCommand, layerApp:
			c.checkCaseOrder(f, resultRank, "order the cases: success, --json, then exit codes 1, 2 and 3")
		case layerDomain:
			c.checkCaseOrder(f, nameRank, "order the cases: accepts_, returns_, then rejects_")
		}
	}
	for _, noun := range c.nouns(layerDomain) {
		c.requireFile("TEST-01", "internal/domain/"+noun+"/"+noun+"_test.go")
	}
	for _, noun := range c.nouns(layerAdapter) {
		c.requireFile("TEST-01", "internal/adapter/"+noun+"store/"+noun+"store_test.go")
	}
}

func (c *checker) requireFile(rule, p string) {
	if c.file(p) == nil {
		c.atLine(rule, p, 1, "this file is missing")
	}
}

func (c *checker) checkTestSyntax(f *sourceFile) {
	ast.Inspect(f.syntax, func(n ast.Node) bool {
		switch n := n.(type) {
		case *ast.GenDecl:
			if n.Tok == token.TYPE {
				c.at("TEST-03", f, n.Pos(), "do not declare types in tests; use the table and apptest")
			}
		case *ast.KeyValueExpr:
			name := stringValue(n.Value)
			if isIdent(n.Key, "name") && !regexp.MustCompile(`^[a-z0-9]+(_[a-z0-9]+)*$`).MatchString(name) {
				c.at("TEST-02", f, n.Pos(), "subtest names must be snake_case, not "+strconv.Quote(name))
			}
		}
		return true
	})
}

// checkCaseOrder は各テーブルの件が rank の順に並ぶことを検査する（TEST-05）。
func (c *checker) checkCaseOrder(f *sourceFile, rank func(*ast.CompositeLit) int, msg string) {
	ast.Inspect(f.syntax, func(n ast.Node) bool {
		table, ok := n.(*ast.CompositeLit)
		if !ok {
			return true
		}
		_, ok = table.Type.(*ast.ArrayType)
		if !ok {
			return true
		}
		last := -1
		for _, elt := range table.Elts {
			tc, ok := elt.(*ast.CompositeLit)
			if !ok {
				continue
			}
			r := rank(tc)
			if r >= 0 && r < last {
				c.at("TEST-05", f, tc.Pos(), msg)
			}
			last = max(last, r)
		}
		return true
	})
}

// resultRank は成功は0、--json は1、失敗は終了コードに1を足した値、それ以外は -1 を返す。
func resultRank(tc *ast.CompositeLit) int {
	want, ok := field(tc, "want").(*ast.CompositeLit)
	if !ok || exprString(want.Type) != "apptest.Result" {
		return -1
	}
	code, err := strconv.Atoi(literalValue(field(want, "Code")))
	switch {
	case err != nil:
		return -1
	case code == 0 && slices.Contains(stringValues(field(tc, "args")), "--json"):
		return 1
	case code == 0:
		return 0
	}
	return code + 1
}

// nameRank は件名の接頭辞が accepts_・returns_・rejects_ の何番目かを返し、一致しなければ -1 を返す。
func nameRank(tc *ast.CompositeLit) int {
	name := stringValue(field(tc, "name"))
	for i, prefix := range []string{"accepts_", "returns_", "rejects_"} {
		if strings.HasPrefix(name, prefix) {
			return i
		}
	}
	return -1
}

// checkMain は main.go が app.Run を呼んで終了するだけであることを検査する（STR-08）。
func (c *checker) checkMain() {
	f := c.file("main.go")
	if f == nil {
		return
	}
	if !slices.Equal(declNames(f.syntax), []string{"func main"}) {
		c.at("STR-08", f, token.NoPos, "main.go declares only func main")
	}
	allowed := []string{"signal.NotifyContext", "context.Background", "app.Run", "stop", "os.Exit"}
	ast.Inspect(f.syntax, func(n ast.Node) bool {
		call, ok := n.(*ast.CallExpr)
		if ok && !slices.Contains(allowed, exprString(call.Fun)) {
			c.at("STR-08", f, call.Pos(), "main only calls "+strings.Join(allowed, ", "))
		}
		return true
	})
}

// checkImports は DEP-01・DEP-03・DEP-04・DEP-05 を検査する。
func (c *checker) checkImports() {
	for _, f := range c.files {
		if f.place.layer == "" {
			continue
		}
		for _, spec := range f.syntax.Imports {
			c.checkImport(f, spec)
		}
	}
}

func (c *checker) checkImport(f *sourceFile, spec *ast.ImportSpec) {
	p, err := strconv.Unquote(spec.Path.Value)
	if err != nil {
		return
	}
	rel, internal := strings.CutPrefix(p, modulePath+"/")
	switch {
	case internal:
		c.checkInternalImport(f, spec.Pos(), rel)
	case !strings.Contains(strings.Split(p, "/")[0], "."):
		c.checkStdImport(f, spec.Pos(), p)
	default:
		c.at("DEP-04", f, spec.Pos(), "use only the standard library, not "+p)
	}
}

func (c *checker) checkInternalImport(f *sourceFile, pos token.Pos, dir string) {
	to := placeOf(dir)
	if f.test && (dir == f.dir || to.layer == layerAppTest) {
		return
	}
	from := f.place
	if from.layer == to.layer && slices.Contains([]string{layerCommand, layerDomain, layerAdapter}, from.layer) {
		c.at("DEP-03", f, pos, "do not import another noun of the same layer: "+dir)
		return
	}
	allowed := allowedImports()[from.layer]
	if !slices.Contains(allowed, to.layer) || (from.layer == layerAdapter && from.noun != to.noun) {
		c.at("DEP-01", f, pos, from.layer+" must not import "+dir)
	}
}

func (c *checker) checkStdImport(f *sourceFile, pos token.Pos, p string) {
	allowed, restricted := restrictedImports()[p]
	if !restricted || (p == "testing" && f.test) {
		return
	}
	if !slices.Contains(allowed, f.place.layer) {
		c.at("DEP-05", f, pos, p+" may be imported only in: "+strings.Join(allowed, ", "))
	}
}

// checkExports は各層が公開する名前を検査する（DEP-02）。
func (c *checker) checkExports() {
	for _, f := range c.files {
		allowed, restricted := exportedNames()[f.place.layer]
		if f.test || !restricted {
			continue
		}
		for _, name := range declNames(f.syntax) {
			if !isExportedDecl(name) || slices.Contains(allowed, name) {
				continue
			}
			if f.place.layer == layerErrKind && strings.HasPrefix(name, "var Err") {
				continue
			}
			c.at("DEP-02", f, token.NoPos, "do not export "+name+"; "+f.place.layer+" exports only "+
				strings.Join(allowed, ", "))
		}
	}
}

// checkModFiles は go.mod と golangci-lint.mod の DEP-04・TOOL-04 を検査する。
func (c *checker) checkModFiles() {
	mod := c.readLines(goMod)
	for i, line := range mod {
		if strings.HasPrefix(line, "require") {
			c.atLine("DEP-04", goMod, i+1, "go.mod must not require modules")
		}
	}
	c.requireLine(goMod, mod, "go 1.27")
	c.requireLine(goMod, mod, "toolchain go1.27.2")
	lint := c.readLines(lintMod)
	c.requireLine(lintMod, lint, "go 1.27")
	c.requireLine(lintMod, lint, "tool github.com/golangci/golangci-lint/v2/cmd/golangci-lint")
	c.requireLine(lintMod, lint, "github.com/golangci/golangci-lint/v2 v2.15.0 // indirect")
}

func (c *checker) readLines(p string) []string {
	data, err := fs.ReadFile(c.fsys, p)
	if err != nil {
		c.atLine("TOOL-04", p, 1, "cannot read the file")
		return nil
	}
	lines := strings.Split(string(data), "\n")
	for i, line := range lines {
		lines[i] = strings.TrimSpace(line)
	}
	return lines
}

func (c *checker) requireLine(p string, lines []string, want string) {
	if !slices.Contains(lines, want) {
		c.atLine("TOOL-04", p, 1, "want the line "+strconv.Quote(want))
	}
}

// checkCommandFiles は command 層のファイルを検査する。
func (c *checker) checkCommandFiles() {
	for _, f := range c.sources(layerCommand) {
		switch f.name {
		case f.place.noun + "cmd.go":
			c.checkGroupFile(f)
		case "view.go":
			c.requireDecls(f, "type "+f.place.noun+"View", "func to"+title(f.place.noun)+"View")
			c.checkViewMethods(f)
		default:
			c.checkVerbFile(f, strings.TrimSuffix(f.name, ".go"))
		}
		c.checkFlags(f)
		c.checkSummaries(f)
	}
}

// checkViewMethods は view のメソッド名と列の見出しの対応を検査する（NAM-03）。
func (c *checker) checkViewMethods(f *sourceFile) {
	for _, decl := range f.syntax.Decls {
		fn, ok := decl.(*ast.FuncDecl)
		if !ok || fn.Recv == nil {
			continue
		}
		header := upperSnake(fn.Name.Name)
		if !c.packageHasString(f.dir, header) {
			c.at("NAM-03", f, fn.Pos(), "name the method after its column header: no header "+strconv.Quote(header))
		}
	}
}

// packageHasString は dir のテスト以外のファイルに文字列リテラル s があるかを返す。
func (c *checker) packageHasString(dir, s string) bool {
	found := false
	for _, f := range c.files {
		if f.dir != dir || f.test {
			continue
		}
		ast.Inspect(f.syntax, func(n ast.Node) bool {
			lit, ok := n.(*ast.BasicLit)
			if ok && stringValue(lit) == s {
				found = true
			}
			return !found
		})
	}
	return found
}

// checkGroupFile は<noun>cmd.go の NAM-03・NAM-06・STR-02 を検査する。
func (c *checker) checkGroupFile(f *sourceFile) {
	if !slices.Equal(declNames(f.syntax), []string{"func New"}) {
		c.at("NAM-03", f, token.NoPos, f.name+" declares only func New")
	}
	lit := literalOf(f.syntax, "cli", "Group")
	if lit == nil {
		c.at("NAM-03", f, token.NoPos, "New returns a &cli.Group{...} literal")
		return
	}
	name := stringValue(field(lit, "Name"))
	if name != f.place.noun {
		c.at("NAM-06", f, lit.Pos(), "the group name must be the noun "+strconv.Quote(f.place.noun))
	}
	if !slices.IsSorted(calledNames(field(lit, "Commands"))) {
		c.at("STR-02", f, lit.Pos(), "list the commands in alphabetical order")
	}
}

func (c *checker) checkVerbFile(f *sourceFile, verb string) {
	v := title(verb)
	want := []string{
		"type " + verb + "Options", "type " + verb + "Output", "func new" + v, "func run" + v,
		"method " + verb + "Output.WriteText",
	}
	got := declNames(f.syntax)
	if !slices.Equal(got, want) {
		c.at("STR-04", f, token.NoPos, "want the declarations "+strings.Join(want, ", ")+
			" in this order, got "+strings.Join(got, ", "))
	}
	c.checkCommandLiteral(f, verb)
	c.checkRun(f, verb)
	test := c.file(path.Join(f.dir, verb+"_test.go"))
	if test == nil || findFunc(test.syntax, "Test"+v) == nil {
		c.atLine("TEST-01", path.Join(f.dir, verb+"_test.go"), 1, "want func Test"+v+" for the command "+verb)
	}
}

// checkCommandLiteral は new<Verb> の cli.Command を検査する（STR-04・NAM-04・NAM-06・CODE-02）。
func (c *checker) checkCommandLiteral(f *sourceFile, verb string) {
	fn := findFunc(f.syntax, "new"+title(verb))
	if fn == nil {
		return
	}
	lit := literalOf(fn, "cli", "Command")
	if lit == nil {
		c.at("STR-04", f, fn.Pos(), "new"+title(verb)+" returns a &cli.Command{...} literal")
		return
	}
	if slices.Contains(forbiddenVerbs(), verb) {
		c.at("NAM-04", f, lit.Pos(), "use the verb of the NAM-04 table instead of "+strconv.Quote(verb))
	}
	name := stringValue(field(lit, "Name"))
	if name != verb {
		c.at("NAM-04", f, lit.Pos(), "the command name "+strconv.Quote(name)+" must equal the file name "+verb)
	}
	call := onlyReturnedCall(field(lit, "Run"))
	if call == nil || !isIdent(call.Fun, "run"+title(verb)) {
		c.at("STR-04", f, lit.Pos(), "Run must only return run"+title(verb)+"(ctx, svc, opts)")
	}
	c.checkArgs(f, field(lit, "Args"))
}

func (c *checker) checkArgs(f *sourceFile, args ast.Expr) {
	if args == nil {
		return
	}
	ast.Inspect(args, func(n ast.Node) bool {
		kv, ok := n.(*ast.KeyValueExpr)
		switch {
		case !ok:
		case isIdent(kv.Key, "Name") && !isKebab(stringValue(kv.Value)):
			c.at("NAM-06", f, kv.Pos(), "argument names must be kebab-case")
		case isIdent(kv.Key, "Value") && !isOptsField(kv.Value):
			c.at("CODE-02", f, kv.Pos(), "bind the argument to a field of opts: &opts.<field>")
		}
		return true
	})
}

// checkRun は run<Verb> の NAM-04・NAM-05 を検査する。
func (c *checker) checkRun(f *sourceFile, verb string) {
	fn := findFunc(f.syntax, "run"+title(verb))
	if fn == nil {
		return
	}
	want := resultName(verb, f.place.noun)
	called := false
	ast.Inspect(fn.Body, func(n ast.Node) bool {
		as, ok := n.(*ast.AssignStmt)
		if !ok || len(as.Rhs) != 1 || !isMethodCall(as.Rhs[0], title(verb)) {
			return true
		}
		called = true
		if identName(as.Lhs[0]) != want {
			c.at("NAM-05", f, as.Pos(), "name the result of "+title(verb)+" "+strconv.Quote(want))
		}
		return true
	})
	if !called {
		c.at("NAM-04", f, fn.Pos(), "run"+title(verb)+" must call the Service method "+title(verb))
	}
}

// checkFlags はコマンドのフラグについて CODE-02・NAM-06・OPS-06 を検査する。
func (c *checker) checkFlags(f *sourceFile) {
	ast.Inspect(f.syntax, func(n ast.Node) bool {
		switch n := n.(type) {
		case *ast.Field:
			if exprString(n.Type) == "*flag.FlagSet" && (len(n.Names) != 1 || n.Names[0].Name != "fs") {
				c.at("CODE-02", f, n.Pos(), "name the *flag.FlagSet parameter fs")
			}
		case *ast.CallExpr:
			c.checkFlagCall(f, n)
		}
		return true
	})
}

func (c *checker) checkFlagCall(f *sourceFile, call *ast.CallExpr) {
	sel, ok := call.Fun.(*ast.SelectorExpr)
	if !ok || (!isIdent(sel.X, "fs") && !isIdent(sel.X, "flag")) {
		return
	}
	if isIdent(sel.X, "flag") || !slices.Contains([]string{"StringVar", "BoolVar", "IntVar"}, sel.Sel.Name) {
		c.at("CODE-02", f, call.Pos(), "declare flags only with fs.StringVar, fs.BoolVar or fs.IntVar")
		return
	}
	const flagArgs = 4
	if len(call.Args) != flagArgs {
		return
	}
	if !isOptsField(call.Args[0]) {
		c.at("CODE-02", f, call.Pos(), "bind the flag to a field of opts: &opts.<field>")
	}
	name := stringValue(call.Args[1])
	if len(name) < 2 || !isKebab(name) {
		c.at("NAM-06", f, call.Pos(), "flag names must be kebab-case with at least 2 characters, not "+
			strconv.Quote(name))
	}
	if !isSentence(stringValue(call.Args[3])) {
		c.at("OPS-06", f, call.Pos(), "the flag usage must start with an uppercase letter and not end with a period")
	}
}

func (c *checker) checkSummaries(f *sourceFile) {
	ast.Inspect(f.syntax, func(n ast.Node) bool {
		kv, ok := n.(*ast.KeyValueExpr)
		if ok && isIdent(kv.Key, "Summary") && !isSentence(stringValue(kv.Value)) {
			c.at("OPS-06", f, kv.Pos(), "the summary must start with an uppercase letter and not end with a period")
		}
		return true
	})
}

// checkDomainAndAdapter は domain 層と adapter 層の NAM-03 を検査する。
func (c *checker) checkDomainAndAdapter() {
	for _, f := range c.sources(layerDomain) {
		noun := f.place.noun
		switch f.name {
		case noun + ".go":
			c.requireDecls(f, "type "+title(noun))
		case "service.go":
			c.requireDecls(f, "type Service", "func NewService")
		case "repository.go":
			c.requireDecls(f, "type Repository")
			c.checkRepository(f)
		}
	}
	for _, f := range c.sources(layerAdapter) {
		noun := f.place.noun
		c.requireDecls(f, "type Store", "func New", "type document", "type record", "func toRecord",
			"func to"+title(noun))
	}
}

func (c *checker) requireDecls(f *sourceFile, want ...string) {
	got := declNames(f.syntax)
	for _, name := range want {
		if !slices.Contains(got, name) {
			c.at("NAM-03", f, token.NoPos, "want the declaration "+name)
		}
	}
}

func (c *checker) checkRepository(f *sourceFile) {
	ast.Inspect(f.syntax, func(n ast.Node) bool {
		spec, ok := n.(*ast.TypeSpec)
		if !ok || spec.Name.Name != "Repository" {
			return true
		}
		iface, ok := spec.Type.(*ast.InterfaceType)
		if !ok || !slices.Equal(fieldNames(iface.Methods), []string{"Load", "Save"}) {
			c.at("NAM-03", f, spec.Pos(), "Repository is an interface with only Load and Save")
		}
		return false
	})
}

// checkFieldsMatch はエンティティ・record・view のフィールドが同じ順に並ぶことを検査する（PROC-02）。
func (c *checker) checkFieldsMatch() {
	for _, noun := range c.nouns(layerDomain) {
		entity := c.structFields("internal/domain/"+noun+"/"+noun+".go", title(noun))
		record := c.structFields("internal/adapter/"+noun+"store/"+noun+"store.go", "record")
		view := c.structFields("internal/command/"+noun+"cmd/view.go", noun+"View")
		if entity == nil {
			continue
		}
		n := len(entity.names)
		if n == 0 || entity.names[0] != "ID" || entity.names[n-1] != "CreatedAt" {
			c.at(
				"PROC-02",
				entity.file,
				entity.pos,
				"the fields of "+title(noun)+" start with ID and end with CreatedAt",
			)
		}
		for _, other := range []*fieldList{record, view} {
			if other != nil && !slices.Equal(other.names, entity.names) {
				c.at("PROC-02", other.file, other.pos, "want the fields of "+title(noun)+" in the same order: "+
					strings.Join(entity.names, ", "))
			}
		}
	}
}

func (c *checker) structFields(p, typeName string) *fieldList {
	f := c.file(p)
	if f == nil {
		return nil
	}
	var found *fieldList
	ast.Inspect(f.syntax, func(n ast.Node) bool {
		spec, ok := n.(*ast.TypeSpec)
		if !ok || spec.Name.Name != typeName {
			return found == nil
		}
		st, ok := spec.Type.(*ast.StructType)
		if ok {
			found = &fieldList{file: f, pos: spec.Pos(), names: fieldNames(st.Fields)}
		}
		return false
	})
	return found
}

// checkApp は app パッケージの PROC-02・STR-02・NAM-06 を検査する。
func (c *checker) checkApp() {
	f := c.file("internal/app/app.go")
	if f != nil {
		var groups []string
		ast.Inspect(f.syntax, func(n ast.Node) bool {
			kv, ok := n.(*ast.KeyValueExpr)
			if ok && isIdent(kv.Key, "Groups") {
				groups = calledNames(kv.Value)
			}
			return true
		})
		for _, noun := range c.nouns(layerCommand) {
			if !slices.Contains(groups, noun+"cmd.New") {
				c.at("PROC-02", f, token.NoPos, "register "+noun+"cmd.New in Groups")
			}
		}
		if !slices.IsSorted(groups) {
			c.at("STR-02", f, token.NoPos, "list the groups in alphabetical order")
		}
	}
	config := c.file("internal/app/config.go")
	if config != nil {
		c.checkEnvNames(config)
		c.checkConfig(config)
	}
}

// checkConfig は GOCLI_ 変数に env<Name>・config のフィールド・load<Name> がそろうことを検査する（NAM-03・OPS-02）。
func (c *checker) checkConfig(f *sourceFile) {
	fields := c.structFields(f.path, "config")
	if fields == nil {
		c.at("OPS-02", f, token.NoPos, "want the type config")
		return
	}
	var order []string
	for _, env := range gocliConsts(f.syntax) {
		base := mixedCaps(strings.TrimPrefix(env.value, "GOCLI_"))
		order = append(order, lowerFirst(base))
		switch {
		case env.name != "env"+base:
			c.at("NAM-03", f, env.pos, "name the constant of "+env.value+" env"+base)
		case env.doc || !env.grouped:
			c.at(
				"NAM-03",
				f,
				env.pos,
				"put env"+base+" in the const group of the environment variables without its own comment",
			)
		case findFunc(f.syntax, "load"+base) == nil:
			c.at("NAM-03", f, env.pos, "want func load"+base+" that reads "+env.value)
		case !slices.Contains(fields.names, lowerFirst(base)):
			c.at("NAM-03", f, env.pos, "want the field "+lowerFirst(base)+" in config")
		case env.late:
			c.at("OPS-02", f, env.pos, "put the GOCLI_ constants before the other constants of the group")
		}
	}
	inFields := slices.DeleteFunc(
		slices.Clone(fields.names),
		func(name string) bool { return !slices.Contains(order, name) },
	)
	if !slices.Equal(order, inFields) {
		c.at("OPS-02", f, fields.pos, "list the GOCLI_ constants in the order of the fields of config")
	}
	c.checkLoadConfig(f, fields.names)
}

// checkLoadConfig は loadConfig が config のフィールド順に load<Name> を1回ずつ呼ぶことを検査する（OPS-02）。
func (c *checker) checkLoadConfig(f *sourceFile, fields []string) {
	fn := findFunc(f.syntax, "loadConfig")
	if fn == nil {
		c.at("OPS-02", f, token.NoPos, "want func loadConfig")
		return
	}
	want := make([]string, 0, len(fields))
	for _, name := range fields {
		want = append(want, "load"+title(name))
	}
	var got []string
	ast.Inspect(fn.Body, func(n ast.Node) bool {
		call, ok := n.(*ast.CallExpr)
		if ok && strings.HasPrefix(identName(call.Fun), "load") {
			got = append(got, identName(call.Fun))
		}
		return true
	})
	if !slices.Equal(got, want) {
		c.at(
			"OPS-02",
			f,
			fn.Pos(),
			"loadConfig calls one load function per field of config in order: "+strings.Join(want, ", "),
		)
	}
}

// gocliConsts は f 内で値が GOCLI_ で始まる定数を返す。
func gocliConsts(f *ast.File) []envConst {
	var consts []envConst
	for _, decl := range f.Decls {
		d, ok := decl.(*ast.GenDecl)
		if !ok || d.Tok != token.CONST {
			continue
		}
		other := false
		for _, spec := range d.Specs {
			s, ok := spec.(*ast.ValueSpec)
			if !ok || len(s.Names) != 1 || len(s.Values) != 1 ||
				!strings.HasPrefix(stringValue(s.Values[0]), "GOCLI_") {
				other = true
				continue
			}
			consts = append(consts, envConst{
				name:    s.Names[0].Name,
				value:   stringValue(s.Values[0]),
				pos:     s.Pos(),
				doc:     s.Doc != nil || (!d.Lparen.IsValid() && d.Doc != nil),
				grouped: d.Lparen.IsValid(),
				late:    other,
			})
		}
	}
	return consts
}

// checkDocs は CODE-10 の宣言に定型文の説明があることを検査する。
func (c *checker) checkDocs() {
	for _, f := range c.files {
		if f.test {
			continue
		}
		for _, d := range declDocs(f.syntax) {
			want := docTemplates(f, d.name)
			if want != nil && !slices.Contains(want, d.doc) {
				c.at(
					"CODE-10",
					f,
					d.pos,
					"the comment of "+d.name+" must be "+strconv.Quote(
						"// "+strings.ReplaceAll(want[0], "\n", "\n// "),
					),
				)
			}
		}
	}
}

// declDocs は f のトップレベルの宣言名と説明文を返す。
func declDocs(f *ast.File) []declDoc {
	var docs []declDoc
	for _, decl := range f.Decls {
		switch d := decl.(type) {
		case *ast.FuncDecl:
			docs = append(docs, declDoc{name: funcName(d), doc: docText(d.Doc), pos: d.Pos()})
		case *ast.GenDecl:
			docs = append(docs, genDeclDocs(d)...)
		}
	}
	return docs
}

// genDeclDocs は d の各名前の説明を返し、括弧が無ければ d 全体の説明を使う。
func genDeclDocs(d *ast.GenDecl) []declDoc {
	var docs []declDoc
	outer := d.Doc
	if d.Lparen.IsValid() {
		outer = nil
	}
	for _, spec := range d.Specs {
		switch s := spec.(type) {
		case *ast.TypeSpec:
			docs = append(docs, declDoc{name: "type " + s.Name.Name, doc: docText(cmp.Or(s.Doc, outer)), pos: s.Pos()})
		case *ast.ValueSpec:
			for _, name := range s.Names {
				docs = append(docs, declDoc{
					name: d.Tok.String() + " " + name.Name,
					doc:  docText(cmp.Or(s.Doc, outer)),
					pos:  s.Pos(),
				})
			}
		}
	}
	return docs
}

// docText はコメントの記号と末尾の改行を取り除いた説明文を返す。
func docText(g *ast.CommentGroup) string {
	if g == nil {
		return ""
	}
	return strings.TrimSpace(g.Text())
}

// docTemplates は f の宣言名に対応する CODE-10 の定型文を返し、定型文が無ければ nil を返す。
func docTemplates(f *sourceFile, name string) []string {
	switch f.place.layer {
	case layerCommand:
		return commandDocTemplates(f, name)
	case layerDomain:
		return domainDocTemplates(f.place.noun, name)
	case layerAdapter:
		noun := f.place.noun
		n := title(noun)
		return oneOf(name, map[string]string{
			"type document": "document はデータファイルの内容を表す。",
			"type record":   "record はデータファイルに保存する1件の " + noun + " を表す。",
			"func toRecord": "toRecord は " + n + " を record に変換する。",
			"func to" + n:   "to" + n + " は record を " + n + " に変換する。",
		})
	case layerApp:
		if f.name == "config.go" {
			return configDocTemplates(f, name)
		}
	}
	return nil
}

// commandDocTemplates は command 層の宣言に対応する CODE-10 の定型文を返す。
func commandDocTemplates(f *sourceFile, name string) []string {
	noun := f.place.noun
	n := title(noun)
	verb := strings.TrimSuffix(f.name, ".go")
	v := title(verb)
	method, ok := strings.CutPrefix(name, "method "+noun+"View.")
	if ok {
		return []string{method + " は " + upperSnake(method) + " 列に表示する文字列を返す。"}
	}
	return oneOf(name, map[string]string{
		"func New":                            "New は svc でユースケースを実行する " + noun + " コマンド群を返す。",
		"type " + verb + "Options":            verb + "Options は " + noun + " " + verb + " の引数とフラグを保持する。",
		"type " + verb + "Output":             verb + "Output は " + noun + " " + verb + " の実行結果を表す。",
		"func new" + v:                        "new" + v + " は " + noun + " " + verb + " コマンドを返す。",
		"func run" + v:                        "run" + v + " は " + noun + " " + verb + " を実行する。",
		"method " + verb + "Output.WriteText": "WriteText は cli.Output を実装する。",
		"type " + noun + "View":               noun + "View は " + noun + " コマンドの出力で1件の " + noun + " を表す。",
		"func to" + n + "View":                "to" + n + "View は " + n + " を " + noun + "View に変換する。",
	})
}

// domainDocTemplates は domain 層の宣言に対応する CODE-10 の定型文を返す。
func domainDocTemplates(noun, name string) []string {
	n := title(noun)
	field, ok := strings.CutPrefix(name, "func Parse")
	if ok {
		one := "Parse" + field + " はコマンドライン引数を " + n + " の " + field + " フィールドに変換する。"
		return []string{one, one + "\n空文字列の場合はゼロ値を返す。"}
	}
	field, ok = strings.CutPrefix(name, "func validate")
	if ok {
		return []string{"validate" + field + " は " + n + " の " + field + " フィールドを検証する。"}
	}
	return oneOf(name, map[string]string{
		"type Service":           "Service は " + noun + " のユースケースを実行する。",
		"method *Service.Get":    "Get は指定した ID の " + noun + " を返す。",
		"method *Service.Remove": "Remove は指定した ID の " + noun + " を削除し、その内容を返す。",
		"type Filter":            "Filter は List が返す " + noun + " を絞り込む。",
		"type Repository":        "Repository は全 " + noun + " を一括で読み書きする。",
		"func indexOf":           "indexOf は " + noun + "s 内で指定した ID の " + noun + " の位置を返す。",
		"func nextID":            "nextID は " + noun + "s 内の最大 ID に1を足した新しい " + noun + " の ID を返す。",
	})
}

// configDocTemplates は config.go の default<Name> と load<Name> に対応する CODE-10 の定型文を返す。
func configDocTemplates(f *sourceFile, name string) []string {
	for _, env := range gocliConsts(f.syntax) {
		base := strings.TrimPrefix(env.name, "env")
		if !slices.Contains(declNames(f.syntax), "const default"+base) {
			continue
		}
		switch name {
		case "const default" + base:
			return []string{"default" + base + " は $" + env.value + " が空のときに使う値を表す。"}
		case "func load" + base:
			return []string{"load" + base + " は $" + env.value + " の値を返し、空なら default" + base + " を返す。"}
		}
	}
	return nil
}

// oneOf は templates にある name の定型文をリストで返し、無ければ nil を返す。
func oneOf(name string, templates map[string]string) []string {
	t, ok := templates[name]
	if !ok {
		return nil
	}
	return []string{t}
}

func (c *checker) checkEnvNames(f *sourceFile) {
	ast.Inspect(f.syntax, func(n ast.Node) bool {
		spec, ok := n.(*ast.ValueSpec)
		if !ok || len(spec.Names) != 1 || len(spec.Values) != 1 || !strings.HasPrefix(spec.Names[0].Name, "env") {
			return true
		}
		value := stringValue(spec.Values[0])
		standard := []string{"HOME", "XDG_DATA_HOME"}
		if !slices.Contains(standard, value) && !regexp.MustCompile(`^GOCLI_[A-Z][A-Z0-9_]*$`).MatchString(value) {
			c.at("NAM-06", f, spec.Pos(), "environment variables must be GOCLI_ followed by UPPER_SNAKE_CASE")
		}
		return true
	})
}

// checkSyntax は全 Go ファイルに適用する規則を検査する。
func (c *checker) checkSyntax() {
	for _, f := range c.files {
		c.checkASCII(f)
		c.checkPackageDoc(f)
		c.checkCommentLines(f)
		c.checkNodes(f)
	}
}

// checkASCII はコメントを除くコードが ASCII であることを検査する（OPS-03）。
func (c *checker) checkASCII(f *sourceFile) {
	if f.place.layer == layerTools {
		return
	}
	src := slices.Clone(f.src)
	for _, group := range f.syntax.Comments {
		for _, comment := range group.List {
			for i := c.fset.Position(comment.Pos()).Offset; i < c.fset.Position(comment.End()).Offset; i++ {
				src[i] = ' '
			}
		}
	}
	for i, b := range src {
		if b > maxASCII {
			c.atLine(
				"OPS-03",
				f.path,
				strings.Count(string(f.src[:i]), "\n")+1,
				"write code outside comments in ASCII only",
			)
			return
		}
	}
}

// checkPackageDoc はパッケージの説明が <package>.go だけにあることを検査する（CODE-08）。
func (c *checker) checkPackageDoc(f *sourceFile) {
	want := f.syntax.Name.Name + ".go"
	if f.syntax.Doc != nil && f.name != want {
		c.at("CODE-08", f, f.syntax.Doc.Pos(), "write the package comment only in "+want)
	}
}

// checkCommentLines は各コメント行が句点で終わる日本語の1文であることを検査する（CODE-08）。
// スラッシュの直後が空白でないディレクティブの検査は guard.py に任せる。
func (c *checker) checkCommentLines(f *sourceFile) {
	for _, group := range f.syntax.Comments {
		for _, comment := range group.List {
			text, ok := strings.CutPrefix(comment.Text, "//")
			switch {
			case !ok:
				c.at("CODE-08", f, comment.Pos(), "write comments with //, not /* */")
			case text != "" && !strings.HasPrefix(text, " "):
			case strings.TrimSpace(text) == "":
			case !strings.HasSuffix(text, "。") || strings.Count(text, "。") != 1 || !regexp.MustCompile(`[ぁ-ゖァ-ヺ一-龯]`).MatchString(text):
				c.at("CODE-08", f, comment.Pos(), "write one Japanese sentence per comment line and end it with 。")
			}
		}
	}
}

// checkNodes は NAM-05・ERR-01・OPS-02・ASYNC-01 を検査する。
func (c *checker) checkNodes(f *sourceFile) {
	ast.Inspect(f.syntax, func(n ast.Node) bool {
		switch n := n.(type) {
		case *ast.GoStmt, *ast.ChanType, *ast.SelectStmt, *ast.SendStmt:
			c.at("ASYNC-01", f, n.Pos(), "do not use goroutines or channels")
		case *ast.Field:
			c.checkBoolName(f, n.Names, n.Type)
		case *ast.ValueSpec:
			c.checkBoolName(f, n.Names, n.Type)
		case *ast.CallExpr:
			c.checkErrorf(f, n)
		case *ast.BasicLit:
			c.checkEnvLiteral(f, n)
		}
		return true
	})
}

func (c *checker) checkBoolName(f *sourceFile, names []*ast.Ident, typ ast.Expr) {
	if !isIdent(typ, "bool") {
		return
	}
	for _, name := range names {
		if regexp.MustCompile(`^(is|has|Is|Has)[A-Z]`).MatchString(name.Name) {
			c.at("NAM-05", f, name.Pos(), "do not prefix bool names with is or has: "+name.Name)
		}
	}
}

// checkErrorf は fmt.Errorf のエラーの種類の指定を検査する（ERR-01）。
func (c *checker) checkErrorf(f *sourceFile, call *ast.CallExpr) {
	if exprString(call.Fun) != "fmt.Errorf" || len(call.Args) < 2 {
		return
	}
	kinds := 0
	for _, arg := range call.Args[1:] {
		if strings.HasPrefix(exprString(arg), "errkind.") {
			kinds++
		}
	}
	if kinds == 0 {
		return
	}
	format := stringValue(call.Args[0])
	if !strings.HasPrefix(format, "%w: ") || !strings.HasPrefix(exprString(call.Args[1]), "errkind.") {
		c.at("ERR-01", f, call.Pos(), `wrap the error kind first: fmt.Errorf("%w: detail", errkind.ErrX)`)
	}
}

// checkEnvLiteral は GOCLI_ の名前が許可されたファイルだけにあることを検査する（OPS-02）。
func (c *checker) checkEnvLiteral(f *sourceFile, lit *ast.BasicLit) {
	allowed := f.test || f.place.layer == layerTools || f.path == "internal/app/config.go" ||
		f.path == "internal/app/apptest/apptest.go"
	if lit.Kind == token.STRING && strings.Contains(lit.Value, "GOCLI_") && !allowed {
		c.at("OPS-02", f, lit.Pos(), "name environment variables only in internal/app/config.go")
	}
}

func skipDir(p, name string) error {
	if p == "." {
		return nil
	}
	if strings.HasPrefix(name, ".") || slices.Contains([]string{"docs", "bin"}, name) {
		return fs.SkipDir
	}
	return nil
}

// placeOf は dir の層と名詞を返し、Go ファイルを置けなければゼロ値を返す。
func placeOf(dir string) place {
	fixed := map[string]string{
		".":                    layerMain,
		"internal/app":         layerApp,
		"internal/app/apptest": layerAppTest,
		"internal/cli":         layerCLI,
		"internal/errkind":     layerErrKind,
	}
	layer, ok := fixed[dir]
	if ok {
		return place{layer: layer, noun: ""}
	}
	for _, d := range nounDirs() {
		rest, ok := strings.CutPrefix(dir, d.prefix)
		if !ok {
			continue
		}
		noun, ok := strings.CutSuffix(rest, d.suffix)
		if ok && regexp.MustCompile(`^[a-z][a-z0-9]*$`).MatchString(noun) {
			return place{layer: d.layer, noun: noun}
		}
	}
	return place{layer: "", noun: ""}
}

func nounDirs() []nounDir {
	return []nounDir{
		{layer: layerCommand, prefix: "internal/command/", suffix: "cmd"},
		{layer: layerDomain, prefix: "internal/domain/", suffix: ""},
		{layer: layerAdapter, prefix: "internal/adapter/", suffix: "store"},
		{layer: layerTools, prefix: "tools/", suffix: ""},
	}
}

func nounDirOf(layer, noun string) string {
	for _, d := range nounDirs() {
		if d.layer == layer {
			return d.prefix + noun + d.suffix
		}
	}
	return noun
}

// allowedFileNames は p に対応する STR-03 の表を返し、名前を制限しなければ nil を返す。
func allowedFileNames(p place) []string {
	switch p.layer {
	case layerMain, layerTools:
		return []string{"main.go"}
	case layerApp:
		return []string{"app.go", "config.go"}
	case layerAppTest:
		return []string{"apptest.go"}
	case layerCLI:
		return []string{"cli.go", "exit.go", "help.go", "table.go"}
	case layerErrKind:
		return []string{"errkind.go"}
	case layerDomain:
		return []string{p.noun + ".go", "service.go", "repository.go"}
	case layerAdapter:
		return []string{p.noun + "store.go"}
	}
	return nil
}

func requiredFileNames(p place) []string {
	switch p.layer {
	case layerDomain, layerAdapter:
		return allowedFileNames(p)
	case layerCommand:
		return []string{p.noun + "cmd.go", "view.go"}
	}
	return nil
}

// allowedImports は各層が import できる層の表を返す（DEP-01）。
func allowedImports() map[string][]string {
	return map[string][]string{
		layerMain:    {layerApp},
		layerApp:     {layerCLI, layerCommand, layerDomain, layerAdapter, layerErrKind},
		layerAppTest: {layerApp},
		layerCLI:     {layerErrKind},
		layerCommand: {layerCLI, layerDomain, layerErrKind},
		layerDomain:  {layerErrKind},
		layerAdapter: {layerDomain},
		layerErrKind: nil,
		layerTools:   {layerApp, layerCLI},
	}
}

// restrictedImports は標準パッケージを import できる層の表を返す（DEP-05）。
func restrictedImports() map[string][]string {
	return map[string][]string{
		"os":             {layerMain, layerAdapter, layerTools},
		"io/fs":          {layerMain, layerAdapter, layerTools},
		"os/signal":      {layerMain, layerTools},
		"path/filepath":  {layerApp, layerAdapter, layerTools},
		"flag":           {layerCLI, layerCommand, layerTools},
		"encoding/json":  {layerCLI, layerAdapter},
		"text/tabwriter": {layerCLI},
		"runtime/debug":  {layerApp},
		"testing":        {layerAppTest},
		"os/exec":        nil,
		"net":            nil,
		"net/http":       nil,
		"log":            nil,
		"log/slog":       nil,
		"math/rand":      nil,
		"math/rand/v2":   nil,
		"reflect":        nil,
		"syscall":        nil,
		"unsafe":         nil,
		"io/ioutil":      nil,
		"sync":           nil,
	}
}

// exportedNames は DEP-02 の公開名の表を返す。
// 表に無い層の公開名は制限しない。
func exportedNames() map[string][]string {
	return map[string][]string{
		layerCommand: {"func New"},
		layerAdapter: {"type Store", "func New", "method *Store.Load", "method *Store.Save"},
		layerErrKind: nil,
		layerApp:     {"type Env", "func New", "func Run"},
		layerAppTest: {
			"type Result", "type Harness", "func New", "method *Harness.Setenv", "method *Harness.Run",
			"method *Harness.Setup",
		},
	}
}

func forbiddenVerbs() []string {
	return []string{
		"create", "new", "show", "view", "describe", "ls", "all", "edit", "set", "modify", "delete", "rm", "del",
		"done", "finish",
	}
}

// resultName は Service の結果を受け取る変数名を返す（NAM-05）。
func resultName(verb, noun string) string {
	switch {
	case verb == "list":
		return noun + "s"
	case verb == "get":
		return "found"
	case strings.HasSuffix(verb, "e"):
		return verb + "d"
	}
	return verb + "ed"
}

// declNames は f のトップレベルの宣言を type T・func F・const C・var V・method T.M の形式で順に返す。
func declNames(f *ast.File) []string {
	names := make([]string, 0, len(f.Decls))
	for _, decl := range f.Decls {
		switch d := decl.(type) {
		case *ast.FuncDecl:
			names = append(names, funcName(d))
		case *ast.GenDecl:
			names = append(names, genDeclNames(d)...)
		}
	}
	return names
}

func funcName(d *ast.FuncDecl) string {
	if d.Recv == nil || len(d.Recv.List) == 0 {
		return "func " + d.Name.Name
	}
	return "method " + exprString(d.Recv.List[0].Type) + "." + d.Name.Name
}

func genDeclNames(d *ast.GenDecl) []string {
	var names []string
	for _, spec := range d.Specs {
		switch s := spec.(type) {
		case *ast.TypeSpec:
			names = append(names, "type "+s.Name.Name)
		case *ast.ValueSpec:
			for _, name := range s.Names {
				names = append(names, d.Tok.String()+" "+name.Name)
			}
		}
	}
	return names
}

// isExportedDecl は declNames の名前がパッケージ外に公開されるかを返す。
func isExportedDecl(name string) bool {
	kind, rest, _ := strings.Cut(name, " ")
	if kind != "method" {
		return ast.IsExported(rest)
	}
	recv, method, _ := strings.Cut(strings.TrimPrefix(rest, "*"), ".")
	return ast.IsExported(recv) && ast.IsExported(method)
}

func findFunc(f *ast.File, name string) *ast.FuncDecl {
	for _, decl := range f.Decls {
		fn, ok := decl.(*ast.FuncDecl)
		if ok && fn.Recv == nil && fn.Name.Name == name {
			return fn
		}
	}
	return nil
}

// literalOf は node 内で最初の pkg.typ 型の複合リテラルを返す。
func literalOf(node ast.Node, pkg, typ string) *ast.CompositeLit {
	var found *ast.CompositeLit
	ast.Inspect(node, func(n ast.Node) bool {
		lit, ok := n.(*ast.CompositeLit)
		if ok && found == nil && exprString(lit.Type) == pkg+"."+typ {
			found = lit
		}
		return found == nil
	})
	return found
}

// field は lit の key の値を返し、無ければ nil を返す。
func field(lit *ast.CompositeLit, key string) ast.Expr {
	for _, elt := range lit.Elts {
		kv, ok := elt.(*ast.KeyValueExpr)
		if ok && isIdent(kv.Key, key) {
			return kv.Value
		}
	}
	return nil
}

// calledNames は e が呼ぶ関数の名前を順に返す。
func calledNames(e ast.Expr) []string {
	var names []string
	if e == nil {
		return names
	}
	ast.Inspect(e, func(n ast.Node) bool {
		call, ok := n.(*ast.CallExpr)
		if ok {
			names = append(names, exprString(call.Fun))
		}
		return !ok
	})
	return names
}

// onlyReturnedCall は本体が return call(...) だけの関数リテラルから呼び出しを返す。
func onlyReturnedCall(e ast.Expr) *ast.CallExpr {
	lit, ok := e.(*ast.FuncLit)
	if !ok || len(lit.Body.List) != 1 {
		return nil
	}
	ret, ok := lit.Body.List[0].(*ast.ReturnStmt)
	if !ok || len(ret.Results) != 1 {
		return nil
	}
	call, ok := ret.Results[0].(*ast.CallExpr)
	if !ok {
		return nil
	}
	return call
}

func isMethodCall(e ast.Expr, method string) bool {
	call, ok := e.(*ast.CallExpr)
	if !ok {
		return false
	}
	sel, ok := call.Fun.(*ast.SelectorExpr)
	return ok && sel.Sel.Name == method
}

func isOptsField(e ast.Expr) bool {
	unary, ok := e.(*ast.UnaryExpr)
	return ok && unary.Op == token.AND && strings.HasPrefix(exprString(unary.X), "opts.")
}

func fieldNames(list *ast.FieldList) []string {
	var names []string
	for _, f := range list.List {
		for _, name := range f.Names {
			names = append(names, name.Name)
		}
	}
	return names
}

func identName(e ast.Expr) string {
	ident, ok := e.(*ast.Ident)
	if !ok {
		return ""
	}
	return ident.Name
}

func isIdent(e ast.Expr, name string) bool {
	return identName(e) == name
}

// exprString は識別子・セレクター・ポインターを記述どおりに返し、それ以外は空文字列を返す。
func exprString(e ast.Expr) string {
	switch x := e.(type) {
	case *ast.Ident:
		return x.Name
	case *ast.SelectorExpr:
		return exprString(x.X) + "." + x.Sel.Name
	case *ast.StarExpr:
		return "*" + exprString(x.X)
	}
	return ""
}

// stringValue は文字列リテラルの値を返し、それ以外は空文字列を返す。
func stringValue(e ast.Expr) string {
	lit, ok := e.(*ast.BasicLit)
	if !ok || lit.Kind != token.STRING {
		return ""
	}
	value, err := strconv.Unquote(lit.Value)
	if err != nil {
		return ""
	}
	return value
}

// literalValue は基本リテラルのソース表記を返し、それ以外は空文字列を返す。
func literalValue(e ast.Expr) string {
	lit, ok := e.(*ast.BasicLit)
	if !ok {
		return ""
	}
	return lit.Value
}

// stringValues は複合リテラルに含まれる文字列リテラルを返す。
func stringValues(e ast.Expr) []string {
	lit, ok := e.(*ast.CompositeLit)
	if !ok {
		return nil
	}
	values := make([]string, 0, len(lit.Elts))
	for _, elt := range lit.Elts {
		values = append(values, stringValue(elt))
	}
	return values
}

// upperSnake は lowerCamelCase を UPPER_SNAKE_CASE に変換する。
func upperSnake(s string) string {
	var b strings.Builder
	for i, r := range s {
		if i > 0 && unicode.IsUpper(r) {
			b.WriteByte('_')
		}
		b.WriteRune(unicode.ToUpper(r))
	}
	return b.String()
}

// mixedCaps は頭字語を大文字に保ちながら UPPER_SNAKE_CASE を MixedCaps に変換する。
func mixedCaps(s string) string {
	var b strings.Builder
	for word := range strings.SplitSeq(s, "_") {
		if slices.Contains([]string{"API", "HTTP", "ID", "JSON", "URL", "UTC", "XDG"}, word) {
			b.WriteString(word)
			continue
		}
		b.WriteString(title(strings.ToLower(word)))
	}
	return b.String()
}

// lowerFirst は s の先頭を小文字にして返す。
func lowerFirst(s string) string {
	if s == "" {
		return s
	}
	return strings.ToLower(s[:1]) + s[1:]
}

func title(s string) string {
	if s == "" {
		return s
	}
	return strings.ToUpper(s[:1]) + s[1:]
}

func isKebab(s string) bool {
	return regexp.MustCompile(`^[a-z][a-z0-9]*(-[a-z0-9]+)*$`).MatchString(s)
}

// isSentence は s が大文字で始まり、ピリオドで終わらないかを返す。
func isSentence(s string) bool {
	return regexp.MustCompile(`^[A-Z].*[^.\s]$`).MatchString(s)
}

func isLowerPath(dir string) bool {
	if dir == "." {
		return true
	}
	for part := range strings.SplitSeq(dir, "/") {
		if !regexp.MustCompile(`^[a-z0-9]+$`).MatchString(part) {
			return false
		}
	}
	return true
}
