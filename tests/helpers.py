"""Shared bits for the tests: the repo root and the pages on the site."""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_script(name):
    """A script under scripts/ (with a dash in its name) as a module."""
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def html_pages():
    """Every HTML page in the site, as paths relative to the root (assets and .github left out)."""
    skip = ("assets", ".github", ".git", "tests", "node_modules")
    return sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in ROOT.rglob("*.html")
                  if not p.relative_to(ROOT).parts[0] in skip)


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def head(rel):
    text = read(rel)
    return re.search(r"<head>(.*?)</head>", text, re.S).group(1)
