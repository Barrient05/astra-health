from idiomas import N_, _

URL_HRP = "https://www.nasa.gov/hrp/risks/"
URL_VTE = "https://www.nasa.gov/organizations/ochmo/risk-of-venous-thromboembolism-during-spaceflight/"

RIESGOS = {
    "inmune": (N_("Respuestas alteradas del sistema inmune"), "Risk of Altered Immune System Responses",
               "https://www.nasa.gov/reference/risk-of-altered-immune-system-responses/"),
    "vestibular": (N_("Función sensoriomotora y vestibular alterada"), "Risk of Altered Sensorimotor and Vestibular Function",
                   "https://www.nasa.gov/reference/risk-of-altered-sensorimotor-and-vestibular-function/"),
    "cardiovascular": (N_("Adaptaciones cardiovasculares"), "Risk of Cardiovascular Adaptations",
                       "https://www.nasa.gov/reference/risk-of-cardiovascular-adaptations/"),
    "descompresion": (N_("Enfermedad por descompresión"), "Risk of Decompression Sickness",
                      "https://www.nasa.gov/reference/risk-of-decompression-sickness/"),
    "microorganismos": (N_("Interacciones huésped–microorganismos"), "Risk of Host-Microorganism Interactions",
                        "https://www.nasa.gov/reference/risk-of-host-microorganism-interactions/"),
    "hipoxia": (N_("Hipoxia"), "Risk of Hypoxia", "https://www.nasa.gov/reference/risk-of-hypoxia/"),
    "nutricion": (N_("Alimentación y nutrición inadecuadas"), "Risk of Inadequate Food and Nutrition",
                  "https://www.nasa.gov/reference/risk-of-inadequate-food-and-nutrition/"),
    "eva": (N_("Lesiones y bajo desempeño en caminatas espaciales"), "Risk of Injury and Compromised Performance from Spacewalks",
            "https://www.nasa.gov/reference/risk-of-injury-and-compromised-performance-from-extravehicular-activity-eva/"),
    "condicion": (N_("Menor condición cardiorrespiratoria y musculoesquelética"), "Risk of Reduced Cardiorespiratory and Musculoskeletal Fitness",
                  "https://www.nasa.gov/reference/risk-of-reduced-cardiorespiratory-and-musculoskeletal-fitness/"),
    "sans": (N_("Síndrome neuro-ocular asociado al vuelo espacial (SANS)"), "Risk of Spaceflight Associated Neuro-ocular Syndrome (SANS)",
             "https://www.nasa.gov/reference/risk-of-spaceflight-associated-neuro-ocular-syndrome-sans/"),
    "hueso": (N_("Cambios óseos inducidos por el vuelo espacial"), "Risk of Spaceflight-Induced Bone Changes",
              "https://www.nasa.gov/reference/risk-of-spaceflight-induced-bone-changes/"),
    "conducta": (N_("Cambios de conducta y trastornos psiquiátricos"), "Risk of Behavioral Changes and Psychiatric Disorders",
                 "https://www.nasa.gov/reference/risk-of-behavioral-conditions-and-psychiatric-disorders/"),
    "equipo": (N_("Trabajo en equipo inadecuado"), "Risk of Inadequate Teamwork",
               "https://www.nasa.gov/reference/risk-of-inadequate-teamwork/"),
    "sueno": (N_("Sueño insuficiente y horarios irregulares"), "Risk of Inadequate Sleep and Irregular Schedules",
              "https://www.nasa.gov/reference/risk-from-inadequate-sleep-and-irregular-schedules/"),
    "sistemas": (N_("Apoyo inadecuado a la operación de sistemas"), "Risk of Inadequate Systems Operations Support",
                 "https://www.nasa.gov/reference/risk-of-inadequate-systems-operations-support/"),
    "cargas": (N_("Lesiones por cargas dinámicas"), "Risk of Injury from Dynamic Loads",
               "https://www.nasa.gov/reference/risk-of-injury-from-dynamic-loads/"),
    "cancer": (N_("Cáncer inducido por radiación"), "Risk of Radiation-Induced Cancers",
               "https://www.nasa.gov/reference/risk-of-radiation-induced-cancers/"),
    "vte": (N_("Tromboembolismo venoso durante el vuelo espacial"), "Risk of Venous Thromboembolism During Spaceflight",
            URL_VTE),
    "arritmia": (N_("Problemas del ritmo cardiaco durante el vuelo espacial"), "Risk of Cardiac Rhythm Problems During Spaceflight",
                 "https://ntrs.nasa.gov/citations/20170005625"),
    "urinario": (N_("Retención urinaria, infección urinaria y cálculos renales"), "Urinary Retention, UTI and Renal Stones in Spaceflight",
                 "https://www.nasa.gov/?p=860466"),
}

RIESGOS_POR_SISTEMA = {
    "cardiovascular": ["cardiovascular", "arritmia", "condicion"],
    "trombosis": ["vte"],
    "urinario": ["urinario", "hueso"],
    "respiratorio": ["hipoxia"],
    "oseo": ["hueso"],
    "muscular": ["condicion"],
    "mental": ["conducta", "sueno"],
    "ojos": ["sans"],
    "inmune": ["inmune", "cancer"],
    "nutricion": ["nutricion", "hueso"],
}

COBERTURA = {
    "inmune": ("cubierto", N_("Sistema inmune y radiación: fiebre, erupciones, sueño, estrés y dosis acumulada.")),
    "vestibular": ("parcial", N_("Se registran mareo y náuseas, con protocolo; no hay pruebas de equilibrio.")),
    "cardiovascular": ("cubierto", N_("Frecuencia cardiaca, presión y palpitaciones contra la línea base; prueba de pie al llegar a la Luna o a Marte.")),
    "descompresion": ("no", N_("Requiere datos de caminatas espaciales y del traje.")),
    "microorganismos": ("no", N_("Requiere análisis de microbioma.")),
    "hipoxia": ("cubierto", N_("SpO₂ y CO₂ en cabina.")),
    "nutricion": ("cubierto", N_("Calorías contra la meta, peso semanal (pérdida de 5 % y 10 %) e hidratación diaria (meta de NASA: 2.5 L).")),
    "eva": ("no", N_("Fuera del alcance del prototipo.")),
    "condicion": ("cubierto", N_("Ejercicio de resistencia y aeróbico; pérdida muscular estimada.")),
    "sans": ("cubierto", N_("Visión borrosa, dolor de cabeza, días de vuelo y CO₂.")),
    "hueso": ("cubierto", N_("Pérdida ósea estimada según el ejercicio de resistencia.")),
    "conducta": ("cubierto", N_("Ánimo y estrés contra la línea base; prueba de reacción de 3 minutos.")),
    "equipo": ("no", N_("Posible siguiente módulo: encuesta breve de clima de equipo.")),
    "sueno": ("cubierto", N_("Horas de sueño contra la línea base y noches seguidas con menos de 6 h.")),
    "sistemas": ("no", N_("Fuera del alcance del prototipo.")),
    "cargas": ("no", N_("Ocurre en el aterrizaje, fuera de la fase monitoreada.")),
    "cancer": ("parcial", N_("Dosis acumulada contra el límite de carrera; no estima probabilidad de cáncer.")),
}


def riesgos_de(sistema):
    return [riesgo(k) for k in RIESGOS_POR_SISTEMA.get(sistema, [])]


def riesgo(clave):
    nombre, oficial, url = RIESGOS[clave]
    return {"clave": clave, "nombre": _(nombre), "oficial": oficial, "url": url}
