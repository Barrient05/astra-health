import json
from datetime import date, timedelta
from pathlib import Path

import requests

from idiomas import N_, _

URL = "https://ccmc.gsfc.nasa.gov/DONKI-API/get/{tipo}"
ARCHIVO = Path(__file__).parent / "datos" / "donki.json"


def _pedir(tipo, inicio, fin):
    respuesta = requests.get(URL.format(tipo=tipo),
                             params={"startDate": inicio.isoformat(), "endDate": fin.isoformat()},
                             timeout=(8, 30))
    respuesta.raise_for_status()
    return respuesta.json() or []


def _explicar(error):
    if isinstance(error, requests.Timeout):
        return _("NASA tardó demasiado en responder. Intenta de nuevo o prueba con otra red.")
    if isinstance(error, requests.ConnectionError):
        return _("No hay conexión a internet o la red bloquea ccmc.gsfc.nasa.gov.")
    if isinstance(error, requests.HTTPError):
        return _("NASA respondió con error {codigo}.", codigo=error.response.status_code)
    if isinstance(error, ValueError):
        return _("NASA respondió algo que no son datos.")
    return type(error).__name__


def actualizar(dias=30):
    fin = date.today()
    inicio = fin - timedelta(days=dias)
    try:
        sep, flr = _pedir("SEP", inicio, fin), _pedir("FLR", inicio, fin)
    except Exception as e:
        return False, _explicar(e)

    eventos = []
    for e in sep:
        eventos.append({"tipo": "SEP",
                        "fecha": (e.get("eventTime") or "")[:16].replace("T", " "), "enlace": e.get("link")})
    for f in flr:
        clase = f.get("classType") or "?"
        eventos.append({"tipo": "FLR", "clase": clase, "fuerte": clase[:1] in ("M", "X"),
                        "fecha": (f.get("peakTime") or f.get("beginTime") or "")[:16].replace("T", " "),
                        "enlace": f.get("link")})
    eventos.sort(key=lambda x: x["fecha"], reverse=True)
    resultado = {"consultado": fin.isoformat(), "periodo": f"{inicio.isoformat()} a {fin.isoformat()}",
                 "sep": len(sep), "eventos": eventos}
    ARCHIVO.parent.mkdir(exist_ok=True)
    ARCHIVO.write_text(json.dumps(resultado, ensure_ascii=False), encoding="utf-8")
    return True, _("Datos de NASA DONKI actualizados: {n} eventos en los últimos {dias} días.", n=len(eventos), dias=dias)


def guardado():
    if ARCHIVO.exists():
        return json.loads(ARCHIVO.read_text(encoding="utf-8"))
    return None


from datetime import datetime, timedelta, timezone

HORAS_SEP = 72
HORAS_FLR = 48
DIAS_POR_EVENTO = 2
DOSIS_SEP_DIA = 30.0
FACTOR_ENTORNO = {"nave": 1.0, "rover": 1.0, "base_marte": 0.5, "estacion": 0.1}


def _fecha(texto):
    try:
        return datetime.strptime(texto[:16], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _clase(evento):
    return evento.get("clase") or (evento.get("nombre") or "").rsplit(" ", 1)[-1]


def fulguracion_fuerte(evento):
    clase = _clase(evento)
    try:
        return clase[:1] == "X" or (clase[:1] == "M" and float(clase[1:] or 0) >= 5)
    except ValueError:
        return clase[:1] == "X"


def ultimo_sep(donki):
    seps = [e for e in (donki or {}).get("eventos", []) if e["tipo"] == "SEP"]
    return seps[0] if seps else None


def alerta(donki, mision, ahora=None):
    modo = mision.get("clima_real") or {}
    if not modo.get("activo") or not donki:
        return None
    ahora = ahora or datetime.now(timezone.utc)
    aplicados = modo.get("aplicados", {})
    factor = FACTOR_ENTORNO.get(mision.get("entorno", "nave"), 1.0)
    pendiente = lambda clave: aplicados.get(clave, 0) < DIAS_POR_EVENTO
    horas = lambda e: (ahora - _fecha(e["fecha"])).total_seconds() / 3600

    seps = [e for e in donki.get("eventos", []) if e["tipo"] == "SEP" and _fecha(e["fecha"])]
    for e in seps:
        if horas(e) <= HORAS_SEP and pendiente(e["fecha"]):
            return {"tipo": "sep", "origen": "simulado" if e.get("simulado") else "real", "evento": e,
                    "clave": e["fecha"], "dosis_extra": DOSIS_SEP_DIA * factor}
    if modo.get("ensayo") and seps and pendiente("ensayo:" + seps[0]["fecha"]):
        return {"tipo": "sep", "origen": "ensayo", "evento": seps[0], "clave": "ensayo:" + seps[0]["fecha"],
                "dosis_extra": DOSIS_SEP_DIA * factor}
    for e in donki.get("eventos", []):
        if e["tipo"] == "FLR" and _fecha(e["fecha"]) and horas(e) <= HORAS_FLR and fulguracion_fuerte(e):
            return {"tipo": "flr", "origen": "simulado" if e.get("simulado") else "real",
                    "evento": {**e, "clase": _clase(e)}, "clave": None, "dosis_extra": 0}
    return None


TIPOS_SIMULADOS = {
    "sep_fuerte": {"tipo": "SEP", "nombre": N_("Tormenta de partículas solares (fuerte)"), "clase": None},
    "flr_x": {"tipo": "FLR", "nombre": N_("Fulguración solar clase X"), "clase": "X2.4"},
    "flr_m": {"tipo": "FLR", "nombre": N_("Fulguración solar clase M"), "clase": "M6.1"},
}
CUANDO_SIMULADO = {"2": N_("hace 2 horas"), "12": N_("hace 12 horas"), "48": N_("hace 2 días")}


def simular(clave, horas=2):
    plantilla = TIPOS_SIMULADOS.get(clave)
    if not plantilla:
        return False, _("Elige qué evento simular.")
    guardado_actual = guardado() or {"consultado": date.today().isoformat(), "periodo": "", "sep": 0, "eventos": []}
    momento = datetime.now(timezone.utc) - timedelta(hours=float(horas))
    evento = {"tipo": plantilla["tipo"], "clase": plantilla["clase"], "simulado": True,
              "fecha": momento.strftime("%Y-%m-%d %H:%M"), "enlace": None,
              "fuerte": plantilla["tipo"] == "FLR"}
    guardado_actual["eventos"] = [evento] + list(guardado_actual.get("eventos", []))
    guardado_actual["sep"] = sum(1 for e in guardado_actual["eventos"] if e["tipo"] == "SEP")
    ARCHIVO.parent.mkdir(exist_ok=True)
    ARCHIVO.write_text(json.dumps(guardado_actual, ensure_ascii=False), encoding="utf-8")
    return True, _("Evento simulado creado: {evento}, {cuando}. Está marcado como simulado en toda la app.",
                   evento=_(plantilla["nombre"]), cuando=_(CUANDO_SIMULADO.get(str(horas), _("hace {h} horas", h=horas))))


def quitar_simulados():
    datos_guardados = guardado()
    if not datos_guardados:
        return False, _("No hay eventos guardados.")
    antes = len(datos_guardados.get("eventos", []))
    datos_guardados["eventos"] = [e for e in datos_guardados["eventos"] if not e.get("simulado")]
    datos_guardados["sep"] = sum(1 for e in datos_guardados["eventos"] if e["tipo"] == "SEP")
    ARCHIVO.write_text(json.dumps(datos_guardados, ensure_ascii=False), encoding="utf-8")
    quitados = antes - len(datos_guardados["eventos"])
    if not quitados:
        return True, _("No había eventos simulados.")
    return True, _("Se quitó 1 evento simulado.") if quitados == 1 else _("Se quitaron {n} eventos simulados.", n=quitados)


def hay_simulados(donki):
    return any(e.get("simulado") for e in (donki or {}).get("eventos", []))


def consumir(mision, alerta_actual):
    modo = mision["clima_real"]
    clave = alerta_actual["clave"]
    modo["aplicados"][clave] = modo["aplicados"].get(clave, 0) + 1
    if clave.startswith("ensayo:") and modo["aplicados"][clave] >= DIAS_POR_EVENTO:
        modo["ensayo"] = False
