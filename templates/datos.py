import json
from copy import deepcopy

import reloj
import random
from pathlib import Path

from entornos import ENTORNO_INICIAL, ENTORNOS, fase_del_dia

INDICADORES = {
    "fc": ("Pulso en reposo", "lpm", (50, 100), 0),
    "pa_sis": ("Presión sistólica", "mmHg", (90, 129), 0),
    "pa_dia": ("Presión diastólica", "mmHg", (60, 79), 0),
    "spo2": ("Oxígeno (SpO₂)", "%", (95, 100), 0),
    "temp": ("Temperatura", "°C", (36.0, 37.9), 1),
    "sueno": ("Sueño", "h", (7, 9), 1),
    "animo": ("Ánimo", "/10", (6, 10), 0),
    "estres": ("Estrés", "/10", (1, 5), 0),
    "resistencia": ("Ejercicio de resistencia", "min", (60, 180), 0),
    "aerobico": ("Ejercicio aeróbico", "min", (60, 150), 0),
    "agua": ("Agua", "L", (2.5, 4.5), 1),
    "calorias": ("Calorías", "kcal", (2500, 3500), 0),
    "contacto": ("Días sin contacto personal", "días", (0, 14), 0),
    "cohesion": ("Relación con la tripulación", "/10", (6, 10), 0),
    "actividad": ("Actividad despierto", "h", (8, 16), 1),
    "co2": ("CO₂ en cabina", "mmHg", (0, 3.0), 1),
    "ruido": ("Ruido al dormir", "dBA", (0, 50), 0),
}

DEL_VEHICULO = {"co2", "ruido"}

PRUEBAS = {
    "reaccion": ("Tiempo de reacción promedio", "ms"),
    "lapsos": ("Lapsos (reacciones de 355 ms o más)", ""),
    "pa_sis_pie": ("Presión sistólica de pie", "mmHg"),
    "pa_dia_pie": ("Presión diastólica de pie", "mmHg"),
    "fc_pie": ("Pulso de pie", "lpm"),
}

LIMITES = {
    "fc": (30, 200), "pa_sis": (70, 220), "pa_dia": (40, 140), "spo2": (70, 100), "temp": (34, 42),
    "sueno": (0, 16), "animo": (1, 10), "estres": (1, 10), "resistencia": (0, 300), "aerobico": (0, 300),
    "agua": (0, 8), "calorias": (0, 8000), "peso": (30, 200), "reaccion": (100, 3000), "lapsos": (0, 100),
    "contacto": (0, 180), "cohesion": (1, 10), "actividad": (0, 20), "co2": (0, 15), "ruido": (0, 110),
    "pa_sis_pie": (60, 220), "pa_dia_pie": (30, 140), "fc_pie": (30, 200),
}

FUENTES_INDICADOR = {
    "fc": ["fc_normal"], "pa_sis": ["aha_presion"], "pa_dia": ["aha_presion"], "spo2": ["spo2_medline"],
    "temp": ["charite_temp", "fiebre"], "sueno": ["jones_sueno", "sueno_barger"],
    "animo": ["nasa_conducta_tb016"], "estres": ["nasa_conducta_tb016"],
    "resistencia": ["csa_ejercicio"], "aerobico": ["csa_ejercicio"],
    "agua": ["nasa_agua", "nasa_renal"], "calorias": ["sciencefriday_kcal", "sciencenews_dieta"],
    "contacto": ["nasa_bhp", "nasa_aislamiento"], "cohesion": ["nasa_bhp"], "actividad": ["mars500"],
    "co2": ["nasa_co2"], "ruido": ["nasa_ruido"],
}

GUIA_INDICADOR = {
    "fc": "fc_reposo", "pa_sis": "presion", "pa_dia": "presion", "spo2": "spo2", "temp": "temp",
    "sueno": "sueno", "animo": "bienestar", "estres": "bienestar", "resistencia": "ejercicio",
    "aerobico": "ejercicio", "agua": "hidratacion", "calorias": "nutricion",
    "contacto": "aislamiento", "cohesion": "aislamiento", "actividad": "actividad",
    "co2": "co2", "ruido": "ruido",
}

ECO = {"normal": "Flujo normal", "estasis": "Flujo lento", "retrogrado": "Flujo retrógrado", "trombo": "Trombo detectado"}

SISTEMAS = {
    "cardiovascular": "Corazón y circulación",
    "trombosis": "Venas del cuello (trombosis)",
    "respiratorio": "Respiración",
    "oseo": "Huesos",
    "muscular": "Músculos",
    "urinario": "Riñones y vías urinarias",
    "mental": "Salud mental y sueño",
    "ojos": "Ojos (SANS)",
    "inmune": "Sistema inmune y radiación",
    "nutricion": "Nutrición y peso",
}

SINTOMAS = {
    "cefalea": "Dolor de cabeza",
    "vision_borrosa": "Visión borrosa",
    "congestion": "Congestión nasal",
    "dolor_espalda": "Dolor de espalda",
    "nauseas": "Náuseas",
    "mareo": "Mareo o desorientación",
    "fatiga": "Fatiga",
    "palpitaciones": "Palpitaciones",
    "erupcion": "Erupción en la piel",
    "hinchazon_cuello": "Hinchazón visible en el cuello",
    "edema_facial": "Cara más hinchada de lo habitual",
    "edema_parpados": "Párpados hinchados",
    "dolor_orinar": "Ardor al orinar",
    "dificultad_orinar": "Dificultad para orinar",
    "dolor_costado": "Dolor fuerte en el costado",
}
SINTOMAS_TROMBOSIS = ["hinchazon_cuello", "edema_facial", "edema_parpados"]
SINTOMAS_URINARIOS = ["dolor_orinar", "dificultad_orinar", "dolor_costado"]

PLANES = {
    "ejercicio_resistencia": ("Aumentar ejercicio de resistencia", {"oseo": 0.6, "muscular": 0.7}),
    "ejercicio_aerobico": ("Aumentar ejercicio aeróbico", {"cardiovascular": 0.6, "mental": 0.15}),
    "higiene_sueno": ("Plan de higiene de sueño", {"mental": 0.5, "inmune": 0.3}),
    "apoyo_psicologico": ("Apoyo psicológico y contacto familiar", {"mental": 0.6}),
    "hidratacion": ("Plan de hidratación", {"urinario": 0.5}),
    "alimentacion": ("Plan de alimentación", {"nutricion": 0.6, "muscular": 0.1}),
    "vigilancia_yugular": ("Vigilancia de la vena yugular", {"trombosis": 0.35}),
    "control_co2": ("Reducir CO₂ en la zona de descanso", {"ojos": 0.4, "respiratorio": 0.5}),
    "refugio": ("Refugio durante eventos solares", {"inmune": 0.35}),
}

DESCRIPCION_PLAN = {
    "ejercicio_resistencia": "60 minutos diarios en el equipo de resistencia: frena la pérdida de hueso y músculo.",
    "ejercicio_aerobico": "60 minutos diarios en caminadora o bicicleta: mantiene la condición del corazón.",
    "higiene_sueno": "Horario fijo y luz cálida antes de dormir: recupera horas de sueño.",
    "apoyo_psicologico": "Sesiones con el equipo de apoyo y contacto con la familia: mejora el ánimo y baja el estrés.",
    "hidratacion": "Llegar a 2.7 L de agua al día: diluye la orina y previene cálculos.",
    "alimentacion": "Comidas a horario fijo y colaciones: acerca las calorías a tu meta y frena la pérdida de peso.",
    "vigilancia_yugular": "Ultrasonido del cuello cada semana y registro diario de hinchazón.",
    "control_co2": "Más ventilación en la zona de descanso: baja el CO₂ que respiras al dormir.",
    "refugio": "Ir al refugio blindado durante los eventos solares: reduce la dosis del evento.",
}

TRIPULACION_BASE = [
    {
        "id": "jimena", "nombre": "Jimena Rangel", "rol": "Comandante",
        "linea_base": {"fc": 58, "pa_sis": 116, "pa_dia": 74, "spo2": 98, "temp": 36.6, "sueno": 7.3,
                       "animo": 8, "estres": 3, "peso": 62.0, "calorias": 2500, "reaccion": 255,
                       "cohesion": 9, "actividad": 14.2},
        "historia": {"yugular": 85, "edema": [95, 120, 0.3]},
    },
    {
        "id": "cesar", "nombre": "César Tovar", "rol": "Ingeniero de vuelo",
        "linea_base": {"fc": 62, "pa_sis": 120, "pa_dia": 78, "spo2": 98, "temp": 36.6, "sueno": 7.2,
                       "animo": 8, "estres": 3, "peso": 78.0, "calorias": 3000, "reaccion": 270,
                       "cohesion": 8, "actividad": 13.5},
        "historia": {"sueno": [60, 120, 5.5], "estres": [60, 120, 7.0], "animo": [70, 120, 5.0],
                     "apetito": [70, 120, 0.72], "fiebre": [110, 112],
                     "aislamiento": [75, 130, 1.0], "hipocinesia": [75, 140, 1.0]},
    },
    {
        "id": "cynthia", "nombre": "Cynthia Calzadilla", "rol": "Especialista médica",
        "linea_base": {"fc": 60, "pa_sis": 114, "pa_dia": 72, "spo2": 98, "temp": 36.5, "sueno": 7.4,
                       "animo": 8, "estres": 3, "peso": 60.0, "calorias": 2500, "reaccion": 262,
                       "cohesion": 8, "actividad": 13.8},
        "historia": {"resistencia": [40, 55, 0.25], "agua": [50, 110, 1.8], "sans": [80, 120, 0.4],
                     "renal": [105, 120, 0.10]},
    },
    {
        "id": "jesus", "nombre": "Jesús Barrientos", "rol": "Especialista de misión",
        "linea_base": {"fc": 61, "pa_sis": 118, "pa_dia": 76, "spo2": 98, "temp": 36.6, "sueno": 7.5,
                       "animo": 8, "estres": 3, "peso": 74.0, "calorias": 2800, "reaccion": 258,
                       "cohesion": 8, "actividad": 13.6},
        "historia": {"aerobico": [50, 110, 0.2], "palpitaciones": [90, 120, 0.35]},
        "reloj": True,
    },
]

NOMBRE_APP = "Astra Health"

DIAS_TOTALES = 180
DIA_INICIAL = 120
EVENTO_SOLAR = (96, 98)
FALLA_CO2 = (70, 78)
DOSIS_DIA = 1.8
CADA_REACCION = 4
CADA_PESO = 7


def _progreso(dia, inicio, fin):
    if dia <= inicio:
        return 0.0
    if dia >= fin:
        return 1.0
    return (dia - inicio) / (fin - inicio)


def _tendencia(dia, base, regla):
    if not regla:
        return base
    inicio, fin, final = regla
    return base + (final - base) * _progreso(dia, inicio, fin)


def efecto_planes(planes, dia):
    efectos = {}
    for p in planes:
        if p["inicio"] <= dia < p["inicio"] + p["duracion"]:
            efectos[p["tipo"]] = max(efectos.get(p["tipo"], 0), p["adherencia"])
    return efectos


def _apetito(astro, dia, efectos):
    frac = _tendencia(dia, 0.95, astro["historia"].get("apetito"))
    return frac + (1 - frac) * efectos.get("alimentacion", 0)


def _dias_en_gravedad(astro, dia, gravedad):
    if gravedad <= 0:
        return 0
    previos = {r["dia"]: r for r in astro.get("registros", [])}
    n, d = 1, dia - 1
    while d in previos and (previos[d].get("gravedad") or 0) > 0:
        n, d = n + 1, d - 1
    return n


def generar_dia(astro, dia, planes=None, entorno=ENTORNO_INICIAL, sep_real=0.0):
    planes = astro.get("planes", []) if planes is None else planes
    b, h = astro["linea_base"], astro["historia"]
    amb = ENTORNOS[entorno]
    ef = efecto_planes(planes, dia)
    rng = random.Random(f"{astro['id']}:{dia}")
    tormenta = EVENTO_SOLAR[0] <= dia <= EVENTO_SOLAR[1] or sep_real > 0
    nave = random.Random(f"nave:{dia}")
    falla_co2 = FALLA_CO2[0] <= dia <= FALLA_CO2[1]
    co2 = (4.6 if falla_co2 else 2.4) + nave.gauss(0, 0.2)
    ruido = (56 if falla_co2 else 45) + nave.gauss(0, 2)

    frac_res = _tendencia(dia, 1.0, h.get("resistencia")) * amb["factor_resistencia"]
    frac_res += (1 - frac_res) * ef.get("ejercicio_resistencia", 0)
    frac_aer = _tendencia(dia, 1.0, h.get("aerobico"))
    frac_aer += (1 - frac_aer) * ef.get("ejercicio_aerobico", 0)
    resistencia = max(0, 66 * frac_res + rng.gauss(0, 6))
    aerobico = max(0, 66 * frac_aer + rng.gauss(0, 5))
    if tormenta:
        resistencia, aerobico = resistencia * 0.2, aerobico * 0.2

    sueno = _tendencia(dia, b["sueno"], h.get("sueno"))
    sueno += (b["sueno"] - sueno) * 0.8 * ef.get("higiene_sueno", 0) + rng.gauss(0, 0.35) - (0.6 if tormenta else 0)
    estres = _tendencia(dia, b["estres"], h.get("estres"))
    estres -= (estres - b["estres"]) * 0.7 * ef.get("apoyo_psicologico", 0)
    estres += rng.gauss(0, 0.6) + (2 if tormenta else 0)
    animo = _tendencia(dia, b["animo"], h.get("animo"))
    animo += (b["animo"] - animo) * 0.7 * ef.get("apoyo_psicologico", 0) + rng.gauss(0, 0.5)

    agua = _tendencia(dia, 2.7, h.get("agua"))
    agua = max(0.8, agua + (2.7 - agua) * ef.get("hidratacion", 0) + rng.gauss(0, 0.2))
    calorias = b["calorias"] * _apetito(astro, dia, ef) + rng.gauss(0, 110)

    fiebre = 1.0 if h.get("fiebre") and h["fiebre"][0] <= dia <= h["fiebre"][1] else 0.0
    descondicion = 12 * (1 - frac_aer) * _progreso(dia, 0, 120)
    fc = b["fc"] + 0.8 * (estres - b["estres"]) + 1.2 * max(0, b["sueno"] - sueno) + descondicion + 9 * fiebre + rng.gauss(0, 1.8)
    medido = reloj.del_dia(dia, DIAS_TOTALES) if astro.get("reloj") else None
    if medido:
        fc = medido["reposo"]
    pa_sis = b["pa_sis"] + 1.6 * (estres - b["estres"]) + rng.gauss(0, 3.5)
    pa_dia = b["pa_dia"] + 0.9 * (estres - b["estres"]) + rng.gauss(0, 2.5)
    spo2 = b["spo2"] - (1.2 if co2 > 4 else 0) - 1.2 * fiebre + rng.gauss(0, 0.5)
    temp = b["temp"] + 0.8 * _progreso(dia, 0, 75) + rng.gauss(0, 0.12) + 1.5 * fiebre

    peso = None
    if dia % 7 == 0:
        deficit = sum(b["calorias"] * (1 - _apetito(astro, d, efecto_planes(planes, d))) for d in range(1, dia + 1))
        peso = round(b["peso"] - deficit / 7700 + rng.gauss(0, 0.2), 1)

    reaccion = lapsos = None
    if dia % CADA_REACCION == 0:
        reaccion = (b["reaccion"] + 14 * max(0, 7 - sueno) + 4 * max(0, estres - b["estres"])
                    + 30 * fiebre + (10 if co2 > 4 else 0) + rng.gauss(0, 8))
        lapsos = max(0, round((reaccion - b["reaccion"]) / 10 + abs(rng.gauss(0, 0.7))))

    orto = None
    dias_g = _dias_en_gravedad(astro, dia, amb["gravedad"])
    if dias_g and (dias_g <= 3 or dia % 7 == 2):
        decond = 1 - min(1.0, frac_aer)
        recien = (1.0 if dias_g <= 3 else 0.4) * min(1.0, dia / 90)
        seco = max(0.0, 2.5 - agua)
        orto = {"sis": 4 + 14 * decond + 10 * recien + 6 * seco + rng.gauss(0, 3),
                "dia": -2 + 8 * decond + 6 * recien + 3 * seco + rng.gauss(0, 2),
                "fc": 10 + 14 * decond + 12 * recien + 5 * seco + rng.gauss(0, 3)}
    mareo_de_pie = bool(orto and (orto["sis"] >= 20 or orto["fc"] >= 30))

    aisl = _tendencia(dia, 0, h.get("aislamiento"))
    contacto = max(0, round(2 + 16 * aisl + rng.gauss(0, 1.2)))
    cohesion = b.get("cohesion", 8) - 3.2 * aisl - 0.35 * max(0, estres - b["estres"]) + rng.gauss(0, 0.5)
    cohesion = int(max(1, min(10, round(cohesion))))
    hipo = _tendencia(dia, 0, h.get("hipocinesia"))
    actividad = b.get("actividad", 13.8) * (1 - 0.14 * hipo)
    actividad -= (sueno - b["sueno"]) * 0.5
    actividad = round(max(4, min(18, actividad + rng.gauss(0, 0.3))), 1)

    eco = None
    if dia % (7 if ef.get("vigilancia_yugular") else 15) == 0:
        eco = "retrogrado" if h.get("yugular") and dia >= h["yugular"] else "normal"

    edema = _tendencia(dia, 0, h.get("edema"))
    sans = _tendencia(dia, 0, h.get("sans"))
    renal = _tendencia(dia, 0, h.get("renal")) * (1 - 0.7 * ef.get("hidratacion", 0))
    probabilidades = {
        "cefalea": 0.07 + (0.5 if co2 > 4 else 0) + 0.3 * sans + 0.2 * edema,
        "vision_borrosa": sans,
        "congestion": 0.12,
        "dolor_espalda": 0.06 + 0.2 * (1 - min(1, frac_res)),
        "nauseas": 0.02,
        "mareo": 0.5 if mareo_de_pie else 0.02,
        "fatiga": 0.05 + 0.25 * max(0, 6.5 - sueno) + 0.6 * fiebre,
        "palpitaciones": 0.01 + _tendencia(dia, 0, h.get("palpitaciones")) * (1 - ef.get("ejercicio_aerobico", 0)),
        "erupcion": 0.02 + 0.06 * max(0, estres - b["estres"] - 2),
        "hinchazon_cuello": 0.4 * edema,
        "edema_facial": 0.02 + edema,
        "edema_parpados": 0.01 + 0.7 * edema,
        "dolor_orinar": 0.01 + (0.08 if agua < 2.0 else 0),
        "dificultad_orinar": 0.004,
        "dolor_costado": renal,
    }
    sintomas = [s for s, p in probabilidades.items() if rng.random() < p]

    return {
        "dia": dia, "fuente": "simulado",
        "reales": ["fc"] if medido else [],
        "medicion": {"fecha": medido["fecha"], "lecturas": medido["lecturas"],
                     "media": medido["media"], "maximo": medido["maximo"]} if medido else None,
        "fc": round(fc), "pa_sis": round(pa_sis), "pa_dia": round(pa_dia),
        "spo2": int(max(88, min(100, round(spo2)))), "temp": round(temp, 1),
        "sueno": round(max(3, min(10, sueno)), 1),
        "animo": int(max(1, min(10, round(animo)))), "estres": int(max(1, min(10, round(estres)))),
        "resistencia": round(resistencia), "aerobico": round(aerobico),
        "agua": round(agua, 1), "calorias": round(max(800, calorias)), "peso": peso,
        "co2": round(co2, 1), "ruido": round(ruido),
        "contacto": contacto, "cohesion": cohesion, "actividad": actividad,
        "dosis": round(fase_del_dia(dia, entorno)["tasa"] + (30 if EVENTO_SOLAR[0] <= dia <= EVENTO_SOLAR[1] else 0) * (0.5 - 0.35 * ef.get("refugio", 0))
                       + sep_real * (0.5 - 0.35 * ef.get("refugio", 0)), 2),
        "sep_real": sep_real > 0,
        "reaccion": round(reaccion) if reaccion is not None else None, "lapsos": lapsos,
        "pa_sis_pie": round(pa_sis - orto["sis"]) if orto else None,
        "pa_dia_pie": round(pa_dia - orto["dia"]) if orto else None,
        "fc_pie": round(fc + orto["fc"]) if orto else None,
        "entorno": entorno, "gravedad": amb["gravedad"],
        "eco": eco, "sintomas": sintomas,
    }


def estado_inicial(dia_inicial=None):
    dia_inicial = max(1, min(DIAS_TOTALES, dia_inicial or DIA_INICIAL))
    tripulacion = []
    for base in TRIPULACION_BASE:
        astro = {**deepcopy(base), "planes": [], "tareas": {}, "registros": []}
        if astro.get("reloj") and reloj.linea_base():
            astro["linea_base"]["fc"] = reloj.linea_base()
        for d in range(1, dia_inicial + 1):
            astro["registros"].append(generar_dia(astro, d, []))
        tripulacion.append(astro)
    mision = {"dia": dia_inicial, "dias_totales": DIAS_TOTALES, "entorno": ENTORNO_INICIAL,
              "clima_real": {"activo": False, "ensayo": False, "aplicados": {}}}
    return {"mision": mision, "tripulacion": tripulacion}


ARCHIVO = Path(__file__).parent / "datos" / "estado.json"


def reparar(estado):
    cambio = False
    mision = estado["mision"]
    for clave, valor in (("dias_totales", DIAS_TOTALES), ("entorno", ENTORNO_INICIAL),
                         ("clima_real", {"activo": False, "ensayo": False, "aplicados": {}})):
        if clave not in mision:
            mision[clave] = valor
            cambio = True

    dia = max(1, min(mision["dias_totales"], int(mision.get("dia") or DIA_INICIAL)))
    if dia != mision.get("dia"):
        mision["dia"], cambio = dia, True

    for astro in estado["tripulacion"]:
        if "tareas" not in astro:
            astro["tareas"], cambio = {}, True
        astro.setdefault("planes", [])
        if "reaccion" not in astro["linea_base"]:
            astro["linea_base"]["reaccion"], cambio = 260, True

        registros = {r["dia"]: r for r in astro.get("registros", [])}
        faltantes = [d for d in range(1, dia + 1) if d not in registros]
        if faltantes:
            for d in faltantes:
                registros[d] = generar_dia(astro, d, astro["planes"], mision["entorno"])
            cambio = True
        sobrantes = [d for d in registros if d > dia]
        if sobrantes:
            for d in sobrantes:
                del registros[d]
            cambio = True
        if faltantes or sobrantes:
            astro["registros"] = [registros[d] for d in sorted(registros)]
    return estado, cambio


def cargar():
    if ARCHIVO.exists():
        try:
            estado = json.loads(ARCHIVO.read_text(encoding="utf-8"))
            estado, cambio = reparar(estado)
        except (ValueError, KeyError, TypeError) as error:
            print(f"[datos] No se pudo leer datos/estado.json ({error}). Se crea una misión nueva.")
        else:
            if cambio:
                guardar(estado)
            return estado
    estado = estado_inicial()
    guardar(estado)
    return estado


def guardar(estado):
    ARCHIVO.parent.mkdir(exist_ok=True)
    ARCHIVO.write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")


def reiniciar(dia_inicial=None):
    estado = estado_inicial(dia_inicial)
    guardar(estado)
    return estado
