"""一時コピーに禁止importを加え、depguardが拒否することを確認する。"""

import pathlib
import shutil
import subprocess
import sys
import tempfile


root = pathlib.Path(__file__).resolve().parent.parent
binary = str(pathlib.Path(sys.argv[1]).resolve())
with tempfile.TemporaryDirectory(prefix="go-clean-dependency-") as directory:
    target = pathlib.Path(directory) / "go-clean"
    shutil.copytree(root, target, ignore=shutil.ignore_patterns("bin", ".git", ".env", ".venv", "__pycache__"))
    violation = target / "internal/domain/user/dependency_violation.go"
    violation.write_text('package user\n\nimport "net/http"\n\nvar forbiddenHTTPMethod = http.MethodGet\n')
    result = subprocess.run([binary, "run", "./..."], cwd=target, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    if result.returncode == 0 or "(depguard)" not in result.stdout or "net/http" not in result.stdout:
        raise RuntimeError("Expected depguard to reject domain importing net/http:\n" + result.stdout)
    print("Dependency check: domain importing net/http rejected by depguard")
