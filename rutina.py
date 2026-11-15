import random

from datos import CADA_PESO, CADA_REACCION, EVENTO_SOLAR, efecto_planes
from idiomas import N_, _

PUNTOS_POR_NIVEL = 800

TAREAS_BASE = {
    "signos": (N_("Medir signos vitales al despertar"), N_("Pulso, presión, SpO₂ y temperatura."), "fc_reposo", 10),
    "resistencia": (N_("Ejercicio de resistencia: 60 min"), N_("Sentadillas, peso muerto y elevación de talones con carga."), "ejercicio", 20),
    "aerobico": (N_("Ejercicio aeróbico: 60 min"), N_("Caminadora o bicicleta."), "ejercicio", 10),
    "agua": (N_("Tomar al menos 2.5 L de agua"), N_("Meta de NASA para cada tripulante; previene cálculos renales."), "hidratacion", 10),
    "sueno": (N_("Dormir 7 horas o más"), N_("Se cuenta con las horas de sueño que registraste."), "sueno", 10),
    "bienestar": (N_("Registrar ánimo y estrés"), N_("Del 1 al 10, al final del día."), "bienestar", 5),
    "comidas": (N_("Llegar a tu meta de calorías"), N_("Comer poco acelera la pérdida de hueso y músculo."), "nutricion", 10),
    "dosimetro": (N_("Revisar tu dosímetro personal"), N_("Confirma que lo llevas contigo y anota la dosis."), "dosimetro", 5),
}
TAREAS_PROGRAMADAS = {
    "eco": (N_("Ultrasonido de la vena yugular"), N_("Lado izquierdo del cuello; registra el resultado."), "eco_yugular", 20),
    "amsler": (N_("Prueba de la vista con la rejilla de Amsler"), N_("Un ojo a la vez, a 30 cm."), "amsler", 10),
    "reaccion": (N_("Prueba de reacción de 3 minutos"), N_("En el registro diario; mide tu atención."), "reaccion", 15),
    "peso": (N_("Pesarte"), N_("En ayunas, a la misma hora cada semana."), "nutricion", 10),
    "pie": (N_("Prueba de pie"), N_("5 min acostado y 3 min de pie; anota presión y pulso."), "ortostatica", 15),
}
TAREAS_DE_PLAN = {
    "higiene_sueno": ("plan_sueno", N_("Luz cálida y sin tareas una hora antes de dormir"), N_("Parte de tu plan de higiene de sueño."), "sueno", 10),
    "apoyo_psicologico": ("plan_apoyo", N_("Contacto con tu equipo de apoyo o tu familia"), N_("Parte de tu plan de apoyo psicológico."), "bienestar", 10),
    "control_co2": ("plan_co2", N_("Revisar la ventilación de tu zona de descanso"), N_("Parte de tu plan para reducir el CO₂."), "co2", 5),
    "vigilancia_yugular": ("plan_cuello", N_("Revisar hinchazón de cuello, cara y párpados"), N_("Parte de tu plan de vigilancia de la vena yugular."), "eco_yugular", 5),
}
NUCLEO = ("signos", "resistencia", "aerobico", "sueno")

INSIGNIAS = {
    "huesos": (N_("Huesos de acero"), N_("14 días seguidos con 60 min de ejercicio de resistencia."), 14),
    "corazon": (N_("Corazón en forma"), N_("14 días seguidos con 60 min de ejercicio aeróbico."), 14),
    "agua": (N_("Bien hidratado"), N_("7 días seguidos tomando 2.5 L de agua o más."), 7),
    "sueno": (N_("Sueño reparador"), N_("7 noches seguidas durmiendo 7 horas o más."), 7),
    "racha": (N_("Rutina de hierro"), N_("30 días seguidos con la rutina básica completa."), 30),
    "vigia": (N_("Vigía"), N_("4 ultrasonidos de la vena yugular registrados."), 4),
    "bitacora": (N_("Bitácora al día"), N_("Hacer un registro diario tú mismo."), 1),
    "plan": (N_("Manos a la obra"), N_("Crear un plan de acción."), 1),
    "reflejos": (N_("Reflejos de piloto"), N_("5 pruebas de reacción sin lapsos."), 5),
}


def _tareas_dia(astro, dia, dia_actual, por_dia):
    r = por_dia.get(dia) or {}
    activos = set(efecto_planes(astro.get("planes", []), dia))
    guardadas = (astro.get("tareas") or {}).get(str(dia))
    rng = random.Random(f"tareas:{astro['id']}:{dia}")
    lista = []

    def manual(tid):
        if guardadas is not None:
            return tid in guardadas
        return dia < dia_actual and rng.random() < 0.85

    def agregar(tid, titulo, detalle, guia, puntos, hecho, es_manual):
        lista.append({"id": tid, "titulo": titulo, "detalle": detalle, "guia": guia,
                      "puntos": puntos, "hecho": bool(hecho), "manual": es_manual})

    automaticas = {
        "signos": r.get("fc") is not None,
        "resistencia": (r.get("resistencia") or 0) >= 60,
        "aerobico": (r.get("aerobico") or 0) >= 60,
        "agua": (r.get("agua") or 0) >= 2.5,
        "sueno": (r.get("sueno") or 0) >= 7,
        "bienestar": r.get("animo") is not None,
        "comidas": (r.get("calorias") or 0) >= 0.9 * astro["linea_base"]["calorias"],
    }
    for tid, datos_tarea in TAREAS_BASE.items():
        if tid in automaticas:
            agregar(tid, *datos_tarea, automaticas[tid], False)
        else:
            agregar(tid, *datos_tarea, manual(tid), True)

    cada_eco = 7 if "vigilancia_yugular" in activos else 15
    if dia % cada_eco == 0:
        agregar("eco", *TAREAS_PROGRAMADAS["eco"], r.get("eco") is not None, False)
    if dia % 7 == 0:
        agregar("amsler", *TAREAS_PROGRAMADAS["amsler"], manual("amsler"), True)
    if dia % CADA_REACCION == 0:
        agregar("reaccion", *TAREAS_PROGRAMADAS["reaccion"], r.get("reaccion") is not None, False)
    if dia % CADA_PESO == 0:
        agregar("peso", *TAREAS_PROGRAMADAS["peso"], r.get("peso") is not None, False)
    if (r.get("gravedad") or 0) > 0 and (dia % 7 == 2 or r.get("pa_sis_pie") is not None):
        agregar("pie", *TAREAS_PROGRAMADAS["pie"], r.get("pa_sis_pie") is not None, False)
    for tipo, (tid, *datos_tarea) in TAREAS_DE_PLAN.items():
        if tipo in activos:
            agregar(tid, *datos_tarea, manual(tid), True)
    if "refugio" in activos and (EVENTO_SOLAR[0] <= dia <= EVENTO_SOLAR[1] or r.get("sep_real")):
        agregar("plan_refugio", N_("Dormir en el refugio blindado"), N_("Hay un evento solar en curso."), "dosimetro", 10,
                manual("plan_refugio"), True)
    return lista


def _racha_max(valores):
    mejor = actual = 0
    for v in valores:
        actual = actual + 1 if v else 0
        mejor = max(mejor, actual)
    return mejor


def _racha_final(valores):
    n = 0
    for v in reversed(valores):
        if not v:
            break
        n += 1
    return n


def resumen(astro, dia, dia_actual):
    por_dia = {r["dia"]: r for r in astro["registros"]}
    dias = [d for d in range(1, dia + 1) if d in por_dia]
    puntos = 0
    nucleo, res, aer, sueno, agua = [], [], [], [], []
    for d in dias:
        tareas = _tareas_dia(astro, d, dia_actual, por_dia)
        hechas = {t["id"] for t in tareas if t["hecho"]}
        puntos += sum(t["puntos"] for t in tareas if t["hecho"])
        nucleo.append(all(t in hechas for t in NUCLEO))
        res.append("resistencia" in hechas)
        aer.append("aerobico" in hechas)
        sueno.append("sueno" in hechas)
        agua.append("agua" in hechas)

    hoy = _tareas_dia(astro, dia, dia_actual, por_dia)
    progreso = {
        "huesos": _racha_max(res), "corazon": _racha_max(aer), "sueno": _racha_max(sueno), "agua": _racha_max(agua),
        "racha": _racha_max(nucleo), "vigia": sum(1 for d in dias if por_dia[d].get("eco")),
        "bitacora": int(any(por_dia[d].get("fuente") == "registro" for d in dias)),
        "plan": len(astro.get("planes", [])),
        "reflejos": sum(1 for d in dias if por_dia[d].get("reaccion") is not None and not por_dia[d].get("lapsos")),
    }
    insignias = [{"id": k, "nombre": _(n), "descripcion": _(desc), "meta": meta,
                  "progreso": min(meta, progreso[k]), "ganada": progreso[k] >= meta}
                 for k, (n, desc, meta) in INSIGNIAS.items()]

    cada_eco = 7 if "vigilancia_yugular" in efecto_planes(astro.get("planes", []), dia) else 15
    faltan = lambda cada: (cada - dia % cada) % cada or cada
    proximos = sorted([
        {"titulo": _("Ultrasonido de la vena yugular"), "en_dias": faltan(cada_eco), "guia": "eco_yugular"},
        {"titulo": _("Prueba de la vista con la rejilla de Amsler"), "en_dias": faltan(7), "guia": "amsler"},
        {"titulo": _("Prueba de reacción de 3 minutos"), "en_dias": faltan(CADA_REACCION), "guia": "reaccion"},
        {"titulo": _("Pesarte"), "en_dias": faltan(CADA_PESO), "guia": "nutricion"},
    ], key=lambda x: x["en_dias"])

    for t in hoy:
        t["titulo"], t["detalle"] = _(t["titulo"]), _(t["detalle"])
    return {
        "dia": dia, "editable": dia == dia_actual, "tareas": hoy,
        "puntos_hoy": sum(t["puntos"] for t in hoy if t["hecho"]),
        "puntos_posibles_hoy": sum(t["puntos"] for t in hoy),
        "puntos": puntos, "nivel": 1 + puntos // PUNTOS_POR_NIVEL,
        "en_nivel": puntos % PUNTOS_POR_NIVEL, "por_nivel": PUNTOS_POR_NIVEL,
        "racha": _racha_final(nucleo), "insignias": insignias, "proximos": proximos,
    }


def marcar(astro, dia, dia_actual, tarea_id, hecho):
    por_dia = {r["dia"]: r for r in astro["registros"]}
    manuales = {t["id"]: t for t in _tareas_dia(astro, dia, dia_actual, por_dia) if t["manual"]}
    if tarea_id not in manuales:
        return False
    hechas = {t["id"] for t in manuales.values() if t["hecho"]}
    if hecho:
        hechas.add(tarea_id)
    else:
        hechas.discard(tarea_id)
    astro.setdefault("tareas", {})[str(dia)] = sorted(hechas)
    return True
