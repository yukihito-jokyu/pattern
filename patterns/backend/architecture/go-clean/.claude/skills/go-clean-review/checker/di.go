package main

import (
	"strings"
)

const mainPath = "cmd/api/main.go"

// checkDI は、adapter と usecase のコンストラクタが main.go で配線されているかを見る（C01）。
func (p *project) checkDI() {
	main, ok := p.files[mainPath]
	if !ok {
		return
	}
	for rel, f := range p.files {
		if isTestPath(rel) {
			continue
		}
		inAdapter := strings.HasPrefix(rel, adapterDir+"/")
		inUsecase := strings.HasPrefix(rel, usecaseDir+"/")
		if !inAdapter && !inUsecase {
			continue
		}
		for _, fd := range funcDecls(f.ast) {
			name := fd.Name.Name
			if fd.Recv != nil || !strings.HasPrefix(name, "New") || !isExportedName(name) || name == "NewRouter" {
				continue
			}
			if !strings.Contains(main.src, "."+name+"(") {
				p.add("WARN", "C01", rel, p.line(fd.Pos()), "%s が cmd/api/main.go で呼ばれていない（DI を配線し忘れていないか）", name)
			}
		}
	}
}

func isExportedName(s string) bool { return s != "" && strings.ToUpper(s[:1]) == s[:1] }
