from datos import ECO, INDICADORES, PLANES, SINTOMAS, SINTOMAS_TROMBOSIS, SINTOMAS_URINARIOS, SISTEMAS, efecto_planes
from entornos import ENTORNOS, factor_gravedad
from idiomas import _, minuscula_inicial, numero
from riesgos_nasa import riesgo

LIMITE_RADIACION = 600
LIMITE_EVENTO_SEP = 250
VIGENCIA_PRUEBA = 8
VIGENCIA_PESO = 10
VIGENCIA_ECO = 20
PESO_ECO = {"normal": 0.0, "estasis": 0.45, "retrogrado": 0.6, "trombo": 1.0}

NIVELES = [
    (80, "critico", "Crítico", "#EB4D5C"),
    (60, "atencion", "Atención", "#F28C3B"),
    (35, "vigilar", "Vigilar", "#F0C24B"),
    (0, "normal", "Normal", "#4FC48D"),
]
PUNTAJE_DE_NIVEL = {"critico": 80, "atencion": 60, "vigilar": 35}

ESCALAMIENTO = {
    "tu": "Tú puedes atenderlo: sigue los pasos.",
    "tripulacion": "Avisa a tu tripulación y al oficial médico de a bordo.",
    "tierra": "Avisa a los médicos de vuelo en Tierra.",
}
AVISO_POR_NIVEL = {"vigilar": "tu", "atencion": "tripulacion", "critico": "tierra"}
AVISO_FIJO = {"flujo_yugular": "tierra", "sintomas_svt": "tierra", "trombo": "tierra", "dosis": "tu",
              "calculo_renal": "tierra", "retencion_urinaria": "tierra"}

RIESGO_PROTOCOLO = {
    "hipoxemia": "hipoxia", "fc_elevada": "cardiovascular", "pa_elevada": "cardiovascular", "aerobico": "condicion",
    "palpitaciones": "arritmia", "fiebre": "inmune", "erupcion": "inmune", "deuda_sueno": "sueno",
    "bienestar": "conducta", "perdida_osea": "hueso", "resistencia": "condicion", "sans": "sans",
    "co2": "hipoxia", "sep": "cancer", "dosis": "cancer", "trombo": "vte", "flujo_yugular": "vte",
    "sintomas_svt": "vte", "mareo": "vestibular", "hidratacion": "urinario", "calculo_renal": "urinario",
    "infeccion_urinaria": "urinario", "retencion_urinaria": "urinario", "reaccion": "sueno",
    "ortostatica": "cardiovascular", "nutricion": "nutricion", "sep_real": "cancer", "flr_aviso": "cancer",
    "ruido": "sueno", "contacto": "conducta", "cohesion": "conducta", "actividad": "conducta",
}
GUIA_PROTOCOLO = {
    "hipoxemia": "spo2", "fc_elevada": "fc_reposo", "pa_elevada": "presion", "aerobico": "ejercicio",
    "palpitaciones": "ecg", "fiebre": "temp", "trombo": "eco_yugular", "flujo_yugular": "eco_yugular",
    "sintomas_svt": "eco_yugular", "deuda_sueno": "sueno", "bienestar": "bienestar", "perdida_osea": "ejercicio",
    "resistencia": "ejercicio", "sans": "amsler", "co2": "co2", "sep": "dosimetro", "dosis": "dosimetro",
    "hidratacion": "hidratacion", "calculo_renal": "urinario", "infeccion_urinaria": "urinario",
    "retencion_urinaria": "urinario", "reaccion": "reaccion", "ortostatica": "ortostatica", "nutricion": "nutricion",
    "sep_real": "dosimetro", "flr_aviso": "dosimetro", "erupcion": "temp",
    "ruido": "ruido", "contacto": "aislamiento", "cohesion": "aislamiento", "actividad": "actividad",
}


def nivel_de(puntaje):
    for minimo, clave, nombre, color in NIVELES:
        if puntaje >= minimo:
            return {"clave": clave, "nombre": _(nombre), "color": color}


def rampa(x, a, b):
    if x is None or x <= a:
        return 0.0
    if x >= b:
        return 1.0
    return (x - a) / (b - a)


def _promedio(valores):
    valores = [v for v in valores if v is not None]
    return sum(valores) / len(valores) if valores else None


class Analisis:

    def __init__(self, astro):
        self.astro = astro
        self.base = astro["linea_base"]
        self.por_dia = {r["dia"]: r for r in astro["registros"]}
        self.ultimo = max(self.por_dia) if self.por_dia else 0
        self._acumulados()

    def _acumulados(self):
        self.osea, self.muscular, self.dosis, self.micro = {}, {}, {}, {}
        osea = muscular = dosis = micro = 0.0
        for d in range(1, self.ultimo + 1):
            r = self.por_dia.get(d, {})
            res, aer = r.get("resistencia") or 0, r.get("aerobico") or 0
            fg = factor_gravedad(r.get("gravedad", 0.0))
            osea += fg * (1.5 / 30) * (1 - 0.65 * min(1, res / 60))
            muscular += fg * 0.10 * (1 - 0.9 * min(1, (res + aer) / 120))
            dosis += r.get("dosis") or 0
            micro += fg
            self.osea[d], self.muscular[d], self.dosis[d], self.micro[d] = osea, muscular, dosis, micro

    def ventana(self, dia, n):
        return [self.por_dia[d] for d in range(max(1, dia - n + 1), dia + 1) if d in self.por_dia]

    def prom(self, dia, clave, n=7):
        return _promedio([r.get(clave) for r in self.ventana(dia, n)])

    def frecuencia(self, dia, sintoma, n=7):
        regs = self.ventana(dia, n)
        return sum(1 for r in regs if sintoma in r.get("sintomas", [])) / len(regs) if regs else 0

    def ultimo_valor(self, dia, clave, n=15):
        for d in range(dia, max(0, dia - n), -1):
            if (self.por_dia.get(d) or {}).get(clave) is not None:
                return self.por_dia[d][clave], d
        return None, None

    def seguidos(self, dia, prueba):
        n, d = 0, dia
        while d in self.por_dia and prueba(self.por_dia[d]):
            n, d = n + 1, d - 1
        return n

    def temp_normal_en_vuelo(self, dia):
        vals = sorted(r["temp"] for r in self.ventana(dia - 4, 18))
        return vals[len(vals) // 2] if vals else self.base["temp"]

    def metricas(self, dia):
        b, hoy = self.base, self.por_dia.get(dia, {})
        f = lambda s, n=7: self.frecuencia(dia, s, n)
        temp_base = self.temp_normal_en_vuelo(dia)
        temps3 = [r["temp"] for r in self.ventana(dia, 3)]
        tmax3 = max(temps3) if temps3 else temp_base
        reaccion, dia_r = self.ultimo_valor(dia, "reaccion", VIGENCIA_PRUEBA)
        pie, dia_o = self.ultimo_valor(dia, "pa_sis_pie", VIGENCIA_PRUEBA)
        orto = None
        if pie is not None:
            r = self.por_dia[dia_o]
            orto = {"caida_sis": r["pa_sis"] - r["pa_sis_pie"], "caida_dia": r["pa_dia"] - (r.get("pa_dia_pie") or r["pa_dia"]),
                    "sube_fc": (r.get("fc_pie") or r["fc"]) - r["fc"]}
            orto["indice"] = max(orto["caida_sis"] / 20, orto["caida_dia"] / 10, orto["sube_fc"] / 30)
        peso, dia_peso = self.ultimo_valor(dia, "peso", VIGENCIA_PESO)
        eco, dia_eco = self.ultimo_valor(dia, "eco", VIGENCIA_ECO)
        kcal7 = self.prom(dia, "calorias")
        return {
            "temp_base": temp_base, "tmax3": tmax3, "delta_t3": tmax3 - temp_base,
            "dias_fiebre_base3": sum(1 for r in self.ventana(dia, 3) if r["temp"] >= temp_base + 1.0),
            "sueno_hoy": hoy.get("sueno"),
            "noches_bajo6": self.seguidos(dia, lambda r: (r.get("sueno") or 9) < 6),
            "dias_animo4": self.seguidos(dia, lambda r: (r.get("animo") or 10) <= 4),
            "dias_animo3": self.seguidos(dia, lambda r: (r.get("animo") or 10) <= 3),
            "dias_estres7": self.seguidos(dia, lambda r: (r.get("estres") or 0) >= 7),
            "reaccion": reaccion, "dia_reaccion": dia_r,
            "lapsos": self.por_dia[dia_r].get("lapsos") if dia_r else None,
            "reaccion_delta": reaccion / b["reaccion"] - 1 if reaccion else None,
            "orto": orto, "dia_orto": dia_o,
            "kcal7": kcal7, "frac_kcal7": kcal7 / b["calorias"] if kcal7 else None,
            "dias_bajo_kcal3": sum(1 for r in self.ventana(dia, 3) if (r.get("calorias") or b["calorias"]) < 0.8 * b["calorias"]),
            "peso": peso, "dia_peso": dia_peso,
            "perdida_peso_pct": 100 * (b["peso"] - peso) / b["peso"] if peso else None,
            "eco": eco, "dia_eco": dia_eco,
            "frec_trombosis": {s: f(s) for s in SINTOMAS_TROMBOSIS},
            "sintomas_trombosis_3d": sum(1 for s in SINTOMAS_TROMBOSIS if f(s, 3) > 0),
            "urinario": {s: f(s) for s in SINTOMAS_URINARIOS},
            "urinario_3d": {s: f(s, 3) for s in SINTOMAS_URINARIOS},
            "frec": {s: f(s) for s in SINTOMAS},
            "mareo_3d": f("mareo", 3),
            "palpitaciones_hoy": "palpitaciones" in hoy.get("sintomas", []),
            "sep_real_hoy": bool(hoy.get("sep_real")),
            "spo2_hoy": hoy.get("spo2"), "pa_hoy": (hoy.get("pa_sis"), hoy.get("pa_dia")),
            "fc7": self.prom(dia, "fc"), "pas7": self.prom(dia, "pa_sis"), "pad7": self.prom(dia, "pa_dia"),
            "spo2_7": self.prom(dia, "spo2"), "sueno7": self.prom(dia, "sueno"), "animo7": self.prom(dia, "animo"),
            "estres7": self.prom(dia, "estres"), "co2_7": self.prom(dia, "co2"), "agua7": self.prom(dia, "agua"),
            "contacto": hoy.get("contacto"), "cohesion7": self.prom(dia, "cohesion"),
            "actividad7": self.prom(dia, "actividad"), "actividad_base": b.get("actividad"),
            "ruido7": self.prom(dia, "ruido"),
            "res14": self.prom(dia, "resistencia", 14), "aer14": self.prom(dia, "aerobico", 14),
            "osea": self.osea[dia], "muscular": self.muscular[dia], "dosis": self.dosis[dia], "micro": self.micro[dia],
        }

    def puntajes(self, dia, m=None):
        m = m or self.metricas(dia)
        b = self.base
        fr, ft, fu = m["frec"], m["frec_trombosis"], m["urinario"]
        res14, aer14 = m["res14"] or 60, m["aer14"] or 60
        orto = (m["orto"] or {}).get("indice", 0)
        reac = max(rampa(m["reaccion_delta"], 0.05, 0.25), rampa(m["lapsos"], 1, 6))
        p = {
            "cardiovascular": 0.25 * rampa(m["fc7"] - b["fc"], 3, 18) + 0.17 * rampa(m["pas7"], 130, 160)
                              + 0.22 * rampa(1 - aer14 / 60, 0.15, 0.8) + 0.08 * rampa(b["spo2"] - m["spo2_7"], 1, 5)
                              + 0.13 * min(1, 2 * fr["palpitaciones"]) + 0.15 * rampa(orto, 0.6, 1.2),
            "trombosis": 0.6 * PESO_ECO.get(m["eco"], 0)
                         + 0.4 * min(1, 1.5 * ft["hinchazon_cuello"] + ft["edema_facial"] + 0.5 * ft["edema_parpados"]),
            "respiratorio": 0.55 * rampa(b["spo2"] - m["spo2_7"], 0.8, 5) + 0.30 * rampa(m["co2_7"], 3, 5.5)
                            + 0.15 * fr["congestion"],
            "oseo": 0.85 * rampa(m["osea"], 1, 6) + 0.15 * fr["dolor_espalda"],
            "muscular": 0.8 * rampa(m["muscular"], 1, 10) + 0.2 * rampa(1 - res14 / 60, 0.2, 0.9),
            "urinario": 0.35 * rampa(2.5 - m["agua7"], 0, 1) + 0.20 * rampa(m["osea"], 2, 6)
                        + 0.45 * min(1, 1.5 * fu["dolor_costado"] + fu["dolor_orinar"] + 1.5 * fu["dificultad_orinar"]),
            "mental": 0.30 * rampa(b["animo"] - m["animo7"], 0.5, 4) + 0.25 * rampa(m["estres7"], 4.5, 8.5)
                      + 0.30 * rampa(b["sueno"] - m["sueno7"], 0.3, 2.5) + 0.15 * reac,
            "ojos": 0.35 * rampa(m["micro"], 30, 200) + 0.35 * min(1, fr["vision_borrosa"] + 0.5 * fr["cefalea"])
                    + 0.30 * rampa(m["co2_7"], 2.5, 4.5),
            "inmune": 0.30 * rampa(m["dosis"], 50, 450) + 0.18 * rampa(b["sueno"] - m["sueno7"], 0.3, 2.5)
                      + 0.17 * rampa(m["estres7"], 5, 9) + 0.22 * rampa(m["delta_t3"], 0.4, 1.4)
                      + 0.13 * min(1, 2 * fr["erupcion"]),
            "nutricion": 0.55 * rampa(m["perdida_peso_pct"], 2, 10) + 0.45 * rampa(1 - (m["frac_kcal7"] or 1), 0.05, 0.35),
        }
        if m["eco"] == "trombo":
            p["trombosis"] = max(p["trombosis"], 0.85)
        return {s: round(100 * min(1.0, v)) for s, v in p.items()}

    @staticmethod
    def general(puntajes):
        v = list(puntajes.values())
        return round(0.5 * max(v) + 0.5 * sum(v) / len(v))

    def historial(self, hasta, dias=60):
        rango = [d for d in range(max(1, hasta - dias + 1), hasta + 1) if d in self.por_dia]
        series = {s: [] for s in SISTEMAS}
        for d in rango:
            for s, v in self.puntajes(d).items():
                series[s].append(v)
        return rango, series

    def pronostico(self, dia, serie, sistema, horizonte=30):
        ys = serie[-21:]
        n = len(ys)
        xs = list(range(n))
        mx, my = sum(xs) / n, sum(ys) / n
        den = sum((x - mx) ** 2 for x in xs)
        pendiente = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else 0
        sin_plan, con_plan = [], []
        v_sin = v_con = serie[-1]
        for k in range(1, horizonte + 1):
            paso = pendiente * 0.97 ** k
            ef = efecto_planes(self.astro["planes"], dia + k)
            freno = min(0.9, sum(PLANES[t][1].get(sistema, 0) * a for t, a in ef.items() if t in PLANES))
            v_sin = max(0, min(100, v_sin + paso))
            v_con = max(0, min(100, v_con + (paso * (1 - freno) if paso > 0 else paso) - 0.5 * freno))
            sin_plan.append(round(v_sin, 1))
            con_plan.append(round(v_con, 1))
        return sin_plan, con_plan

    def protocolos(self, dia, entorno="nave", alerta=None, m=None):
        m = m or self.metricas(dia)
        b, hoy, out = self.base, self.por_dia[dia], []
        amb = ENTORNOS[entorno]
        avisar_tierra = _("Avisar al cirujano de vuelo en la siguiente ventana de comunicación.")

        def agregar(clave, titulo, nivel, motivo, pasos, plan=None, fuentes=()):
            quien = AVISO_FIJO.get(clave, AVISO_POR_NIVEL[nivel])
            aviso = _(ESCALAMIENTO[quien])
            if quien == "tierra":
                if amb["retraso_largo"]:
                    aviso += " " + _("Cada mensaje tarda {retraso}: empieza los pasos sin esperar respuesta.", retraso=_(amb["retraso_txt"]))
                else:
                    aviso += " " + _("El retraso es de {retraso}: contáctalos ahora.", retraso=_(amb["retraso_txt"]))
            nv = nivel_de(PUNTAJE_DE_NIVEL[nivel])
            out.append({"clave": clave, "titulo": _(titulo), "nivel": nivel, "nombre_nivel": nv["nombre"], "color": nv["color"],
                        "motivo": motivo, "pasos": [p if p == avisar_tierra else _(p) for p in pasos],
                        "avisar": quien, "quien": aviso,
                        "plan": plan, "plan_nombre": _(PLANES[plan][0]) if plan else None,
                        "fuentes": list(fuentes),
                        "guia": GUIA_PROTOCOLO.get(clave),
                        "riesgo": riesgo(RIESGO_PROTOCOLO[clave]) if clave in RIESGO_PROTOCOLO else None})

        spo2_hoy, spo2_7 = m["spo2_hoy"], m["spo2_7"]
        if spo2_hoy <= 92 or spo2_7 < 95:
            agregar("hipoxemia", "Oxígeno en sangre bajo", "critico" if spo2_hoy <= 88 else "atencion",
                    _("SpO₂ de hoy {hoy} %, promedio de 7 días {prom:.1f} % (normal: 95–100 %).", hoy=spo2_hoy, prom=spo2_7),
                    ["Repetir la medición en reposo y verificar la colocación del sensor.",
                     "Si hay síntomas, ponerse la mascarilla de oxígeno.", "Revisar el CO₂ del módulo.", avisar_tierra],
                    "control_co2", ["spo2_medline", "nasa_hipoxia"])

        if m["fc7"] - b["fc"] >= 10:
            agregar("fc_elevada", "Pulso en reposo elevado", "atencion",
                    _("Promedio de 7 días {prom:.0f} lpm; tu base es {base}.", prom=m["fc7"], base=b["fc"]),
                    ["Medir el pulso al despertar 3 días seguidos.", "Revisar sueño, agua y estrés.",
                     "Registrar un electrocardiograma si el equipo está disponible."], "ejercicio_aerobico", ["fc_normal"])
        pas_hoy, pad_hoy = m["pa_hoy"]
        if pas_hoy > 180 or pad_hoy > 120:
            agregar("pa_elevada", "Presión arterial muy alta", "critico",
                    _("Lectura de hoy: {sis}/{dia} mmHg (crisis: más de 180/120).", sis=pas_hoy, dia=pad_hoy),
                    ["Repetir la medición en 5 minutos, en reposo.",
                     "Si sigue alta o hay dolor de pecho, cambios en la vista o dificultad para hablar, avisar de inmediato.",
                     avisar_tierra], None, ["aha_presion"])
        elif m["pas7"] >= 130 or m["pad7"] >= 80:
            etapa2 = m["pas7"] >= 140 or m["pad7"] >= 90
            agregar("pa_elevada", "Presión arterial elevada", "atencion" if etapa2 else "vigilar",
                    _("Promedio de 7 días: {sis:.0f}/{dia:.0f} mmHg.", sis=m["pas7"], dia=m["pad7"]) + " "
                    + (_("Etapa 2: 140/90 o más.") if etapa2 else _("Etapa 1: 130–139 u 80–89.")),
                    ["Medir dos veces al día durante 3 días.", "Reducir el sodio.", "Mantener el ejercicio aeróbico."],
                    "ejercicio_aerobico", ["aha_presion"])
        if (m["aer14"] or 60) < 40:
            agregar("aerobico", "Poco ejercicio aeróbico", "vigilar",
                    _("Promedio de 14 días: {prom:.0f} min al día (meta: 60). Sin él, el corazón pierde condición.", prom=m["aer14"]),
                    ["Programar 60 min diarios en caminadora o bicicleta.", "Si el equipo falló, reportarlo."],
                    "ejercicio_aerobico", ["csa_ejercicio"])
        if m["palpitaciones_hoy"] or m["frec"]["palpitaciones"] >= 2 / 7:
            grave = m["palpitaciones_hoy"] and (m["mareo_3d"] > 0 or spo2_hoy <= 92)
            agregar("palpitaciones", "Palpitaciones", "critico" if grave else "atencion",
                    _("Palpitaciones en {n} de los últimos 7 días.", n=round(m["frec"]["palpitaciones"] * 7))
                    + (" " + _("Con mareo u oxígeno bajo.") if grave else ""),
                    ["Registrar un electrocardiograma mientras ocurren.", "Reposo y evitar cafeína.",
                     "Anotar cuándo ocurren: con ejercicio, estrés o al dormir.", avisar_tierra],
                    "ejercicio_aerobico", ["nasa_arritmia", "nasa_qtc"])
        o = m["orto"]
        if o and (o["caida_sis"] >= 20 or o["caida_dia"] >= 10 or o["sube_fc"] >= 30):
            con_mareo = m["mareo_3d"] > 0
            agregar("ortostatica", "Intolerancia al ponerse de pie", "critico" if con_mareo else "atencion",
                    _("Prueba del día {dia}: la presión bajó {sis:.0f}/{diast:.0f} mmHg y el pulso subió {fc:.0f} lpm al pararte (criterio: 20/10 mmHg o +30 lpm).",
                      dia=m["dia_orto"], sis=o["caida_sis"], diast=o["caida_dia"], fc=o["sube_fc"])
                    + (" " + _("Con mareo.") if con_mareo else ""),
                    ["Levantarte despacio: primero sentarte un minuto.", "Tomar 500 mL de agua y revisar la sal de la dieta.",
                     "Usar prendas o brazaletes de compresión en muslos si están disponibles.",
                     "No hacer tareas en altura ni caminatas hasta repetir la prueba."],
                    "hidratacion", ["aafp_orto", "scirep_cardio2024"])

        dt, tn = m["delta_t3"], m["temp_base"]
        sint_inf = m["frec"]["erupcion"] > 0 or "fatiga" in hoy.get("sintomas", [])
        if dt >= 1.0 or m["tmax3"] >= 39.4:
            grave = m["tmax3"] >= 39.4 or m["dias_fiebre_base3"] >= 3 or sint_inf
            agregar("fiebre", "Fiebre o posible infección", "critico" if grave else "atencion",
                    _("Máxima de 3 días {tmax:.1f} °C, {dif:+.1f} °C sobre tu normal en vuelo ({normal:.1f} °C).", tmax=m["tmax3"], dif=dt, normal=tn)
                    + (" " + _("Con erupción o fatiga.") if sint_inf else ""),
                    ["Limitar el contacto cercano con la tripulación.", "Hidratación y antipirético según el protocolo.",
                     "Vigilar oxígeno y pulso cada 6 horas.",
                     "En vuelo se reactivan virus latentes: fotografía cualquier erupción.", avisar_tierra],
                    None, ["charite_temp", "mehta_virus", "fiebre"])
        elif dt >= 0.5:
            combinada = (m["sueno7"] or 9) < 6 or m["dias_estres7"] >= 3
            agregar("fiebre", "Temperatura sobre tu normal en vuelo", "vigilar",
                    _("Máxima de 3 días {tmax:.1f} °C, {dif:+.1f} °C sobre tu normal en vuelo ({normal:.1f} °C).", tmax=m["tmax3"], dif=dt, normal=tn)
                    + (" " + _("Con poco sueño o estrés alto: el sistema inmune se debilita.") if combinada else ""),
                    ["Repetir la medición en reposo, 30 minutos después de cualquier ejercicio.",
                     "Revisar la temperatura y el CO₂ de la cabina para descartar el ambiente.",
                     "Vigilar erupciones, dolor de garganta y fatiga."],
                    "higiene_sueno" if combinada else None, ["charite_temp", "fiebre"])
        if m["frec"]["erupcion"] >= 2 / 7:
            agregar("erupcion", "Erupciones en la piel", "vigilar",
                    _("Erupción registrada en {n} de los últimos 7 días.", n=round(m["frec"]["erupcion"] * 7)),
                    ["Fotografiar la zona para el registro médico.",
                     "El estrés del vuelo puede reactivar virus latentes: revisar sueño y estrés.",
                     "Informar al cirujano de vuelo si hay dolor, ampollas o fiebre."], "higiene_sueno", ["mehta_virus"])

        pasos_svt = [avisar_tierra, "Registrar hinchazón de cuello, cara y párpados.",
                     "No iniciar ni suspender medicamentos sin indicación del equipo médico."]
        if m["eco"] == "trombo":
            agregar("trombo", "Posible trombosis en la vena yugular", "critico",
                    _("El ultrasonido del día {dia} detectó un trombo en la vena yugular interna.", dia=m["dia_eco"]),
                    ["Repetir el ultrasonido de la vena yugular interna izquierda.", *pasos_svt], "vigilancia_yugular", ["nasa_vte"])
        elif m["eco"] in ("estasis", "retrogrado"):
            agregar("flujo_yugular", "Flujo anormal en la vena yugular", "atencion",
                    _("Ultrasonido del día {dia}: {resultado}. Puede no dar síntomas (NASA).", dia=m["dia_eco"], resultado=minuscula_inicial(_(ECO[m["eco"]]))),
                    ["Repetir el ultrasonido cada semana.", *pasos_svt], "vigilancia_yugular", ["nasa_vte"])
        elif m["sintomas_trombosis_3d"] >= 2:
            nombres = [minuscula_inicial(_(SINTOMAS[s])) for s in SINTOMAS_TROMBOSIS if m["frec_trombosis"][s] > 0]
            agregar("sintomas_svt", "Síntomas compatibles con trombosis venosa", "atencion",
                    _("En los últimos días: {sintomas}.", sintomas=", ".join(nombres)),
                    ["Hacer un ultrasonido de la vena yugular interna izquierda.", *pasos_svt], "vigilancia_yugular", ["nasa_vte"])

        u3 = m["urinario_3d"]
        if u3["dificultad_orinar"] > 0:
            agregar("retencion_urinaria", "Dificultad para orinar (posible retención)", "atencion",
                    _("Dificultad para orinar en los últimos 3 días. En vuelo, 12 de 16 casos de retención ocurrieron tras tomar medicamentos para el mareo."),
                    ["Intentar orinar con calma, en una posición cómoda.", "Revisar si tomaste medicamentos para el mareo.",
                     "Si no puedes vaciar la vejiga, avisar: puede requerir una sonda.", avisar_tierra],
                    None, ["nasa_urinario", "nasa_urinario_tb"])
        if u3["dolor_costado"] > 0:
            factores = []
            if m["agua7"] < 2.5:
                factores.append(_("tomas {agua:.1f} L de agua al día", agua=m["agua7"]))
            if m["osea"] >= 2:
                factores.append(_("pérdida ósea estimada de {pct:.1f} %", pct=m["osea"]))
            agregar("calculo_renal", "Posible cálculo renal", "atencion",
                    _("Dolor fuerte en el costado en los últimos 3 días.")
                    + (" " + _("Factores de riesgo: {factores}.", factores="; ".join(factores)) if factores else ""),
                    ["Aumentar los líquidos.", "Analgésico según el protocolo.", "Ultrasonido renal si el equipo está disponible.",
                     "Vigilar fiebre, náuseas y sangre en la orina.", avisar_tierra],
                    "hidratacion", ["nasa_urinario", "nasa_renal"])
        if u3["dolor_orinar"] >= 2 / 3:
            con_fiebre = dt >= 1.0 or m["tmax3"] >= 38.5
            agregar("infeccion_urinaria", "Posible infección urinaria", "critico" if con_fiebre else "atencion",
                    _("Ardor al orinar en 2 de los últimos 3 días.") + (" " + _("Con fiebre.") if con_fiebre else ""),
                    ["Usar una tira reactiva de orina si está en el botiquín.", "Tomar más líquidos y cuidar la higiene.",
                     "No tomar antibióticos sin indicación del equipo médico.", avisar_tierra],
                    "hidratacion", ["nasa_urinario", "nasa_urinario_tb"])
        if m["agua7"] < 2.5:
            agregar("hidratacion", "Poca agua consumida", "atencion" if m["agua7"] < 2.0 else "vigilar",
                    _("Promedio de 7 días: {prom:.1f} L (NASA asigna mínimo 2.5 L).", prom=m["agua7"]),
                    ["Tomar al menos 2.5 L al día, repartidos.", "Más agua en días de ejercicio intenso."],
                    "hidratacion", ["nasa_agua", "nasa_orina_2l"])

        n6, s7 = m["noches_bajo6"], m["sueno7"]
        if s7 < 6.0 or n6 >= 3 or (m["sueno_hoy"] or 9) < 5:
            partes = [_("Promedio de sueño de 7 días: {prom:.1f} h (NASA programa 8.5 h).", prom=s7)]
            if n6 >= 2:
                partes.append(_("{n} noches seguidas con menos de 6 h.", n=n6))
            if (m["sueno_hoy"] or 9) < 5:
                partes.append(_("Anoche: {h:.1f} h.", h=m["sueno_hoy"]))
            agregar("deuda_sueno", "Deuda de sueño", "atencion", " ".join(partes),
                    ["Mismo horario de descanso todos los días.", "Luz cálida una hora antes de dormir.",
                     "Evitar tareas operativas en la última hora antes de dormir.",
                     "Hacer la prueba de reacción para ver si ya afecta tu atención."],
                    "higiene_sueno", ["jones_sueno", "sueno_barger"])
        elif n6 == 2:
            agregar("deuda_sueno", "Dos noches cortas seguidas", "vigilar", _("Dormiste menos de 6 h dos noches seguidas."),
                    ["Prioriza el descanso esta noche.", "Evita tareas delicadas si te sientes con sueño."],
                    "higiene_sueno", ["jones_sueno"])
        a7 = m["animo7"]
        if m["dias_animo3"] >= 5:
            agregar("bienestar", "Ánimo muy bajo varios días", "critico",
                    _("Ánimo de 3 o menos durante {n} días seguidos.", n=m["dias_animo3"]),
                    ["Contactar hoy al psicólogo de la misión (conferencia privada).",
                     "Avisar a la comandante para ajustar la carga de trabajo.",
                     "Contacto con familia en la próxima ventana."], "apoyo_psicologico", ["nasa_conducta_tb016", "nasa_cognitivo"])
        elif a7 <= b["animo"] - 3 or m["dias_animo4"] >= 3 or a7 <= 5.5 or m["estres7"] >= 6.5:
            agregar("bienestar", "Bienestar psicológico en descenso", "atencion",
                    _("Ánimo promedio {animo:.1f}/10 (tu base: {base}), estrés promedio {estres:.1f}/10.", animo=a7, base=b["animo"], estres=m["estres7"])
                    + (" " + _("Ánimo de 4 o menos {n} días seguidos.", n=m["dias_animo4"]) if m["dias_animo4"] >= 3 else ""),
                    ["Agendar una sesión con el equipo de apoyo psicológico.", "Contacto con familia en la próxima ventana.",
                     "Hablar con la tripulación sobre la carga de trabajo."],
                    "apoyo_psicologico", ["nasa_conducta_tb016", "nasa_cognitivo"])
        if m["reaccion"] is not None:
            lap, dlt = m["lapsos"] or 0, m["reaccion_delta"] or 0
            if lap >= 3 or dlt >= 0.10:
                agregar("reaccion", "Atención más lenta", "atencion" if lap >= 5 or dlt >= 0.20 else "vigilar",
                        _("Prueba del día {dia}: {ms} ms en promedio ({pct:+.0f} % contra tu base) y {lapsos} lapsos de atención.",
                          dia=m["dia_reaccion"], ms=m["reaccion"], pct=dlt * 100, lapsos=lap),
                        ["Evitar tareas críticas (caminatas espaciales, maniobras) hasta repetir la prueba descansado.",
                         "Revisar el sueño de las últimas noches y la carga de trabajo.", "Repetir la prueba mañana a la misma hora."],
                        "higiene_sueno", ["jones_sueno"])
        if dia > 3 and m["mareo_3d"] >= 2 / 3:
            agregar("mareo", "Mareo o desorientación", "vigilar",
                    _("Mareo en 2 de los últimos 3 días, ya pasada la adaptación inicial (el mareo espacial suele durar 2 o 3 días)."),
                    ["Mover la cabeza despacio y fijar la vista en un punto de referencia.",
                     "Evitar caminatas espaciales y tareas delicadas mientras dure.",
                     "Si tomas medicamentos para el mareo, vigila que puedas orinar con normalidad.",
                     "Avisar si dura más de 3 días o aparece con palpitaciones."], None, ["nasa_mareo"])

        pp, fk = m["perdida_peso_pct"], m["frac_kcal7"]
        if (pp is not None and pp >= 5) or m["dias_bajo_kcal3"] >= 3:
            nivel = "critico" if pp is not None and pp >= 10 else "atencion" if pp is not None and pp >= 5 else "vigilar"
            partes = []
            if pp is not None:
                partes.append(_("Peso del día {dia}: {peso} kg, {pct:.1f} % menos que al inicio (5–10 % preocupa a los médicos).",
                                dia=m["dia_peso"], peso=m["peso"], pct=pp))
            if fk is not None:
                partes.append(_("Comes {pct:.0f} % de tu meta de {meta} kcal.", pct=fk * 100, meta=numero(b["calorias"], ",")))
            agregar("nutricion", "Pérdida de peso o pocas calorías", nivel, " ".join(partes),
                    ["Comidas a horario fijo.", "Colaciones entre tareas.", "Pesarte cada semana.",
                     "Si tienes poco apetito varios días, coméntalo en tu conferencia médica."],
                    "alimentacion", ["sciencenews_dieta", "sciencefriday_kcal", "nasa_nutricion"])

        if m["osea"] >= 3:
            agregar("perdida_osea", "Pérdida ósea estimada", "atencion" if m["osea"] >= 4.5 else "vigilar",
                    _("Pérdida estimada en cadera y columna: {pct:.1f} %.", pct=m["osea"]),
                    ["Completar 60 min diarios de ejercicio de resistencia.", "Priorizar sentadillas y peso muerto con carga.",
                     "Revisar calcio y vitamina D."], "ejercicio_resistencia", ["nasa_hueso"])
        if (m["res14"] or 60) < 40:
            agregar("resistencia", "Poco ejercicio de resistencia", "vigilar",
                    _("Promedio de 14 días: {prom:.0f} min al día (meta: 60).", prom=m["res14"]),
                    ["Revisar la agenda de ejercicio con la comandante.",
                     "Si el equipo falló, reportarlo y usar bandas elásticas."], "ejercicio_resistencia", ["csa_ejercicio"])

        if m["frec"]["vision_borrosa"] >= 0.25:
            agregar("sans", "Posible síndrome neuro-ocular (SANS)", "atencion",
                    _("Visión borrosa en {n} de los últimos 7 días.", n=round(m["frec"]["vision_borrosa"] * 7)),
                    ["Prueba de rejilla de Amsler y agudeza visual.", "Registrar dolores de cabeza y su intensidad.",
                     "Reducir el CO₂ en la zona de descanso."], "control_co2", ["nasa_sans", "nasa_co2"])
        if m["co2_7"] >= 2.5:
            supera = m["co2_7"] >= 3.0
            agregar("co2", "CO₂ elevado en cabina", "atencion" if supera else "vigilar",
                    _("CO₂ promedio de 7 días: {co2:.1f} mmHg.", co2=m["co2_7"]) + " "
                    + (_("Supera el límite de NASA de 3 mmHg.") if supera else _("Sobre 2.5 mmHg aumenta el riesgo de dolor de cabeza.")),
                    ["Revisar los filtros del sistema de remoción de CO₂.", "Aumentar la ventilación en la zona de descanso."],
                    "control_co2", ["nasa_co2"])

        if m["ruido7"] is not None and m["ruido7"] > 50:
            fuerte = m["ruido7"] >= 60
            agregar("ruido", "Ruido alto al dormir", "atencion" if fuerte else "vigilar",
                    _("Ruido promedio de 7 noches: {db} dBA.", db=round(m["ruido7"]))
                    + " " + (_("El diseño de las zonas de sueño es de 50 dBA; arriba de 60 dBA se recomienda protección auditiva.")
                             if fuerte else _("Arriba de 50 dBA en las 8 horas de sueño, el médico de vuelo indica medidas.")),
                    ["Usar protección auditiva para dormir.",
                     "Buscar de dónde viene el ruido (ventiladores, bombas, equipo encendido).",
                     "Si no baja, pedir a tierra una revisión acústica."],
                    None, ["nasa_ruido"])

        if m["contacto"] is not None and m["contacto"] >= 7:
            mucho = m["contacto"] >= 14
            agregar("contacto", "Sin contacto personal con la Tierra", "atencion" if mucho else "vigilar",
                    _("{n} días desde la última llamada personal.", n=m["contacto"])
                    + " " + (_("En órbita hay conferencia privada cada dos semanas; ya pasó ese plazo.")
                             if mucho else _("El contacto con familia y amigos es una contramedida, no un premio.")),
                    ["Agendar una llamada o grabar un mensaje para tu familia hoy.",
                     "Pedir conferencia privada con el psicólogo de vuelo.",
                     "Revisar si el paquete personal o las noticias de casa llegaron."],
                    None, ["nasa_bhp", "nasa_aislamiento"])

        if m["cohesion7"] is not None and m["cohesion7"] <= 5:
            grave = m["cohesion7"] <= 3.5
            agregar("cohesion", "Tensión con la tripulación", "atencion" if grave else "vigilar",
                    _("Relación con la tripulación: {v:.1f} de 10 en promedio de 7 días.", v=m["cohesion7"]),
                    ["Hablar con la tripulación del problema concreto, no de la persona.",
                     "Separar el trabajo compartido unos días si la tensión sigue.",
                     "Pedir conferencia privada: la convivencia es uno de los temas que revisa tierra."],
                    None, ["nasa_bhp"])

        if m["actividad7"] is not None and m["actividad_base"]:
            caida = 1 - m["actividad7"] / m["actividad_base"]
            if caida >= 0.07:
                mucha = caida >= 0.15
                agregar("actividad", "Te estás moviendo menos", "atencion" if mucha else "vigilar",
                        _("Actividad despierto {pct} % por debajo de tu normal ({h:.1f} h al día).",
                          pct=round(caida * 100), h=m["actividad7"]),
                        ["Partir el día en bloques con una tarea de pie en cada uno.",
                         "Mantener el ejercicio aunque el ánimo esté bajo: es lo primero que se abandona.",
                         "Avisar a la tripulación: el encierro apaga a cualquiera y se nota desde afuera."],
                        "ejercicio_aerobico", ["mars500"])

        if alerta and alerta["tipo"] == "sep":
            e = alerta["evento"]
            motivo = {"real": _("Evento real de partículas solares del {fecha} UTC.", fecha=e["fecha"]),
                      "simulado": _("Evento SIMULADO para la demostración, fechado el {fecha} UTC.", fecha=e["fecha"]),
                      "ensayo": _("Ensayo con el evento real del {fecha} UTC.", fecha=e["fecha"])}[alerta["origen"]]
            agregar("sep_real", "Tormenta solar detectada por NASA DONKI", "critico",
                    motivo + " "
                    + _("En los próximos días de misión sumará hasta {dosis:.0f} mSv al día sin refugio.", dosis=alerta["dosis_extra"]),
                    ["Trasladarse al refugio blindado antes de que lleguen las partículas.",
                     "Suspender caminatas espaciales y actividades fuera del refugio.",
                     "Llevar el dosímetro personal y anotar la dosis cada día.",
                     "Crear el plan de refugio para que la app calcule la dosis que evitas."],
                    "refugio", ["nasa_donki", "nasa_radiacion_std"])
        elif alerta and alerta["tipo"] == "flr":
            e = alerta["evento"]
            agregar("flr_aviso", "Fulguración solar fuerte: posible tormenta de partículas", "vigilar",
                    (_("Fulguración SIMULADA clase {clase}, fechada el {fecha} UTC.", clase=e["clase"], fecha=e["fecha"])
                     if alerta["origen"] == "simulado" else
                     _("Fulguración clase {clase} el {fecha} UTC (NASA DONKI).", clase=e["clase"], fecha=e["fecha"])) + " "
                    + _("Las fulguraciones fuertes pueden anticipar un evento de partículas en horas."),
                    ["Revisar el camino al refugio y tener listo el dosímetro.",
                     "Evitar programar caminatas espaciales en las próximas horas."], None, ["nasa_donki"])
        from datos import EVENTO_SOLAR
        if EVENTO_SOLAR[0] <= dia <= EVENTO_SOLAR[1] or m["sep_real_hoy"]:
            agregar("sep", "Evento de partículas solares en curso", "critico",
                    _("NASA limita la dosis a {limite} mSv por evento.", limite=LIMITE_EVENTO_SEP),
                    ["Trasladarse de inmediato al refugio blindado.", "Suspender caminatas espaciales y ejercicio fuera del refugio.",
                     "Llevar el dosímetro personal en todo momento."], "refugio", ["nasa_radiacion_std"])
        pct = 100 * m["dosis"] / LIMITE_RADIACION
        if pct >= 40:
            agregar("dosis", "Dosis de radiación acumulada", "atencion" if pct >= 75 else "vigilar",
                    _("{dosis:.0f} mSv: {pct:.0f} % del límite de carrera de NASA ({limite} mSv).", dosis=m["dosis"], pct=pct, limite=LIMITE_RADIACION),
                    ["Revisar las caminatas espaciales restantes.", "Dormir en la zona más blindada."],
                    "refugio", ["nasa_radiacion_std", "nasa_rad_crucero"])

        orden = {"critico": 0, "atencion": 1, "vigilar": 2}
        return sorted(out, key=lambda p: orden[p["nivel"]])

    def signos(self, dia):
        b, hoy = self.base, self.por_dia[dia]

        def tarjeta(nombre, valor, unidad, referencia, nivel="normal", clave=None):
            if isinstance(valor, (int, float)):
                valor = numero(valor)
            t = {"nombre": _(nombre), "valor": valor, "unidad": _(unidad), "referencia": referencia, "nivel": nivel}
            if clave and clave in (hoy.get("reales") or []):
                m = hoy.get("medicion") or {}
                t["medido"] = _("{n} lecturas del reloj el {fecha}", n=m.get("lecturas", 0), fecha=m.get("fecha", ""))
            return t

        presion_alta = hoy["pa_sis"] >= 130 or hoy["pa_dia"] >= 80
        tnormal = self.temp_normal_en_vuelo(dia)
        dt = hoy["temp"] - tnormal
        return [
            tarjeta("Pulso en reposo", hoy["fc"], "lpm", _("Base {v}", v=b["fc"]),
                    "vigilar" if hoy["fc"] - b["fc"] >= 10 else "normal", clave="fc"),
            tarjeta("Presión", f"{hoy['pa_sis']}/{hoy['pa_dia']}", "mmHg", _("Base {v}", v=f"{b['pa_sis']}/{b['pa_dia']}"),
                    "vigilar" if presion_alta else "normal"),
            tarjeta("Oxígeno (SpO₂)", hoy["spo2"], "%", _("Base {v}", v=b["spo2"]),
                    "critico" if hoy["spo2"] <= 88 else "atencion" if hoy["spo2"] <= 92 else "normal"),
            tarjeta("Temperatura", hoy["temp"], "°C", _("Tu normal en vuelo {v:.1f}", v=tnormal),
                    "atencion" if dt >= 1 else "vigilar" if dt >= 0.5 else "normal"),
            tarjeta("Sueño", hoy["sueno"], "h", _("Base {v}", v=b["sueno"]), "vigilar" if hoy["sueno"] < 6 else "normal"),
            tarjeta("Agua", hoy["agua"], "L", _("Meta {v}", v=numero(2.5) + " L"),
                    "atencion" if hoy["agua"] < 2 else "vigilar" if hoy["agua"] < 2.5 else "normal"),
            tarjeta("Calorías", numero(hoy["calorias"], ","), "kcal", _("Meta {v}", v=numero(b["calorias"], ",")),
                    "vigilar" if hoy["calorias"] < 0.8 * b["calorias"] else "normal"),
            tarjeta("Ánimo", hoy["animo"], "/10", _("Base {v}", v=b["animo"]), "vigilar" if hoy["animo"] <= 4 else "normal"),
        ]

    def indicadores(self, dia):
        hoy, filas = self.por_dia.get(dia, {}), []
        for clave, (nombre, unidad, (minimo, maximo), dec) in INDICADORES.items():
            valor = hoy.get(clave)
            prom7 = self.prom(dia, clave)
            antes = _promedio([r.get(clave) for r in self.ventana(dia - 7, 7)]) if dia > 7 else None
            filas.append({"clave": clave, "nombre": _(nombre), "unidad": _(unidad), "valor": valor,
                          "base": self.base.get(clave), "prom7": prom7, "decimales": dec,
                          "cambio": prom7 - antes if prom7 is not None and antes is not None else None,
                          "rango": (minimo, maximo), "fuera": valor is not None and not (minimo <= valor <= maximo)})
        return filas

    def serie(self, hasta, clave, dias=60):
        rango = [d for d in range(max(1, hasta - dias + 1), hasta + 1) if d in self.por_dia]
        return rango, [self.por_dia[d].get(clave) for d in rango]


ETIQUETAS_MAPA = {
    "mental": {"ancla": (280, 80), "texto": (226, 66), "lado": "end", "corto": "Mente y sueño"},
    "ojos": {"ancla": (272, 100), "texto": (212, 114), "lado": "end", "corto": "Ojos"},
    "trombosis": {"ancla": (288, 130), "texto": (334, 112), "lado": "start", "corto": "Venas del cuello"},
    "respiratorio": {"ancla": (258, 185), "texto": (196, 186), "lado": "end", "corto": "Pulmones"},
    "cardiovascular": {"ancla": (293, 185), "texto": (366, 202), "lado": "start", "corto": "Corazón"},
    "inmune": {"ancla": (310, 170), "texto": (366, 156), "lado": "start", "corto": "Inmune y radiación"},
    "nutricion": {"ancla": (298, 227), "texto": (366, 248), "lado": "start", "corto": "Nutrición"},
    "urinario": {"ancla": (262, 258), "texto": (196, 258), "lado": "end", "corto": "Riñones"},
    "oseo": {"ancla": (256, 286), "texto": (196, 318), "lado": "end", "corto": "Huesos"},
    "muscular": {"ancla": (302, 358), "texto": (366, 362), "lado": "start", "corto": "Músculos"},
}
