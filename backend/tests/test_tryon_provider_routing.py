"""Ensure direct Gemini generation cannot depend on Emergent image wrappers."""
import ast
from pathlib import Path


def test_direct_provider_is_selected_before_emergent_image_wrappers():
    source = (Path(__file__).resolve().parents[1] / "server.py").read_text()
    tree = ast.parse(source)
    function = next(
        node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "generate_customer_tryon"
    )
    direct_branch = next(
        node for node in function.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Name) and node.test.id == "GEMINI_API_KEY"
    )
    assert any(isinstance(n, ast.Return) for n in direct_branch.body)
    image_wrappers = [
        n for n in ast.walk(function)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name) and n.func.id == "ImageContent"
    ]
    assert image_wrappers
    assert min(n.lineno for n in image_wrappers) > direct_branch.end_lineno


def test_personal_tryon_prompt_requires_identity_and_outfit_fidelity():
    """Guard against future prompt edits silently weakening person/garment fidelity."""
    source = (Path(__file__).resolve().parents[1] / "server.py").read_text()
    tree = ast.parse(source)
    function = next(
        node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "generate_customer_tryon"
    )
    instruction = next(
        node for node in ast.walk(function)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "instruction" for t in node.targets)
    )
    prompt_literals = " ".join(
        node.value for node in ast.walk(instruction.value)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ).lower()
    for phrase in ("preserve the face", "skin tone", "body shape", "proportions",
                   "exact stated colours", "change clothing only", "not a guarantee"):
        assert phrase in prompt_literals
