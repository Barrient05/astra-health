import json
from pathlib import Path

ARCHIVO = Path(__file__).parent / "datos" / "reloj.json"
_cache = None


def datos():
    global _cache
    if _cache is None:
        if not ARCHIVO.exists():
            _cache = {}
        else:
            try:
                _cache = json.loads(ARCHIVO.read_text(encoding="utf-8"))
            except ValueError:
                print(f"[reloj] {ARCHIVO.name} no se pudo leer; se usan datos simulados.")
                _cache = {}
    return _cache or None


def hay():
    d = datos()
    return bool(d and d.get("dias"))


def linea_base():
    d = datos()
    return d.get("linea_base") if d else None


def del_dia(dia, total):
    d = datos()
    if not d or not d.get("dias"):
        return None
    dias = d["dias"]
    inicio = max(0, len(dias) - total)
    i = inicio + dia - 1
    return dias[i] if inicio <= i < len(dias) else None


def resumen():
    d = datos()
    if not d or not d.get("dias"):
        return None
    dias = d["dias"]
    return {"origen": d.get("origen", ""), "metodo": d.get("metodo", ""),
            "lecturas": d.get("lecturas_totales", 0), "dias": len(dias),
            "desde": dias[0]["fecha"], "hasta": dias[-1]["fecha"],
            "linea_base": d.get("linea_base")}
