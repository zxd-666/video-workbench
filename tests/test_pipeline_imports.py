from __future__ import annotations

import ast
import builtins
import importlib
import pkgutil
from pathlib import Path

from app.media import render as render_pkg

PIPELINE_PACKAGE = "app.media.render.pipeline"


def _bound_names(tree: ast.AST) -> set[str]:
    """收集模块里所有被绑定过的名字（import、赋值、函数/类定义、形参、推导式变量）。"""
    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
            args = getattr(node, "args", None)
            if args is not None:
                for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs]:
                    bound.add(arg.arg)
                if args.vararg:
                    bound.add(args.vararg.arg)
                if args.kwarg:
                    bound.add(args.kwarg.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            bound.update(node.names)
    return bound


def _undefined_names(path: Path, module) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}
    known = _bound_names(tree) | set(dir(builtins)) | set(vars(module))
    return sorted(used - known)


def test_pipeline_modules_have_no_undefined_names():
    """渲染流水线拆包后曾漏掉 _tts_signature 的 import，整批渲染直接 NameError。"""
    package = importlib.import_module(PIPELINE_PACKAGE)
    module_dir = Path(package.__file__).parent

    problems: dict[str, list[str]] = {}
    for info in pkgutil.iter_modules([str(module_dir)]):
        path = module_dir / f"{info.name}.py"
        module = importlib.import_module(f"{PIPELINE_PACKAGE}.{info.name}")
        undefined = _undefined_names(path, module)
        if undefined:
            problems[info.name] = undefined

    assert problems == {}


def test_story_render_exposes_tts_signature():
    story_render = importlib.import_module(f"{PIPELINE_PACKAGE}.story_render")

    assert callable(story_render._tts_signature)
