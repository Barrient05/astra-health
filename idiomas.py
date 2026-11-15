import json
import re
import string
from pathlib import Path

from flask import g, has_request_context

IDIOMAS = {"es": "Español", "en": "English", "pt": "Português", "fr": "Français"}
POR_DEFECTO = "es"

CARPETA = Path(__file__).parent / "traducciones"
CATALOGOS = {}
for codigo in IDIOMAS:
    archivo = CARPETA / f"{codigo}.json"
    if archivo.exists():
        CATALOGOS[codigo] = json.loads(archivo.read_text(encoding="utf-8"))

FALTANTES = set()


def actual():
    return g.get("idioma", POR_DEFECTO) if has_request_context() else POR_DEFECTO


SEPARADORES = {"pt": (",", "."), "fr": (",", "\u202f")}


def numero(valor, formato=""):
    texto = format(valor, formato)
    if actual() in SEPARADORES:
        decimal, miles = SEPARADORES[actual()]
        texto = texto.replace(",", "§").replace(".", decimal).replace("§", miles)
    return texto


class _Formateador(string.Formatter):
    def format_field(self, valor, formato):
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            return numero(valor, formato)
        return super().format_field(valor, formato)


_formateador = _Formateador()


def _(texto, **valores):
    if not texto:
        return texto
    idioma = actual()
    if idioma != POR_DEFECTO:
        traduccion = CATALOGOS.get(idioma, {}).get(texto)
        if traduccion is None:
            FALTANTES.add(texto)
        else:
            texto = traduccion
    return _formateador.format(texto, **valores) if valores else texto


def N_(texto):
    return texto


def minuscula_inicial(texto):
    return texto if texto[:2].isupper() else texto[:1].lower() + texto[1:]


_CARPETA_JS = Path(__file__).parent / "static" / "js"
CLAVES_JS = sorted({m for js in ("pagina.js", "pulso_bluetooth.js")
                    for m in re.findall(r'\bt\("((?:[^"\\]|\\.)*)"', (_CARPETA_JS / js).read_text(encoding="utf-8"))})


def textos_js():
    return {clave: _(clave) for clave in CLAVES_JS}
