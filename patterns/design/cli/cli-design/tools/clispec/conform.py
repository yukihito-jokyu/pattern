"""適合テスト（TEST-01）。実装を外から実行し、仕様どおりかを確かめる。実装の言語は問わない。

確かめる項目は仕様から導く。HOME・XDG_*・<PREFIX>_DATA_DIR を一時ディレクトリに向けるので、
利用者のデータには触れない。失敗は `FAIL <ルールID> <項目>: <詳細>` の形で出す。
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

import helptext
import model
import vocab

TIMEOUT = 30
COLOR_ENV = ["NO_COLOR", "FORCE_COLOR", "CLICOLOR", "CLICOLOR_FORCE", "PYTHON_COLORS"]
BAD_VALUES = {"integer": "abc", "number": "abc", "enum": "conform_invalid", "date": "2026/01/31"}


class Result(NamedTuple):
    code: int
    out: str
    err: str


class Conform:
    def __init__(self, spec: Dict[str, Any], command: List[str], tmp: Path) -> None:
        self.spec = spec
        self.command = command
        self.tmp = tmp
        self.name = spec["name"]
        self.failures: List[str] = []
        self.passed = 0
        self.counter = 0
        env = {k: v for k, v in os.environ.items() if k not in COLOR_ENV and not k.startswith("XDG_")}
        for sub in ("home", "data", "xdg-data", "xdg-config", "xdg-state", "xdg-cache", "inputs"):
            (tmp / sub).mkdir()
        env.update({"HOME": str(tmp / "home"), "XDG_DATA_HOME": str(tmp / "xdg-data"),
                    "XDG_CONFIG_HOME": str(tmp / "xdg-config"), "XDG_STATE_HOME": str(tmp / "xdg-state"),
                    "XDG_CACHE_HOME": str(tmp / "xdg-cache")})
        if spec["storage"] == "data":
            env[f"{model.prefix(self.name)}_DATA_DIR"] = str(tmp / "data")
        self.env = env

    # --- 実行と、全実行に共通の確認 ---------------------------------------------

    def run(self, args: List[str], codes: List[int], label: str) -> Result:
        try:
            proc = subprocess.run(self.command + args, env=self.env, stdin=subprocess.DEVNULL,
                                  capture_output=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            self.fail("TEST-01", label, f"{TIMEOUT} 秒で終わらない: {args}")
            return Result(-1, "", "")
        out = proc.stdout.decode("utf-8", "replace")
        err = proc.stderr.decode("utf-8", "replace")
        result = Result(proc.returncode, out, err)
        self.expect("ERR-01", label, proc.returncode in codes,
                    f"終了コード {proc.returncode} は宣言した {codes} に無い: {args}\nstderr: {err.strip()}")
        self.expect("OPS-01", label, "\x1b" not in out + err, f"ESC（色・カーソル操作）を出した: {args}")
        if proc.returncode == 0:
            self.expect("OPS-01", label, err == "", f"成功したのに stderr に書いた: {args}\nstderr: {err.strip()}")
        else:
            lines = err.rstrip("\n").split("\n")
            self.expect("ERR-02", label, out == "", f"失敗したのに stdout に書いた: {args}\nstdout: {out.strip()}")
            self.expect("ERR-02", label, len(lines) == 1 and lines[0].startswith(f"{self.name}: "),
                        f"stderr は '{self.name}: <message>' の1行にする: {args}\nstderr: {err.strip()}")
        return result

    def expect(self, rule: str, label: str, ok: bool, detail: str) -> bool:
        if ok:
            self.passed += 1
        else:
            self.fail(rule, label, detail)
        return ok

    def fail(self, rule: str, label: str, detail: str) -> None:
        self.failures.append(f"FAIL {rule} {label}: {detail}")

    # --- 値を作る ------------------------------------------------------------

    def value(self, param: Dict[str, Any]) -> str:
        t = param["type"]
        if t == "integer":
            return "3"
        if t == "number":
            return "1.5"
        if t == "enum":
            return param["values"][0]
        if t == "date":
            return "2026-01-31"
        if t == "file":
            self.counter += 1
            path = self.tmp / "inputs" / f"input-{self.counter}.txt"
            path.write_text("alpha beta alpha\n", encoding="utf-8")
            return str(path)
        if t == "directory":
            return str(self.tmp / "inputs")
        self.counter += 1
        return f"conform-{self.counter}"

    def required_options(self, command: Dict[str, Any]) -> List[str]:
        return [f"--{o['name']}={self.value(o)}" for o in command["options"] if o["required"]]

    def positional(self, command: Dict[str, Any]) -> List[str]:
        return [self.value(a) for a in command["args"] if a["required"] or a["variadic"]]

    def base(self, command: Dict[str, Any]) -> List[str]:
        return list(command["path"]) + self.required_options(command) + self.positional(command)

    # --- 項目 ---------------------------------------------------------------

    def run_all(self) -> None:
        self.check_help_and_version()
        for command in self.spec["commands"]:
            self.check_rejections(command)
        if model.is_single(self.spec):
            self.check_single(self.spec["commands"][0])
        else:
            for noun in model.nouns(self.spec):
                self.check_noun(noun)
            for noun in model.nouns(self.spec):
                self.check_behavior(noun)

    def check_help_and_version(self) -> None:
        root_codes = [0, 2]
        for path, text in helptext.all_helps(self.spec):
            for flag in ("--help", "-h"):
                label = f"{' '.join([self.name] + path + [flag])}"
                r = self.run(path + [flag], root_codes, label)
                self.expect("OPS-05", label, r.code == 0 and r.out == text,
                            f"ヘルプの文面がリファレンスと違う（終了コード {r.code}）\n--- 期待\n{text}--- 実際\n{r.out}")
        r = self.run(["--version"], root_codes, f"{self.name} --version")
        want = f"{self.name} {self.spec['version']}\n"
        self.expect("OPS-05", f"{self.name} --version", r.code == 0 and r.out == want,
                    f"{want.strip()!r} の1行にする（実際: {r.out!r}、終了コード {r.code}）")
        if not model.is_single(self.spec):
            r = self.run([], root_codes, self.name)
            self.expect("OPS-05", f"{self.name}（コマンドなし）", r.code == 2, f"終了コード2にする（実際: {r.code}）")

    def check_rejections(self, command: Dict[str, Any]) -> None:
        prog = model.program(self.spec, command)
        codes = command["exit_codes"]
        r = self.run(self.base(command) + ["--conform-unknown"], codes, f"{prog} --conform-unknown")
        self.expect("DEP-02", f"{prog} 未知のオプション", r.code == 2, f"終了コード2にする（実際: {r.code}）")
        names = [o["name"] for o in command["options"]] + ["help", "json", "version"]
        for option in command["options"]:
            short = option["name"][:-1]
            if len(short) < 2 or short in names:
                continue
            flag = f"--{short}" if option["type"] == "boolean" else f"--{short}={self.value(option)}"
            r = self.run(self.base(command) + [flag], codes, f"{prog} {flag}")
            self.expect("DEP-02", f"{prog} 前方一致 {flag}", r.code == 2, f"前方一致を受け付けない（実際: {r.code}）")
            break
        for option in command["options"]:
            bad = BAD_VALUES.get(option["type"])
            if bad is None:
                continue
            flag = f"--{option['name']}={bad}"
            args = [a for a in self.base(command) if not a.startswith(f"--{option['name']}=")] + [flag]
            r = self.run(args, codes, f"{prog} {flag}")
            self.expect("ERR-03", f"{prog} {flag}", r.code == 2, f"型に合わない値は終了コード2にする（実際: {r.code}）")
        if any(a["required"] for a in command["args"]):
            r = self.run(list(command["path"]) + self.required_options(command), codes, f"{prog}（位置引数なし）")
            self.expect("ERR-03", f"{prog} 位置引数の欠落", r.code == 2, f"終了コード2にする（実際: {r.code}）")
        boolean = next((o["name"] for o in command["options"] if o["type"] == "boolean"), None)
        if boolean is None and command["output"]["kind"] in ("object", "list"):
            boolean = "json"
        if boolean is not None:
            r = self.run(self.base(command) + [f"--{boolean}=true"], codes, f"{prog} --{boolean}=true")
            self.expect("DEP-03", f"{prog} --{boolean}=true", r.code == 2, f"真偽値のオプションに値を付けたら終了コード2にする（実際: {r.code}）")
        long_only = next((o for o in command["options"] if model.short_name(o["name"]) is None), None)
        if long_only is not None:
            flag = [f"-{long_only['name']}"] + ([] if long_only["type"] == "boolean" else [self.value(long_only)])
            r = self.run(self.base(command) + flag, codes, f"{prog} {' '.join(flag)}")
            self.expect("DEP-03", f"{prog} -{long_only['name']}", r.code == 2,
                        f"1つのダッシュの長い名前を受け付けない（実際: {r.code}）")
        before = list(command["path"]) + self.required_options(command)
        if any(a["type"] in ("string", "file", "directory") for a in command["args"][:1]):
            r = self.run(before + ["--", "-conform-dash"], codes, f"{prog} -- -conform-dash")
            self.expect("DEP-03", f"{prog} -- の後ろの値", r.code != 2,
                        f"-- の後ろの -conform-dash を位置引数として受け取る（終了コード {r.code}）")
        for arg in command["args"]:
            if arg["type"] in ("file", "directory"):
                missing = str(self.tmp / "conform-missing")
                r = self.run(before + [missing], codes, f"{prog} <無い {arg['type']}>")
                self.expect("ERR-01", f"{prog} 無い {arg['type']}", r.code == 3, f"終了コード3にする（実際: {r.code}）")

    def check_output(self, command: Dict[str, Any], args: List[str], label: str,
                     text_args: Optional[List[str]] = None) -> Optional[Any]:
        """--json とテキストで実行し、形を確かめる。--json の値を返す。text_args はテキストで実行する引数（既定は args）。"""
        kind = command["output"]["kind"]
        codes = command["exit_codes"]
        if kind not in ("object", "list"):
            r = self.run(args, codes, label)
            self.expect("TEST-01", label, r.code == 0, f"終了コード0にする（実際: {r.code}）\nstderr: {r.err.strip()}")
            if kind == "none":
                self.expect("OPS-04", label, r.out == "", "output.kind が none のコマンドは stdout に書かない")
            return None
        type_ = model.types_by_name(self.spec)[command["output"]["type"]]
        at = len(command["path"])  # --json を位置引数の前に置き、順序に依存しないことも確かめる（DEP-03）
        r = self.run(args[:at] + ["--json"] + args[at:], codes, label + " --json")
        if not self.expect("TEST-01", label + " --json", r.code == 0,
                           f"終了コード0にする（実際: {r.code}）\nstderr: {r.err.strip()}"):
            return None
        try:
            data = json.loads(r.out)
        except json.JSONDecodeError as exc:
            self.fail("OPS-04", label + " --json", f"JSON として読めない: {exc}")
            return None
        problems = check_json(type_, data, kind == "list")
        self.expect("OPS-04", label + " --json", not problems, "; ".join(problems))
        r = self.run(text_args or args, codes, label)
        header = r.out.split("\n", 1)[0].split()
        self.expect("OPS-04", label + "（テキスト）", r.code == 0 and header == helptext.table_header(type_),
                    f"表の見出しを {helptext.table_header(type_)} にする（実際: {header}、終了コード {r.code}）")
        return data

    def check_single(self, command: Dict[str, Any]) -> None:
        self.check_output(command, self.base(command), self.name)

    def check_noun(self, noun: str) -> None:
        commands = {c["path"][1]: c for c in self.spec["commands"] if c["path"][0] == noun}
        type_ = model.types_by_name(self.spec).get(noun)
        key = model.key_field(type_)
        if type_ is None or key is None:
            return
        k = key["name"]
        created: Optional[Dict[str, Any]] = None
        create = commands.get("create")
        if create is not None:
            prog = model.program(self.spec, create)
            created = self.check_output(create, self.base(create), prog, self.base(create))
            if k == "name" and isinstance(created, dict):
                args = list(create["path"]) + self.required_options(create) + [str(created["name"])]
                r = self.run(args, create["exit_codes"], f"{prog}（同じ名前）")
                self.expect("ERR-01", f"{prog} 同じ名前", r.code == 4, f"終了コード4にする（実際: {r.code}）")
        if "list" in commands:
            data = self.check_output(commands["list"], [noun, "list"], f"{self.name} {noun} list")
            if created is not None and isinstance(data, list):
                self.expect("OPS-04", f"{self.name} {noun} list --json", len(data) >= 1, "作った項目が一覧に無い")
        key_value = str(created[k]) if isinstance(created, dict) and k in created else None
        missing = "999999" if k == "id" else "conform-missing"
        if "view" in commands:
            view = commands["view"]
            if key_value is not None:
                data = self.check_output(view, [noun, "view", key_value], f"{self.name} {noun} view")
                if isinstance(data, dict) and isinstance(created, dict):
                    self.expect("OPS-04", f"{self.name} {noun} view --json", data == created,
                                "create が返した項目と view が返した項目が違う")
            r = self.run([noun, "view", missing], view["exit_codes"], f"{self.name} {noun} view {missing}")
            self.expect("ERR-01", f"{self.name} {noun} view（無い識別子）", r.code == 3, f"終了コード3にする（実際: {r.code}）")
        if "edit" in commands and key_value is not None:
            edit = commands["edit"]
            settable = [o for o in edit["options"] if o["name"] not in vocab.STANDARD_OPTIONS]
            if settable:
                option = settable[0]
                flag = f"--{option['name']}" if option["type"] == "boolean" else f"--{option['name']}={self.value(option)}"
                self.check_output(edit, [noun, "edit", key_value, flag], f"{self.name} {noun} edit")
        if "delete" in commands and key_value is not None:
            delete = commands["delete"]
            r = self.run([noun, "delete", key_value, "--json"], delete["exit_codes"], f"{self.name} {noun} delete --json")
            ok = r.code == 0 and not check_json(type_, _json(r.out), False)
            self.expect("OPS-04", f"{self.name} {noun} delete --json", ok, f"消した1件を JSON で返す（終了コード {r.code}）")
            r = self.run([noun, "delete", key_value], delete["exit_codes"], f"{self.name} {noun} delete（2回目）")
            self.expect("ERR-01", f"{self.name} {noun} delete（無い識別子）", r.code == 3, f"終了コード3にする（実際: {r.code}）")

    # --- STATE-02 標準の動詞の振る舞い ---------------------------------------------

    def check_behavior(self, noun: str) -> None:
        """確認ごとに空のデータの置き場で行を作り、STATE-02 の決定表どおりかを確かめる。"""
        commands = {c["path"][1]: c for c in self.spec["commands"] if c["path"][0] == noun}
        type_ = model.types_by_name(self.spec).get(noun)
        if self.spec["storage"] != "data" or type_ is None or "create" not in commands or "list" not in commands:
            return
        b = Behavior(self, noun, type_, commands)
        b.check_create()
        b.check_list()
        if "edit" in commands:
            b.check_edit()

    def fresh_data(self) -> None:
        self.counter += 1
        directory = self.tmp / f"data-{self.counter}"
        directory.mkdir()
        self.env[f"{model.prefix(self.name)}_DATA_DIR"] = str(directory)


PAIRS = {"string": ("conform-a", "conform-b"), "integer": ("1", "2"), "number": ("1.5", "2.5"),
         "date": ("2026-01-01", "2026-01-02"), "timestamp": ("2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z")}


def pair(field: Dict[str, Any]) -> Optional[tuple]:
    """値の小さい順の2つ。作れない型は None。"""
    if field["type"] == "enum":
        return tuple(sorted(field["values"])[:2]) if len(field["values"]) >= 2 else None
    return PAIRS.get(field["type"])


def parsed(field: Dict[str, Any], text: str) -> Any:
    return {"integer": int, "number": float}.get(field["type"], str)(text)


class Behavior:
    def __init__(self, c: Conform, noun: str, type_: Dict[str, Any], commands: Dict[str, Dict[str, Any]]) -> None:
        self.c = c
        self.noun = noun
        self.type_ = type_
        self.commands = commands
        self.key = model.key_field(type_)["name"]
        self.create_opts = {o["name"]: o for o in commands["create"]["options"]}
        self.fields = [f for f in model.settable_fields(type_) if model.field_option_name(f) in self.create_opts]

    def label(self, text: str) -> str:
        return f"{self.c.name} {self.noun} {text}"

    def json_run(self, verb: str, args: List[str], label: str) -> Optional[Any]:
        r = self.c.run([self.noun, verb] + args + ["--json"], self.commands[verb]["exit_codes"], label)
        if not self.c.expect("STATE-02", label, r.code == 0, f"終了コード0にする（実際: {r.code}）\nstderr: {r.err.strip()}"):
            return None
        return _json(r.out)

    def code_of(self, verb: str, args: List[str], label: str) -> int:
        return self.c.run([self.noun, verb] + args, self.commands[verb]["exit_codes"], label).code

    def create(self, settings: Dict[str, Any], label: str) -> Optional[Dict[str, Any]]:
        """settings は オプション名 → 値の list（boolean は True）。指定の無い必須のオプションは仮の値で埋める。"""
        args: List[str] = []
        for name, option in self.create_opts.items():
            if name in settings:
                value = settings[name]
                args += [f"--{name}"] if value is True else [f"--{name}={v}" for v in value]
            elif option["required"]:
                args.append(f"--{name}={self.c.value(option)}")
        for arg in self.commands["create"]["args"]:
            if self.key == "name":
                self.c.counter += 1
                args.append(f"conform-row-{self.c.counter:04d}")
            else:
                args.append(self.c.value(arg))
        data = self.json_run("create", args, self.label(f"create {label}"))
        return data if isinstance(data, dict) else None

    def keys(self, args: List[str], label: str) -> Optional[List[Any]]:
        data = self.json_run("list", args, self.label(f"list {label}"))
        return [row.get(self.key) for row in data] if isinstance(data, list) else None

    def expect_keys(self, args: List[str], rows: List[Optional[Dict[str, Any]]], label: str, why: str) -> None:
        if any(r is None for r in rows):
            return
        got = self.keys(args, label)
        want = [r[self.key] for r in rows]
        if got is not None:
            self.c.expect("STATE-02", self.label(f"list {label}"), got == want, f"{why}（期待: {want}、実際: {got}）")

    def setting(self, field: Dict[str, Any], value: Any) -> Dict[str, Any]:
        name = model.field_option_name(field)
        if field["type"] == "boolean":
            return {name: True} if value else {}
        return {name: value if isinstance(value, list) else [value]}

    def check_create(self) -> None:
        if self.key == "id" and "delete" in self.commands:
            self.c.fresh_data()
            first = self.create({}, "（1件目）")
            if first is not None:
                self.code_of("delete", [str(first["id"])], self.label("delete（1件目）"))
                second = self.create({}, "（消した後）")
                if second is not None:
                    self.c.expect("STATE-02", self.label("create の id"), second["id"] > first["id"],
                                  f"消した id を再利用しない（1件目 {first['id']}、次 {second['id']}）")
        self.c.fresh_data()
        row = self.create({}, "（省略）")
        for field in self.fields if row is not None else []:
            option = self.create_opts[model.field_option_name(field)]
            if option["required"]:
                continue
            want = option["default"]
            if want is None:
                want = [] if field["list"] else (False if field["type"] == "boolean" else None)
            self.c.expect("STATE-02", self.label(f"create（{field['name']} を省略）"), row.get(field["name"]) == want,
                          f"省略した {field['name']} を {want!r} にする（実際: {row.get(field['name'])!r}）")
        for field in self.fields:
            if field["type"] == "string":
                name = model.field_option_name(field)
                code = self.code_of("create", [f"--{name}="], self.label(f"create --{name}=（空文字）"))
                self.c.expect("STATE-02", self.label(f"create --{name}="), code == 2, f"空文字は終了コード2にする（実際: {code}）")
                break
        for field in self.fields:
            values = pair(field)
            if field["list"] and values:
                self.c.fresh_data()
                row = self.create(self.setting(field, [values[1], values[0], values[1]]), f"（{field['name']} の重複）")
                want = [parsed(field, v) for v in values]
                if row is not None:
                    self.c.expect("STATE-02", self.label(f"create（{field['name']}）"), row[field["name"]] == want,
                                  f"list の項目は重複を除いて昇順にする（期待: {want}、実際: {row[field['name']]}）")

    def check_list(self) -> None:
        _, allowed = model.option_plan(self.type_, "list")
        names = {o["name"] for o in self.commands["list"]["options"]}
        for field in self.fields:
            values = pair(field)
            option = model.field_option_name(field)
            if option in names and field["type"] == "boolean":
                self.c.fresh_data()
                rows = [self.create(self.setting(field, True), f"（{field['name']} true）"),
                        self.create({}, f"（{field['name']} false）")]
                self.expect_keys([f"--{option}"], rows[:1], f"--{option}", "boolean の絞り込みは true の行だけにする")
            elif option in names and values and field["list"]:
                self.c.fresh_data()
                rows = [self.create(self.setting(field, [values[0]]), f"（{field['name']} 1つ）"),
                        self.create(self.setting(field, list(values)), f"（{field['name']} 2つ）")]
                self.expect_keys([f"--{option}={values[1]}"], rows[1:], f"--{option}", "値を要素に含む行だけにする")
                self.expect_keys([f"--{option}={values[0]}", f"--{option}={values[1]}"], rows[1:],
                                 f"--{option} を繰り返す", "繰り返したら全部の値を含む行だけにする（AND）")
            elif option in names and values:
                self.c.fresh_data()
                rows = [self.create(self.setting(field, v), f"（{field['name']}={v}）") for v in values]
                if field["nullable"]:
                    self.create({}, f"（{field['name']} null）")
                self.expect_keys([f"--{option}={values[1]}"], rows[1:], f"--{option}", "値が等しい行だけにする")
            if option + "-from" in names and option + "-to" in names and values:
                self.c.fresh_data()
                rows = [self.create(self.setting(field, v), f"（{field['name']}={v}）") for v in values]
                if field["nullable"]:
                    self.create({}, f"（{field['name']} null）")
                self.expect_keys([f"--{option}-from={values[1]}"], rows[1:], f"--{option}-from", "from 以上の行だけにし、null を含めない")
                self.expect_keys([f"--{option}-to={values[0]}"], rows[:1], f"--{option}-to", "to 以下の行だけにし、null を含めない")
            sortable = field["name"] in next((o["values"] for o in self.commands["list"]["options"] if o["name"] == "sort"), [])
            if sortable and (values or field["type"] == "boolean"):
                low, high = (False, True) if field["type"] == "boolean" else values
                self.c.fresh_data()
                rows = [self.create(self.setting(field, high), "（大きい値）"), self.create(self.setting(field, low), "（小さい値）"),
                        self.create(self.setting(field, low), "（小さい値・2件目）")]
                if field["nullable"]:
                    rows.append(self.create({}, "（null）"))
                order = [rows[1], rows[2], rows[0]] + rows[3:]
                self.expect_keys([f"--sort={field['name']}"], order, f"--sort={field['name']}",
                                 "昇順、同じ値は識別子の順、null は末尾にする")
        self.c.fresh_data()
        rows = [self.create({}, "（limit 1件目）"), self.create({}, "（limit 2件目）")]
        self.expect_keys(["--limit=1"], rows[:1], "--limit=1", "絞り込みと並べ替えの後の先頭から N 件にする")
        code = self.code_of("list", ["--limit=0"], self.label("list --limit=0"))
        self.c.expect("STATE-02", self.label("list --limit=0"), code == 2, f"1 未満は終了コード2にする（実際: {code}）")

    def check_edit(self) -> None:
        edit_names = {o["name"] for o in self.commands["edit"]["options"]}
        self.c.fresh_data()
        row = self.create({}, "（edit）")
        if row is None:
            return
        key = str(row[self.key])
        code = self.code_of("edit", [key], self.label("edit（オプションなし）"))
        self.c.expect("STATE-02", self.label("edit（オプションなし）"), code == 2, f"値を変えるオプションが無ければ終了コード2にする（実際: {code}）")
        for field in self.fields:
            values = pair(field)
            option = model.field_option_name(field)
            clear = "clear-" + field["name"].replace("_", "-")
            if field["list"] and values and option in edit_names:
                self.c.fresh_data()
                row = self.create(self.setting(field, [values[0]]), f"（{field['name']} を置き換える）")
                data = self.json_run("edit", [str(row[self.key]), f"--{option}={values[1]}"], self.label(f"edit --{option}")) if row else None
                if isinstance(data, dict):
                    self.c.expect("STATE-02", self.label(f"edit --{option}"), data.get(field["name"]) == [parsed(field, values[1])],
                                  f"指定した値の集まりで置き換える（実際: {data.get(field['name'])}）")
            if clear not in edit_names:
                continue
            value = True if field["type"] == "boolean" else ([values[0]] if field["list"] else values[0]) if values else None
            if value is None:
                continue
            self.c.fresh_data()
            row = self.create(self.setting(field, value), f"（{field['name']} を消す）")
            if row is None:
                continue
            want = [] if field["list"] else (False if field["type"] == "boolean" else None)
            data = self.json_run("edit", [str(row[self.key]), f"--{clear}"], self.label(f"edit --{clear}"))
            if isinstance(data, dict):
                self.c.expect("STATE-02", self.label(f"edit --{clear}"), data.get(field["name"]) == want,
                              f"{field['name']} を {want!r} にする（実際: {data.get(field['name'])!r}）")
            if option in edit_names:
                both = [f"--{option}"] if field["type"] == "boolean" else [f"--{option}={values[0]}"]
                code = self.code_of("edit", [str(row[self.key]), f"--{clear}"] + both, self.label(f"edit --{clear} --{option}"))
                self.c.expect("STATE-02", self.label(f"edit --{clear} --{option}"), code == 2,
                              f"--{clear} と --{option} を一緒に指定したら終了コード2にする（実際: {code}）")


def _json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def check_json(type_: Dict[str, Any], data: Any, is_list: bool) -> List[str]:
    if is_list:
        if not isinstance(data, list):
            return ["--json の最上位を配列にする"]
        problems: List[str] = []
        for item in data:
            problems += check_json(type_, item, False)
        return problems
    if not isinstance(data, dict):
        return ["--json の最上位をオブジェクトにする"]
    names = [f["name"] for f in type_["fields"]]
    problems = []
    if sorted(data) != sorted(names):
        problems.append(f"キーを {names} にする（実際: {list(data)}）")
    for field in type_["fields"]:
        if field["name"] in data:
            problems += _check_value(field, data[field["name"]])
    return problems


def _check_value(field: Dict[str, Any], value: Any) -> List[str]:
    name = field["name"]
    if value is None:
        return [] if field["nullable"] else [f"{name} は null にしない"]
    if field["list"]:
        if not isinstance(value, list):
            return [f"{name} は配列にする"]
        return [p for v in value for p in _check_scalar(field, v)]
    return _check_scalar(field, value)


def _check_scalar(field: Dict[str, Any], value: Any) -> List[str]:
    t, name = field["type"], field["name"]
    ok = {
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "string": isinstance(value, str),
        "enum": value in field["values"],
        "date": isinstance(value, str) and bool(vocab.DATE.match(value)),
        "timestamp": isinstance(value, str) and bool(vocab.TIMESTAMP.match(value)),
    }.get(t, False)
    return [] if ok else [f"{name} の値 {value!r} は {t} の形にする（OPS-03、OPS-04）"]


def run(spec: Dict[str, Any], command: List[str]) -> List[str]:
    with tempfile.TemporaryDirectory(prefix="clispec-conform-") as tmp:
        c = Conform(spec, command, Path(tmp))
        c.run_all()
        return c.failures + [f"conform: {c.passed} 件成功、{len(c.failures)} 件失敗"]
