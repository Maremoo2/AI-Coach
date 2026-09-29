"""Code/schema/policy fingerprint for frozen coaching proposals."""
from importlib.resources import files

from . import __version__
from .contracts import digest


def manifest():
    modules = ("coaching.py", "contracts.py", "app_contracts.py", "engine.py", "features.py", "hq.py")
    code = {name: files("ai_coach").joinpath(name).read_text(encoding="utf-8").replace("\r\n", "\n") for name in modules}
    schemas = {p.name: p.read_text(encoding="utf-8").replace("\r\n", "\n")
               for p in files("ai_coach.schemas").iterdir() if p.name.endswith(".json")}
    return {"app_version": __version__, "critical_code_hash": digest(code), "schema_hash": digest(schemas),
            "auto_promotion": False, "plan_authority": "HQ"}
