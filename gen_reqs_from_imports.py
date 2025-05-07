#!/usr/bin/env python3
import ast
import os
import importlib.metadata as md

# Directories to skip (relative to cwd)
SKIP_DIRS = {"docs", "duckling", "logs", "static", "__pycache__"}

def find_py_files(root="."):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".py"):
                yield os.path.join(dirpath, fn)

def extract_top_imports(path):
    try:
        content = open(path, "r", encoding="utf-8", errors="ignore").read()
        node = ast.parse(content, path)
    except Exception:
        # skip files that fail to parse
        return set()
    imports = set()
    for stmt in node.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                imports.add(alias.name.split(".", 1)[0])
        elif isinstance(stmt, ast.ImportFrom):
            if stmt.module and stmt.level == 0:
                imports.add(stmt.module.split(".", 1)[0])
    return imports

def get_version(pkg):
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return None

def main():
    all_imports = set()
    for py in find_py_files():
        all_imports |= extract_top_imports(py)

    # resolve versions
    pkgs = {}
    for pkg in sorted(all_imports):
        ver = get_version(pkg)
        if ver:
            pkgs[pkg] = ver

    if not pkgs:
        print("No third-party packages detected.")
        return

    print(f"Found {len(pkgs)} packages; appending to requirements.txt")
    with open("requirements.txt", "a", encoding="utf-8") as req:
        req.write("\n# --- auto-generated from imports ---\n")
        for pkg, ver in pkgs.items():
            req.write(f"{pkg}=={ver}\n")

if __name__ == "__main__":
    main()
