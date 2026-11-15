import ast
import inspect
import math
import os
import textwrap
from collections import defaultdict
from uuid import uuid4
from pathlib import Path

from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, session, url_for

import clima
import datos
import reloj
import tripulacion
import nota as nota_clinica
import rutina as rutina_diaria
from dictado import interpretar
from entornos import ENTORNOS, entorno_de, fase_del_dia
from fuentes import FUENTES, TIPOS
from guia import GUIA
from idiomas import IDIOMAS, POR_DEFECTO, _, minuscula_inicial, numero, textos_js
from catalogo_acerca import RIDGE, SISTEMA_RIDGE, ZONAS
from riesgos_nasa import COBERTURA, RIESGOS, URL_HRP, URL_VTE, riesgos_de
from salud import ETIQUETAS_MAPA, LIMITE_RADIACION, Analisis, nivel_de

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "orbita-curso"

MULTIUSUARIO = os.environ.get("ORBITA_MULTIUSUARIO") == "1"
if MULTIUSUARIO:
    datos.usar_sesiones(lambda: session.get("sid"))


@app.before_request
def elegir_idioma():
    pedido = request.args.get("lang")
    if pedido in IDIOMAS:
        session["idioma"] = pedido
    g.idioma = session.get("idioma", POR_DEFECTO)
    if MULTIUSUARIO and "sid" not in session:
        session["sid"] = uuid4().hex
        session.permanent = False
        datos.limpiar_sesiones()


@app.context_processor
def herramientas_de_plantilla():
    return {"_": _, "idioma": g.idioma, "idiomas": IDIOMAS, "fuentes": FUENTES, "textos_js": textos_js(),
            "app_nombre": datos.NOMBRE_APP}


app.jinja_env.filters["minuscula"] = minuscula_inicial
app.jinja_env.filters["numero"] = numero


def buscar_astronauta(estado, aid):
    for a in estado["tripulacion"]:
        if a["id"] == aid:
            return a
    return None


def elegir_astronauta(estado):
    aid = request.args.get("astronauta") or request.form.get("astronauta") or session.get("astronauta")
    astro = buscar_astronauta(estado, aid)
    if astro is None:
        dia = estado["mision"]["dia"]
        astro = max(estado["tripulacion"], key=lambda a: Analisis.general(Analisis(a).puntajes(dia)))
    session["astronauta"] = astro["id"]
    return astro


def tarjetas_tripulacion(estado, dia):
    tarjetas = []
    for a in estado["tripulacion"]:
        pts = Analisis(a).puntajes(dia)
        general = Analisis.general(pts)
        peor = max(pts, key=pts.get)
        tarjetas.append({"id": a["id"], "nombre": a["nombre"], "rol": _(a["rol"]), "general": general,
                         "nivel": nivel_de(general), "peor": _(datos.SISTEMAS[peor]), "puntajes": pts})
    return tarjetas


def fuentes_usadas():
    usos = defaultdict(list)
    for clave, claves_fuente in datos.FUENTES_INDICADOR.items():
        for f in claves_fuente:
            usos[f].append(_("Registro: rango de {indicador}", indicador=minuscula_inicial(_(datos.INDICADORES[clave][0]))))
    for entrada in GUIA.values():
        for f in entrada.get("fuentes", []):
            usos[f].append(_("Guía: {medicion}", medicion=minuscula_inicial(_(entrada["titulo"]))))
    texto_reglas = (Path(__file__).parent / "salud.py").read_text(encoding="utf-8")
    for f in FUENTES:
        if f'"{f}"' in texto_reglas:
            usos[f].append(_("Reglas de Qué hacer ahora"))
    for entorno in ENTORNOS.values():
        for f in entorno["fuentes"]:
            usos[f].append(_("Entorno: {nombre}", nombre=minuscula_inicial(_(entorno["nombre"]))))
    for f, uso in [("nasa_radiacion_std", "Radiación: límite de 600 mSv"), ("nasa_rad_crucero", "Radiación: 1.8 mSv al día"),
                   ("nasa_donki", "Radiación: eventos solares reales"), ("reporte_equipo", "Investigación del equipo"),
                   ("reporte_equipo2", "Investigación del equipo"), ("nasa_hueso", "Pérdida ósea de 1.5 % al mes"),
                   ("nasa_ridge", "Cómo funciona: los 5 peligros RIDGE"), ("astra_health", "Dictado y nota clínica"),
                   ("reloj_personal", "Pulso en reposo medido, no simulado"),
                   ("inegi_salud", "Cómo funciona: el mismo problema en la Tierra"),
                   ("soap", "Nota clínica en formato SOAP")]:
        if f in FUENTES:
            usos[f].append(_(uso))
    grupos = []
    for tipo, nombre in TIPOS.items():
        lista = [{"id": k, **f, "usos": sorted(set(usos[k]))} for k, f in FUENTES.items() if f["tipo"] == tipo and k in usos]
        if lista:
            grupos.append({"nombre": _(nombre), "fuentes": lista})
    return grupos


def analizar(astro, mision, dia, sistema_elegido=None):
    an = Analisis(astro)
    m = an.metricas(dia)
    puntajes = an.puntajes(dia, m)
    general = Analisis.general(puntajes)
    es_hoy = dia == mision["dia"]
    alerta = clima.alerta(clima.guardado(), mision) if es_hoy else None
    entorno_clave = an.por_dia[dia].get("entorno", mision["entorno"])
    dias_hist, series = an.historial(dia)
    sistemas = []
    for clave, nombre in datos.SISTEMAS.items():
        sin_plan, con_plan = an.pronostico(dia, series[clave], clave)
        sistemas.append({"clave": clave, "nombre": _(nombre), "puntaje": puntajes[clave], "nivel": nivel_de(puntajes[clave]),
                         "a30": round(sin_plan[-1]), "a30_plan": round(con_plan[-1])})
    dosis = an.dosis[dia]
    fase = fase_del_dia(dia, entorno_clave)
    tasa = fase_del_dia(mision["dias_totales"], mision["entorno"])["tasa"]
    radiacion = {"acumulada": round(dosis), "porcentaje": round(100 * dosis / LIMITE_RADIACION, 1),
                 "hoy": an.por_dia[dia]["dosis"], "limite": LIMITE_RADIACION, "ritmo": tasa,
                 "fase": _(fase["nombre"]), "fase_inicio": fase["inicio"], "fase_fin": min(fase["fin"], mision["dias_totales"]),
                 "fin": round(dosis + tasa * (mision["dias_totales"] - dia)), "anios_tierra": round(dosis / 3)}
    return {"an": an, "m": m, "puntajes": puntajes, "general": {"puntaje": general, "nivel": nivel_de(general)},
            "alerta": alerta, "entorno": ENTORNOS[entorno_clave], "dias_hist": dias_hist, "series": series,
            "sistemas": sistemas, "radiacion": radiacion, "es_hoy": es_hoy, "fase": fase,
            "protocolos": an.protocolos(dia, entorno_clave, alerta, m)}


def linea_de_mision(astro, mision, dia_visto):
    total, hoy = mision["dias_totales"], mision["dia"]
    por_dia = {r["dia"]: r for r in astro["registros"]}
    entorno_de_dia = [por_dia[d].get("entorno", "nave") if d in por_dia else mision["entorno"] for d in range(1, total + 1)]
    tramos, inicio = [], 1
    for d in range(2, total + 2):
        if d > total or entorno_de_dia[d - 1] != entorno_de_dia[inicio - 1]:
            tramos.append({"inicio": inicio, "fin": d - 1, "nombre": _(ENTORNOS[entorno_de_dia[inicio - 1]]["nombre"]),
                           "left": 100 * (inicio - 1) / total, "width": 100 * (d - inicio) / total})
            inicio = d
    eventos = [{"dia": d, "left": 100 * (d - 1) / total, "real": bool(por_dia.get(d, {}).get("sep_real"))}
               for d in range(1, hoy + 1) if datos.EVENTO_SOLAR[0] <= d <= datos.EVENTO_SOLAR[1] or por_dia.get(d, {}).get("sep_real")]
    return {"tramos": tramos, "eventos": eventos, "pasado": 100 * hoy / total, "visto": 100 * (dia_visto - 1) / total}


def pintar_mapa(sistemas, elegido):
    zonas, etiquetas = {}, []
    for s in sistemas:
        color = s["nivel"]["color"]
        clave_nivel = s["nivel"]["clave"]
        if clave_nivel == "normal":
            estilo = f"--color-zona: {color}; opacity: 0.5"
        else:
            estilo = f"--color-zona: {color}; filter: drop-shadow(0 0 {3 + s['puntaje'] // 10}px {color})"
        zonas[s["clave"]] = {"estilo": estilo, "nivel": clave_nivel}
        if clave_nivel != "normal" or s["clave"] == elegido:
            e = ETIQUETAS_MAPA[s["clave"]]
            ajuste = 6 if e["lado"] == "end" else -6
            etiquetas.append({**e, "corto": _(e["corto"]), "puntaje": s["puntaje"], "color": color, "clave": s["clave"],
                              "fin_linea": (e["texto"][0] + ajuste, e["texto"][1] - 6)})
    return zonas, etiquetas


def anillo_mision(dia, total):
    circunferencia = 2 * math.pi * 262
    angulo = 2 * math.pi * dia / total - math.pi / 2
    return {"avance": round(circunferencia * dia / total, 1), "total": round(circunferencia, 1),
            "hoy": (round(280 + 262 * math.cos(angulo), 1), round(280 + 262 * math.sin(angulo), 1))}


def entorno_nave(an, dia):
    co2 = an.prom(dia, "co2")
    ruido = an.prom(dia, "ruido")
    lecturas = []
    if co2 is not None:
        lecturas.append({"clave": "co2", "nombre": _("CO₂ en cabina"), "valor": round(co2, 1), "unidad": "mmHg",
                         "limite": _("límite de NASA: 3"),
                         "nivel": "atencion" if co2 >= 3.0 else "vigilar" if co2 >= 2.5 else "bien"})
    if ruido is not None:
        lecturas.append({"clave": "ruido", "nombre": _("Ruido al dormir"), "valor": round(ruido), "unidad": "dBA",
                         "limite": _("diseño: 50"),
                         "nivel": "atencion" if ruido >= 60 else "vigilar" if ruido > 50 else "bien"})
    return lecturas


def contar_protocolos():
    fuente = textwrap.dedent(inspect.getsource(Analisis.protocolos))
    cuerpo = ast.parse(fuente).body[0]
    return sum(1 for n in ast.walk(cuerpo)
               if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "agregar")


PROTOCOLOS_TOTALES = contar_protocolos()


def cifras_de_portada(estado):
    medidas = reloj.resumen()
    por_tipo = defaultdict(int)
    for f in FUENTES.values():
        por_tipo[f.get("tipo", "estudio")] += 1
    tipos = sorted(((TIPOS.get(k, k), n) for k, n in por_tipo.items()), key=lambda x: -x[1])
    return {
        "dias": datos.DIAS_TOTALES,
        "dia": estado["mision"]["dia"],
        "tripulantes": len(estado["tripulacion"]),
        "indicadores": len(datos.INDICADORES),
        "sistemas": len(datos.SISTEMAS),
        "protocolos": PROTOCOLOS_TOTALES,
        "fuentes": len(FUENTES),
        "tipos": tipos,
        "lecturas": medidas.get("lecturas", 0),
        "dias_reloj": medidas.get("dias", 0),
        "linea_base": medidas.get("linea_base", 0),
        "desde": medidas.get("desde", ""),
        "hasta": medidas.get("hasta", ""),
    }


@app.get("/portada")
def portada():
    session.pop("vio_portada", None)
    return render_template("portada.html", pagina="portada", cifras=cifras_de_portada(datos.cargar()))


@app.get("/entrar")
def entrar():
    session["vio_portada"] = True
    return redirect(url_for("panel"))


@app.route("/")
def panel():
    estado = datos.cargar()
    if not session.get("vio_portada"):
        return render_template("portada.html", pagina="portada", cifras=cifras_de_portada(estado))
    mision = estado["mision"]
    astro = elegir_astronauta(estado)
    dia = max(1, min(mision["dia"], request.args.get("dia", mision["dia"], type=int)))
    r = analizar(astro, mision, dia)
    an, puntajes = r["an"], r["puntajes"]

    elegido = request.args.get("sistema")
    if elegido not in datos.SISTEMAS:
        elegido = max(puntajes, key=puntajes.get)
    sin_plan, con_plan = an.pronostico(dia, r["series"][elegido], elegido)

    zonas, etiquetas = pintar_mapa(r["sistemas"], elegido)
    anillo = anillo_mision(dia, mision["dias_totales"])

    nombre_elegido = _(datos.SISTEMAS[elegido])
    resumen = _("{sistema}: {hoy} hoy. Si sigue la tendencia, llegaría a {a30} en 30 días.",
                sistema=nombre_elegido, hoy=puntajes[elegido], a30=round(sin_plan[-1]))
    if astro["planes"]:
        resumen += " " + _("Con tus planes: {a30}.", a30=round(con_plan[-1]))
    grafica = {"dias": r["dias_hist"], "historial": r["series"][elegido], "futuro": list(range(dia + 1, dia + 31)),
               "sin_plan": sin_plan, "con_plan": con_plan, "hay_planes": bool(astro["planes"]), "nombre": nombre_elegido}
    resumen_rutina = rutina_diaria.resumen(astro, dia, mision["dia"])
    fuera_de_rango = [f for f in an.indicadores(dia) if f["fuera"]]
    donki = clima.guardado()
    tarjetas = tarjetas_tripulacion(estado, dia)
    return render_template(
        "index.html", pagina="panel", rutina=resumen_rutina, fuera_de_rango=fuera_de_rango,
        mision=mision, dia=dia, tarjetas=tarjetas, astro=astro,
        general=r["general"]["puntaje"], nivel_general=r["general"]["nivel"], signos=an.signos(dia),
        sistemas=r["sistemas"], elegido=elegido, nombre_elegido=nombre_elegido, riesgos=riesgos_de(elegido),
        protocolos=r["protocolos"], zonas=zonas, etiquetas=etiquetas, anillo=anillo, radiacion=r["radiacion"],
        grafica=grafica, resumen=resumen, entornos=ENTORNOS, entorno=entorno_de(mision), es_hoy=r["es_hoy"],
        ridge=RIDGE, sistema_ridge=SISTEMA_RIDGE, simulados=clima.hay_simulados(donki),
        tipos_simulados=clima.TIPOS_SIMULADOS, cuando_simulado=clima.CUANDO_SIMULADO,
        donki=donki, alerta=r["alerta"], modo_clima=mision["clima_real"], sep_ensayo=clima.ultimo_sep(donki),
        linea=linea_de_mision(astro, mision, dia), nave=entorno_nave(an, dia),
        equipo=tripulacion.resumen(
            tripulacion.estado(tarjetas, {x["id"]: x["rol"] for x in estado["tripulacion"]}), astro["id"]),
        planes_nombre={k: v[0] for k, v in datos.PLANES.items()},
    )


@app.post("/avanzar")
def avanzar():
    estado = datos.cargar()
    mision = estado["mision"]
    donki = clima.guardado()
    for _vuelta in range(int(request.form.get("dias", 1))):
        if mision["dia"] >= mision["dias_totales"]:
            break
        for a in estado["tripulacion"]:
            a.setdefault("tareas", {}).setdefault(str(mision["dia"]), [])
        alerta = clima.alerta(donki, mision)
        extra = alerta["dosis_extra"] if alerta and alerta["tipo"] == "sep" else 0.0
        mision["dia"] += 1
        for a in estado["tripulacion"]:
            a["registros"].append(datos.generar_dia(a, mision["dia"], entorno=mision["entorno"], sep_real=extra))
        if extra:
            clima.consumir(mision, alerta)
    datos.guardar(estado)
    return redirect(url_for("panel"))


@app.post("/entorno")
def cambiar_entorno():
    estado = datos.cargar()
    clave = request.form.get("entorno")
    if clave in ENTORNOS:
        estado["mision"]["entorno"] = clave
        datos.guardar(estado)
        flash(_("Entorno cambiado: {nombre}. Se aplica a los días que avances desde hoy.", nombre=minuscula_inicial(_(ENTORNOS[clave]["nombre"]))))
    return redirect(url_for("panel"))


@app.post("/clima-real")
def clima_real():
    estado = datos.cargar()
    modo = estado["mision"]["clima_real"]
    accion = request.form.get("accion")
    if accion == "activar":
        modo["activo"] = True
        flash(_("Clima espacial real activado: las tormentas solares que reporte NASA DONKI llegan a la misión."))
    elif accion == "apagar":
        modo.update(activo=False, ensayo=False)
        flash(_("Clima espacial real apagado."))
    elif accion == "ensayo":
        if clima.ultimo_sep(clima.guardado()):
            modo.update(activo=True, ensayo=True)
            modo["aplicados"] = {k: v for k, v in modo["aplicados"].items() if not k.startswith("ensayo:")}
            flash(_("Ensayo iniciado con el último evento real. Avanza la misión para ver la dosis con y sin refugio."))
        else:
            flash(_("No hay eventos de partículas solares en la última consulta: no se puede ensayar."))
    datos.guardar(estado)
    return redirect(url_for("panel") + "#radiacion")


@app.get("/api/dia/<int:dia>")
def api_dia(dia):
    estado = datos.cargar()
    mision = estado["mision"]
    astro = elegir_astronauta(estado)
    dia = max(1, min(mision["dia"], dia))
    r = analizar(astro, mision, dia)
    elegido = request.args.get("sistema")
    if elegido not in datos.SISTEMAS:
        elegido = max(r["puntajes"], key=r["puntajes"].get)
    zonas, etiquetas = pintar_mapa(r["sistemas"], elegido)
    sin_plan, con_plan = r["an"].pronostico(dia, r["series"][elegido], elegido)
    nombre_elegido = _(datos.SISTEMAS[elegido])
    resumen = _("{sistema}: {hoy} hoy. Si sigue la tendencia, llegaría a {a30} en 30 días.",
                sistema=nombre_elegido, hoy=r["puntajes"][elegido], a30=round(sin_plan[-1]))
    if astro["planes"]:
        resumen += " " + _("Con tus planes: {a30}.", a30=round(con_plan[-1]))
    return jsonify({
        "dia": dia, "es_hoy": r["es_hoy"],
        "titulo_dia": _("Día {dia} de {total}", dia=dia, total=mision["dias_totales"]),
        "signos": r["an"].signos(dia), "sistemas": r["sistemas"], "elegido": elegido,
        "general": r["general"]["puntaje"], "nivel_general": r["general"]["nivel"],
        "zonas": zonas, "etiquetas": etiquetas, "anillo": anillo_mision(dia, mision["dias_totales"]),
        "radiacion": r["radiacion"], "protocolos": len(r["protocolos"]),
        "nombre_elegido": nombre_elegido, "resumen": resumen, "riesgos": riesgos_de(elegido),
        "titulo_tendencia": _("Tendencia y pronóstico: {sistema}", sistema=minuscula_inicial(nombre_elegido)),
        "grafica": {"dias": r["dias_hist"], "historial": r["series"][elegido], "futuro": list(range(dia + 1, dia + 31)),
                    "sin_plan": sin_plan, "con_plan": con_plan, "hay_planes": bool(astro["planes"]),
                    "nombre": _(datos.SISTEMAS[elegido])},
    })


@app.post("/clima-simular")
def clima_simular():
    if request.form.get("accion") == "quitar":
        _ok, mensaje = clima.quitar_simulados()
    else:
        _ok, mensaje = clima.simular(request.form.get("tipo"), request.form.get("horas", "2"))
        estado = datos.cargar()
        estado["mision"]["clima_real"]["activo"] = True
        datos.guardar(estado)
    flash(mensaje)
    return redirect(url_for("panel") + "#radiacion")


@app.post("/donki")
def actualizar_donki():
    ok, mensaje = clima.actualizar()
    flash(mensaje if ok else _("No se pudo consultar NASA DONKI: {motivo} Se muestra la última consulta guardada.", motivo=mensaje))
    return redirect(url_for("panel") + "#radiacion")


@app.post("/reiniciar")
def reiniciar():
    dia = max(1, min(datos.DIAS_TOTALES, request.form.get("dia", datos.DIA_INICIAL, type=int)))
    datos.reiniciar(dia)
    session.pop("astronauta", None)
    flash(_("Simulación reiniciada en el día {dia}.", dia=dia) if dia > 1
          else _("Simulación reiniciada en el día 1: la misión empieza desde cero."))
    return redirect(url_for("panel"))


CAMPOS_REGISTRO = ([c for c in datos.INDICADORES if c not in datos.DEL_VEHICULO]
                   + ["peso"] + list(datos.PRUEBAS))


@app.route("/registro", methods=["GET", "POST"])
def registro():
    estado = datos.cargar()
    mision = estado["mision"]
    astro = elegir_astronauta(estado)
    dia = mision["dia"]
    hoy = next(r for r in astro["registros"] if r["dia"] == dia)

    if request.method == "POST":
        nuevos, errores = {}, []
        for clave in CAMPOS_REGISTRO:
            texto = request.form.get(clave, "").strip().replace(",", ".")
            if texto == "":
                nuevos[clave] = None if clave in ("peso", *datos.PRUEBAS) else hoy.get(clave)
                continue
            lo, hi = datos.LIMITES[clave]
            try:
                valor = float(texto)
            except ValueError:
                valor = None
            if valor is None or not lo <= valor <= hi:
                nombre = (datos.INDICADORES.get(clave) or datos.PRUEBAS.get(clave) or ("Peso",))[0]
                errores.append(_("{campo}: escribe un valor entre {min} y {max}.", campo=_(nombre), min=lo, max=hi))
                continue
            dec = datos.INDICADORES[clave][3] if clave in datos.INDICADORES else (1 if clave == "peso" else 0)
            nuevos[clave] = round(valor, dec) if dec else int(round(valor))
        if errores:
            for e in errores:
                flash(e)
            return redirect(url_for("registro"))
        hoy.update(nuevos)
        hoy["eco"] = request.form.get("eco") if request.form.get("eco") in datos.ECO else None
        hoy["nota"] = request.form.get("nota", "")[:500]
        hoy["dispositivo"] = request.form.get("dispositivo", "")[:60]
        hoy["sintomas"] = [s for s in request.form.getlist("sintomas") if s in datos.SINTOMAS]
        hoy["fuente"] = "registro"
        datos.guardar(estado)
        flash(_("Registro de {nombre} guardado para el día {dia}.", nombre=astro["nombre"], dia=dia))
        return redirect(url_for("panel", astronauta=astro["id"]))

    return render_template(
        "registro.html", pagina="registro", mision=mision, astro=astro, hoy=hoy, tarjetas=tarjetas_tripulacion(estado, dia),
        indicadores=datos.INDICADORES, pruebas=datos.PRUEBAS, limites=datos.LIMITES, sintomas=datos.SINTOMAS, eco=datos.ECO,
        fuentes_indicador=datos.FUENTES_INDICADOR, guia_indicador=datos.GUIA_INDICADOR, entorno=entorno_de(mision),
    )


@app.post("/dictado")
def dictado():
    texto = (request.get_json(silent=True) or {}).get("texto", "")
    return jsonify(interpretar(texto))


@app.route("/rutina")
def rutina():
    estado = datos.cargar()
    mision = estado["mision"]
    astro = elegir_astronauta(estado)
    return render_template("rutina.html", pagina="rutina", mision=mision, astro=astro,
                           tarjetas=tarjetas_tripulacion(estado, mision["dia"]),
                           r=rutina_diaria.resumen(astro, mision["dia"], mision["dia"]))


@app.post("/tarea")
def marcar_tarea():
    estado = datos.cargar()
    astro = elegir_astronauta(estado)
    dia = estado["mision"]["dia"]
    if rutina_diaria.marcar(astro, dia, dia, request.form.get("tarea"), request.form.get("hecho") == "1"):
        datos.guardar(estado)
    return redirect(url_for("rutina") + "#tareas")


@app.route("/indicadores")
def indicadores():
    estado = datos.cargar()
    mision = estado["mision"]
    astro = elegir_astronauta(estado)
    dia = mision["dia"]
    an = Analisis(astro)
    clave = request.args.get("indicador")
    if clave not in datos.INDICADORES:
        clave = "fc"
    dias, valores = an.serie(dia, clave)
    nombre, unidad, rango, _dec = datos.INDICADORES[clave]
    grafica = {"dias": dias, "valores": valores, "rango": rango, "base": astro["linea_base"].get(clave),
               "nombre": _(nombre), "unidad": _(unidad)}
    hoy = an.por_dia[dia]
    return render_template("indicadores.html", pagina="indicadores", mision=mision, astro=astro,
                           tarjetas=tarjetas_tripulacion(estado, dia), filas=an.indicadores(dia), elegido=clave,
                           grafica=grafica, guia=GUIA, guia_indicador=datos.GUIA_INDICADOR,
                           sintomas_hoy=[_(datos.SINTOMAS[s]) for s in hoy.get("sintomas", [])])


@app.route("/planes")
def planes():
    estado = datos.cargar()
    mision = estado["mision"]
    astro = elegir_astronauta(estado)
    return render_template("planes.html", pagina="planes", mision=mision, astro=astro,
                           tarjetas=tarjetas_tripulacion(estado, mision["dia"]), planes=datos.PLANES,
                           descripciones=datos.DESCRIPCION_PLAN, sugerido=request.args.get("tipo"))


@app.post("/plan")
def crear_plan():
    estado = datos.cargar()
    astro = elegir_astronauta(estado)
    tipo = request.form.get("tipo")
    dia = estado["mision"]["dia"]
    if tipo not in datos.PLANES:
        flash(_("Elige un plan de la lista."))
        return redirect(url_for("planes"))
    inicio = max(1, request.form.get("inicio", dia + 1, type=int))
    duracion = max(1, min(180, request.form.get("duracion", 30, type=int)))
    adherencia = max(10, min(100, request.form.get("adherencia", 90, type=int))) / 100
    astro["planes"].append({"tipo": tipo, "inicio": inicio, "duracion": duracion, "adherencia": adherencia})
    datos.guardar(estado)
    flash(_("Plan creado para {nombre}: {plan}.", nombre=astro["nombre"], plan=minuscula_inicial(_(datos.PLANES[tipo][0]))))
    return redirect(request.form.get("volver") or url_for("planes"))


@app.post("/plan/quitar")
def quitar_plan():
    estado = datos.cargar()
    astro = elegir_astronauta(estado)
    indice = request.form.get("indice", -1, type=int)
    if 0 <= indice < len(astro["planes"]):
        astro["planes"].pop(indice)
        datos.guardar(estado)
    return redirect(url_for("planes"))


@app.route("/nota")
def nota():
    estado = datos.cargar()
    mision = estado["mision"]
    astro = elegir_astronauta(estado)
    dia = max(1, min(mision["dia"], request.args.get("dia", mision["dia"], type=int)))
    r = analizar(astro, mision, dia)
    contenido = nota_clinica.generar(astro, dia, r["m"], r["sistemas"], r["general"], r["protocolos"], r["radiacion"], r["entorno"])
    return render_template("nota.html", pagina="nota", mision=mision, astro=astro, dia=dia,
                           tarjetas=tarjetas_tripulacion(estado, mision["dia"]), nota=contenido)


@app.route("/guia")
def guia():
    return render_template("guia.html", pagina="guia", guia=GUIA)


@app.route("/fuentes")
def fuentes():
    return render_template("fuentes.html", pagina="fuentes", grupos_fuentes=fuentes_usadas())


@app.route("/acerca")
def acerca():
    return render_template("acerca.html", pagina="acerca", sistemas={k: _(v) for k, v in datos.SISTEMAS.items()},
                           ridge=RIDGE, sistema_ridge=SISTEMA_RIDGE, zonas=ZONAS, cobertura=COBERTURA, riesgos=RIESGOS,
                           entornos=ENTORNOS, url_hrp=URL_HRP, url_vte=URL_VTE, limite=LIMITE_RADIACION,
                           reloj=reloj.resumen(), mision_dias=datos.DIAS_TOTALES)


@app.errorhandler(404)
def no_encontrada(_error):
    return render_template("base.html", pagina=None, mensaje_error=_("Esta página no existe.")), 404


@app.errorhandler(500)
def error_interno(error):
    app.logger.exception("Error al dibujar la página", exc_info=error)
    return render_template("base.html", pagina=None,
                           mensaje_error=_("Algo falló al preparar esta página."),
                           detalle_error=_("Suele pasar cuando el archivo datos/estado.json viene de una versión anterior de la app. Empieza una misión nueva y se arregla."),
                           ofrecer_reinicio=True), 500


if __name__ == "__main__":
    app.run(debug=True)
