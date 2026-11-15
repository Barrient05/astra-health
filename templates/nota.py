from datos import ECO, INDICADORES, NOMBRE_APP, PLANES, SINTOMAS, efecto_planes
from idiomas import _, minuscula_inicial, numero

ORDEN = {"critico": 0, "atencion": 1, "vigilar": 2, "normal": 3}
SIGNOS = ["fc", "pa_sis", "spo2", "temp", "sueno", "agua", "calorias", "resistencia", "aerobico", "animo", "estres"]
A_QUIEN = {"tu": "autocuidado", "tripulacion": "tripulación y oficial médico", "tierra": "médicos de vuelo en Tierra"}


def _valor(clave, reg, base):
    nombre, unidad, (lo, hi), dec = INDICADORES[clave]
    v = reg.get(clave)
    if v is None:
        return None
    if clave == "pa_sis":
        txt = _("Presión arterial {sis}/{dia} mmHg (base {bs}/{bd})", sis=reg["pa_sis"], dia=reg["pa_dia"], bs=base["pa_sis"], bd=base["pa_dia"])
        alta = v > hi or reg["pa_dia"] > INDICADORES["pa_dia"][2][1]
        return txt + (" ▲" if alta else "")
    txt = f"{_(nombre)} {numero(v, f'.{dec}f')} {_(unidad)}".replace(" /10", "/10")
    if clave == "calorias":
        txt += " (" + _("meta {v}", v=numero(base["calorias"], ",")) + ")"
    elif base.get(clave) is not None and clave not in ("agua", "resistencia", "aerobico"):
        txt += " (" + _("base {v}", v=numero(base[clave], f".{dec}f")) + ")"
    if not lo <= v <= hi:
        txt += " ▲" if v > hi else " ▼"
    return txt


def generar(astro, dia, m, sistemas, general, protocolos, radiacion, entorno):
    reg = next(r for r in astro["registros"] if r["dia"] == dia)
    base = {**astro["linea_base"], "temp": round(m["temp_base"], 1)}

    sintomas = [minuscula_inicial(_(SINTOMAS[s])) for s in reg.get("sintomas", []) if s in SINTOMAS]
    subjetivo = [_("Refiere: {sintomas}.", sintomas="; ".join(sintomas)) if sintomas else _("Sin síntomas referidos hoy.")]
    if reg.get("nota"):
        subjetivo.append(_("En sus palabras: «{nota}»", nota=reg["nota"].strip()))

    objetivo = [t for t in (_valor(c, reg, base) for c in SIGNOS) if t]
    if m["reaccion"] is not None:
        objetivo.append(_("Prueba de reacción (día {dia}): {ms} ms, {lapsos} lapsos (base {base} ms).",
                          dia=m["dia_reaccion"], ms=m["reaccion"], lapsos=m["lapsos"] or 0, base=base["reaccion"]))
    if m["orto"]:
        o = m["orto"]
        objetivo.append(_("Prueba de pie (día {dia}): presión −{sis:.0f}/−{diast:.0f} mmHg, pulso +{fc:.0f} lpm.",
                          dia=m["dia_orto"], sis=o["caida_sis"], diast=o["caida_dia"], fc=o["sube_fc"]))
    if m["peso"] is not None:
        objetivo.append(_("Peso (día {dia}): {peso} kg, {pct:.1f} % menos que al inicio.", dia=m["dia_peso"], peso=m["peso"], pct=m["perdida_peso_pct"]))
    if m["eco"]:
        objetivo.append(_("Ultrasonido de la vena yugular (día {dia}): {resultado}.", dia=m["dia_eco"], resultado=minuscula_inicial(_(ECO[m["eco"]]))))
    objetivo.append(_("Dosis acumulada {dosis} mSv ({pct} % del límite de carrera de {limite} mSv).",
                      dosis=radiacion["acumulada"], pct=radiacion["porcentaje"], limite=radiacion["limite"]))
    objetivo.append(_("Pérdida ósea estimada {pct:.1f} %.", pct=m["osea"]))

    evaluacion = [_("Estado general {puntaje}/100 ({nivel}).", puntaje=general["puntaje"], nivel=general["nivel"]["nombre"].lower())]
    en_riesgo = sorted([s for s in sistemas if s["nivel"]["clave"] != "normal"], key=lambda s: (ORDEN[s["nivel"]["clave"]], -s["puntaje"]))
    for s in en_riesgo[:5]:
        linea = f"{s['nombre']}: {s['puntaje']} ({s['nivel']['nombre'].lower()})"
        if s["a30"] - s["puntaje"] >= 5:
            linea += "; " + _("sube a {n} en 30 días si sigue igual", n=s["a30"])
        evaluacion.append(linea + ".")
    importantes = [p for p in protocolos if p["nivel"] in ("atencion", "critico") or p["avisar"] == "tierra"]
    for p in importantes:
        evaluacion.append(_("Alerta ({nivel}): {titulo}.", nivel=p["nombre_nivel"].lower(), titulo=minuscula_inicial(p["titulo"])) + " " + p["motivo"])

    plan = [_("{titulo}: {paso} (avisa a: {quien}).", titulo=p["titulo"], paso=p["pasos"][0].rstrip("."), quien=_(A_QUIEN[p["avisar"]]))
            for p in importantes]
    for pl in astro.get("planes", []):
        if pl["inicio"] <= dia < pl["inicio"] + pl["duracion"]:
            plan.append(_("Plan activo: {plan} (días {inicio} a {fin}, adherencia {pct} %).", plan=minuscula_inicial(_(PLANES[pl["tipo"]][0])),
                          inicio=pl["inicio"], fin=pl["inicio"] + pl["duracion"] - 1, pct=round(pl["adherencia"] * 100)))
    if not plan:
        plan.append(_("Continuar rutina y monitoreo habitual."))

    pide_tierra = any(p["avisar"] == "tierra" for p in protocolos)
    encabezado = {
        "astronauta": f"{astro['nombre']} ({_(astro['rol'])})", "dia": dia,
        "entorno": _(entorno["nombre"]), "retraso": _(entorno["retraso_txt"]),
        "prioridad": _("Requiere revisión de médicos de vuelo") if pide_tierra else _("Informativa"),
        "urgente": pide_tierra,
    }
    secciones = [("S", _("Subjetivo"), subjetivo), ("O", _("Objetivo"), objetivo),
                 ("A", _("Evaluación"), evaluacion), ("P", _("Plan"), plan)]
    lineas = [_("NOTA CLÍNICA · {astronauta} · Día {dia}", astronauta=encabezado["astronauta"], dia=dia),
              _("{entorno} · retraso de comunicación {retraso}", entorno=encabezado["entorno"], retraso=encabezado["retraso"]),
              _("Prioridad: {prioridad}", prioridad=encabezado["prioridad"]), ""]
    for letra, titulo, items in secciones:
        lineas += [f"{letra} · {titulo}", *[f"- {t}" for t in items], ""]
    lineas.append(_("Generada por {app} con los datos del registro. Revísala antes de enviarla.", app=NOMBRE_APP))
    texto = "\n".join(lineas)
    return {"encabezado": encabezado, "secciones": [{"letra": l, "titulo": t, "lineas": i} for l, t, i in secciones],
            "texto": texto, "caracteres": len(texto)}
