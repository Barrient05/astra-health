import ast
import json
import re
import string
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import catalogo_acerca
import datos
import clima
import entornos
import riesgos_nasa
import rutina
import salud
from fuentes import FUENTES, TIPOS
from guia import GUIA
from idiomas import CARPETA, IDIOMAS, POR_DEFECTO


def textos_del_codigo():
    claves = set()
    patron_py = re.compile(r'''\b_\(\s*(["'])((?:(?!\1)[^\\]|\\.)*)\1''')
    for archivo in list(RAIZ.glob("*.py")) + list((RAIZ / "templates").rglob("*.html")):
        for _comilla, texto in patron_py.findall(archivo.read_text(encoding="utf-8")):
            claves.add(texto.encode().decode("unicode_escape").encode("latin-1").decode("utf-8") if "\\" in texto else texto)
    for js in (RAIZ / "static" / "js").glob("*.js"):
        if js.name.startswith("chart"):
            continue
        claves.update(re.findall(r'\bt\("((?:[^"\\]|\\.)*)"', js.read_text(encoding="utf-8")))
    return claves


def textos_de_los_datos():
    claves = set()
    for nombre, unidad, _rango, _dec in datos.INDICADORES.values():
        claves.update([nombre, unidad])
    for nombre, unidad in datos.PRUEBAS.values():
        claves.update([nombre, unidad])
    claves.update(datos.SISTEMAS.values())
    claves.update(datos.SINTOMAS.values())
    claves.update(p[0] for p in datos.PLANES.values())
    claves.update(datos.DESCRIPCION_PLAN.values())
    claves.update(datos.ECO.values())
    for e in entornos.ENTORNOS.values():
        claves.update([e["nombre"], e["gravedad_txt"], e["retraso_txt"], e["nota"]])
    claves.update(f["nombre"] for f in entornos.FASES)
    claves.update(t["nombre"] for t in clima.TIPOS_SIMULADOS.values())
    claves.update(clima.CUANDO_SIMULADO.values())
    claves.update(r[0] for r in riesgos_nasa.RIESGOS.values())
    claves.update(nota for _estado, nota in riesgos_nasa.COBERTURA.values())
    claves.update(catalogo_acerca.RIDGE.values())
    claves.update(z["zona"] for z in catalogo_acerca.ZONAS)
    for grupo in (rutina.TAREAS_BASE, rutina.TAREAS_PROGRAMADAS):
        for titulo, detalle, _guia, _puntos in grupo.values():
            claves.update([titulo, detalle])
    for _tid, titulo, detalle, _guia, _puntos in rutina.TAREAS_DE_PLAN.values():
        claves.update([titulo, detalle])
    for nombre, desc, _meta in rutina.INSIGNIAS.values():
        claves.update([nombre, desc])
    claves.update(a["rol"] for a in datos.TRIPULACION_BASE)
    claves.update(n[2] for n in salud.NIVELES)
    claves.update(salud.ESCALAMIENTO.values())
    claves.update(e["corto"] for e in salud.ETIQUETAS_MAPA.values())
    claves.update(TIPOS.values())
    for g in GUIA.values():
        for campo in ("titulo", "equipo", "frecuencia", "por_que", "efecto_vuelo", "tripulacion", "tierra"):
            claves.add(g[campo])
        claves.update(g["como"])
        claves.update(g["prevencion"])
    usadas = set(k for v in datos.FUENTES_INDICADOR.values() for k in v)
    usadas |= set(k for g in GUIA.values() for k in g.get("fuentes", []))
    texto_codigo = "".join(p.read_text(encoding="utf-8") for p in [RAIZ / "salud.py", RAIZ / "app.py", RAIZ / "templates" / "index.html"])
    usadas |= {k for k in FUENTES if f'"{k}"' in texto_codigo}
    claves.update(FUENTES[k]["dato"] for k in usadas)
    espanol = re.compile(r"\b(y|con|por|del|la|estudio|financiado|Agencia|Equipo|Berlín)\b")
    claves.update(FUENTES[k]["autor"] for k in usadas if espanol.search(FUENTES[k]["autor"]))
    return {c for c in claves if c and re.search(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]{2}", c)}


def textos_de_argumentos():
    claves = set()
    cadena = lambda n: n.value if isinstance(n, ast.Constant) and isinstance(n.value, str) else None
    for nodo in ast.walk(ast.parse((RAIZ / "salud.py").read_text(encoding="utf-8"))):
        if isinstance(nodo, ast.Call) and getattr(nodo.func, "id", "") in ("agregar", "tarjeta") and nodo.args:
            if nodo.func.id == "tarjeta":
                claves.update([cadena(nodo.args[0]), cadena(nodo.args[2])])
            else:
                claves.add(cadena(nodo.args[1]))
                for arg in nodo.args:
                    if isinstance(arg, ast.List):
                        claves.update(cadena(e) for e in arg.elts)
    claves.discard(None)
    claves -= set(FUENTES)
    for nodo in ast.walk(ast.parse((RAIZ / "app.py").read_text(encoding="utf-8"))):
        if isinstance(nodo, ast.Tuple) and len(nodo.elts) == 2 and cadena(nodo.elts[0]) in FUENTES:
            claves.add(cadena(nodo.elts[1]))
    return {c for c in claves if c and re.search(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]{2}", c)}


def todas():
    return textos_del_codigo() | textos_de_los_datos() | textos_de_argumentos()


def marcadores(texto):
    return sorted(f"{{{n}{':' + f if f else ''}}}" for _l, n, f, _c in string.Formatter().parse(texto) if n is not None)


if __name__ == "__main__":
    claves = todas()
    print(f"Textos en español: {len(claves)}")
    hay_error = False
    for codigo, nombre in IDIOMAS.items():
        if codigo == POR_DEFECTO:
            continue
        archivo = CARPETA / f"{codigo}.json"
        catalogo = json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else {}
        faltan = sorted(claves - set(catalogo))
        sobran = sorted(set(catalogo) - claves)
        malos = [k for k in claves & set(catalogo) if marcadores(k) != marcadores(catalogo[k])]
        print(f"\n{nombre} ({codigo}.json): {len(catalogo)} traducciones, faltan {len(faltan)}, sobran {len(sobran)}, marcadores distintos {len(malos)}")
        for k in faltan[:15]:
            print("  FALTA:", k[:100])
        for k in malos[:15]:
            print("  MARCADORES:", k[:80], "→", marcadores(catalogo[k]))
        hay_error |= bool(faltan or malos)
    sys.exit(1 if hay_error else 0)
