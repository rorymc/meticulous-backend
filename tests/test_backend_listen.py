"""
Regression test for invalid kwargs passed to app.listen() in backend.py.

ffebc909 introduced a typo ('aaddress' instead of 'address') that caused a
TypeError at startup. This test parses backend.py with the AST and validates
every .listen() call's keyword arguments against tornado.httpserver.HTTPServer's
actual __init__ signature, which is where forwarded **kwargs land.
"""
import ast
import inspect
import pathlib

import tornado.httpserver


def _httpserver_valid_kwargs() -> set[str]:
    sig = inspect.signature(tornado.httpserver.HTTPServer.__init__)
    params = sig.parameters
    return {
        name
        for name, p in params.items()
        if name != "self" and p.kind
        not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )
    }


def test_backend_listen_kwargs_are_valid():
    """Verify every app.listen() call in backend.py uses only valid kwargs."""
    backend_path = pathlib.Path(__file__).parent.parent / "backend.py"
    source = backend_path.read_text()
    tree = ast.parse(source, filename=str(backend_path))

    valid_kwargs = _httpserver_valid_kwargs()
    # 'address' is handled by Application.listen() itself before forwarding
    valid_kwargs.add("address")

    errors = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "listen"):
            continue
        for kw in node.keywords:
            if kw.arg is None:
                continue  # **kwargs unpacking — skip
            if kw.arg not in valid_kwargs:
                errors.append(
                    f"backend.py:{node.lineno}: invalid kwarg '{kw.arg}' "
                    f"passed to .listen() — valid options: {sorted(valid_kwargs)}"
                )

    assert not errors, "\n".join(errors)
