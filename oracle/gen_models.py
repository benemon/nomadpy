"""Generates nomadpy Model dataclasses from oracle/fixtures/surface.json.

A Python module declares what it wants generated with a marker line:

    # generated from surface.json: file=jobs.go only=Job,UpdateStrategy mixins=Job:JobMethods

and everything from that line to `# end generated` is replaced on each run.
`mixins` names hand-written classes, defined above the region, that a
generated class inherits before Model, so methods survive regeneration.
A file that is only models (tasks.py, consul.py) holds its marker at the top
and the whole file is generated. Run `make models` after `make oracle`.

Usage: gen_models.py <surface.json> <module.py> [<module.py> ...]
"""

import json
import re
import sys

MARKER = re.compile(r"^# generated from surface\.json: file=(\S+)(?: only=(\S+))?(?: mixins=(\S+))?$", re.M)
END = "# end generated"
INTS = {"int", "int8", "int16", "int32", "int64", "uint", "uint8", "uint16", "uint32", "uint64", "uintptr"}
FLOATS = {"float32", "float64"}
# Names whose Go spelling does not split into words the way the rule below expects.
SNAKE_OVERRIDES = {"MBits": "mbits"}


def snake(name):
    if name in SNAKE_OVERRIDES:
        return SNAKE_OVERRIDES[name]
    # A plural acronym (CIDRs, UIDs) keeps its s with the acronym.
    name = re.sub(r"([A-Z]{2,})s(?=[A-Z]|$)", lambda m: m.group(1) + "S", name)
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower()


def json_name(py):
    return "".join(p.capitalize() for p in py.split("_"))


class Generator:
    def __init__(self, surface, go_file, only, mixins=None):
        self.surface = surface
        self.mixins = dict(m.split(":") for m in mixins.split(",")) if mixins else {}
        self.this = go_file.removesuffix(".go")
        self.structs = {name for f in surface["files"].values() for name in f["structs"]}
        self.module_of = {name: go.removesuffix(".go") for go, f in surface["files"].items() for name in f["structs"]}
        self.named = {name: under for f in surface["files"].values() for name, under in f.get("types", {}).items()}
        self.named["contexts.Context"] = "string"
        self.referenced = {self._base(fl["type"]) for f in surface["files"].values() for st in f["structs"].values() for fl in st["fields"]}
        self.file = surface["files"][go_file]
        self.only = set(only.split(",")) if only else set()
        self.used_modules = set()
        self.uses_field = False
        self.uses_any = False

    @staticmethod
    def _base(t):
        t = t.lstrip("*")
        while t.startswith("[]"):
            t = t[2:]
        if t.startswith("map["):
            t = re.match(r"map\[[^\]]+\](.+)", t).group(1).lstrip("*")
        return t

    def is_model(self, name, st):
        """Request bodies, option bundles and services are not models; a spec struct another struct embeds as a field is."""
        if not st["fields"]:
            return name in self.referenced
        if name.endswith(("Request", "Options", "Opts")):
            return name in self.referenced
        return True

    def py_type(self, go, meta):
        pointer = go.startswith("*")
        base = go[1:] if pointer else go
        if base.startswith("[]"):
            if base == "[]byte":
                return "str | None", "None"
            inner = self.py_type(base[2:], meta)[0].removesuffix(" | None")
            return f"list[{inner}] | None", "None"
        if base.startswith("map["):
            key, val = re.match(r"map\[([^\]]+)\](.+)", base).groups()
            inner = self.py_type(val, meta)[0].removesuffix(" | None")
            return f"dict[{'str' if key == 'string' else self.py_type(key, meta)[0]}, {inner}] | None", "None"
        if base in self.named and base not in self.structs:
            ann, default = self.py_type(self.named[base], meta)
            if pointer and not ann.endswith("| None"):
                return ann + " | None", "None"
            return ann, default
        if base == "string":
            return ("str | None", "None") if pointer else ("str", '""')
        if base in INTS:
            return ("int | None", "None") if pointer else ("int", "0")
        if base in FLOATS:
            return ("float | None", "None") if pointer else ("float", "0.0")
        if base == "bool":
            return ("bool | None", "None") if pointer else ("bool", "False")
        if base == "time.Duration":
            return ("int | None", "None") if pointer else ("int", "0")
        if base == "time.Time":
            meta["time"] = True
            return ("str | None", "None") if pointer else ("str", '""')
        if base in self.structs:
            module = self.module_of[base]
            if module == self.this:
                return (f"{base} | None", "None") if pointer else (base, f"field(default_factory={base})")
            self.used_modules.add(module)
            qualified = f"_{module}.{base}"
            return (f"{qualified} | None", "None") if pointer else (qualified, f"field(default_factory=lambda: {qualified}())")
        self.uses_any = True
        return "Any", "None"

    def struct(self, name, st):
        body = []
        for f in st["fields"]:
            if f.get("embedded"):
                continue
            meta = {}
            py = snake(f["name"])
            ann, default = self.py_type(f["type"], meta)
            if "Any" in ann:
                self.uses_any = True
            if json_name(py) != f["json"]:
                meta["json"] = f["json"]
            if f.get("omitempty"):
                meta["omitempty"] = True
            if default.startswith("field("):
                self.uses_field = True
                if meta:
                    default = default[:-1] + f", metadata={meta!r})"
                body.append(f"    {py}: {ann} = {default}")
            elif meta:
                self.uses_field = True
                body.append(f"    {py}: {ann} = field(default={default}, metadata={meta!r})")
            else:
                body.append(f"    {py}: {ann} = {default}")
        bases = f"{self.mixins[name]}, Model" if name in self.mixins else "Model"
        return f"@dataclass\nclass {name}({bases}):\n" + "\n".join(body or ["    pass"]) + "\n"

    def value_deps(self, st):
        return {f["type"] for f in st["fields"] if not f.get("embedded") and f["type"] in self.file["structs"]}

    def consts(self):
        return [f"{snake(c['name']).upper()} = {c['value']}" for c in self.file["consts"]
                if c["value"].startswith('"') or re.fullmatch(r"-?\d+", c["value"])]

    def render(self):
        names = [n for n, st in self.file["structs"].items() if (n in self.only if self.only else self.is_model(n, st))]
        emitted, out = [], []
        while names:
            progressed = False
            for n in list(names):
                if self.value_deps(self.file["structs"][n]) - set(emitted):
                    continue
                out.append(self.struct(n, self.file["structs"][n]))
                emitted.append(n)
                names.remove(n)
                progressed = True
            if not progressed:
                raise SystemExit(f"cycle among {names}")
        consts = self.consts()
        return consts, out


def regenerate(surface, path):
    text = open(path).read()
    m = MARKER.search(text)
    if not m:
        raise SystemExit(f"{path}: no generation marker")
    gen = Generator(surface, m.group(1), m.group(2), m.group(3))
    consts, classes = gen.render()
    whole_file = text.startswith(m.group(0))
    parts = []
    if whole_file:
        parts.append(m.group(0))
        parts.append("")
        parts.append("from __future__ import annotations")
        parts.append("")
        imports = "from dataclasses import dataclass" + (", field" if gen.uses_field else "")
        parts.append(imports)
        if gen.uses_any:
            parts.append("from typing import Any")
        parts.append("")
        parts.append("from .models import Model")
        parts += [f"from . import {mod} as _{mod}" for mod in sorted(gen.used_modules)]
        parts.append("")
    else:
        parts.append(m.group(0))
        # A mixed module imports its siblings here, inside the region, so a regeneration that needs a new one is self-contained.
        parts += [f"from . import {mod} as _{mod}  # noqa: E402" for mod in sorted(gen.used_modules)]
    if consts:
        parts.append("")
        parts += consts
        parts.append("")
    parts.append("")
    parts.append("\n\n".join(classes).rstrip("\n"))
    parts.append("")
    if whole_file:
        parts.append(END)
        new = "\n".join(parts) + "\n"
    else:
        end = text.index(END, m.end())
        parts.append("")
        new = text[:m.start()] + "\n".join(parts) + "\n" + text[end:]
    if new != text:
        open(path, "w").write(new)
        return True
    return False


def main():
    surface = json.load(open(sys.argv[1]))
    changed = [p for p in sys.argv[2:] if regenerate(surface, p)]
    print(f"{len(changed)} of {len(sys.argv) - 2} modules changed" + (": " + ", ".join(changed) if changed else ""))


if __name__ == "__main__":
    main()
