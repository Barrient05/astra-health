from idiomas import N_

RIDGE = {
    "R": N_("Radiación"),
    "I": N_("Aislamiento y confinamiento"),
    "D": N_("Distancia de la Tierra"),
    "G": N_("Campos gravitatorios"),
    "E": N_("Entornos cerrados u hostiles"),
}

SISTEMA_RIDGE = {
    "cardiovascular": ["G", "R"],
    "trombosis": ["G"],
    "respiratorio": ["E"],
    "oseo": ["G"],
    "muscular": ["G"],
    "urinario": ["G", "E"],
    "mental": ["I", "D", "E"],
    "ojos": ["G", "E"],
    "inmune": ["R", "E", "I"],
    "nutricion": ["D", "I"],
}

ZONAS = [
    {"zona": N_("Estación Espacial (órbita baja)"), "tasa": "0.2 – 0.5", "fuente": "nasa_iss_dosis"},
    {"zona": N_("Crucero interplanetario"), "tasa": "1.8", "fuente": "nasa_rad_crucero"},
    {"zona": N_("Superficie lunar"), "tasa": "1.37", "fuente": "luna_change4"},
    {"zona": N_("Superficie de Marte"), "tasa": "0.67", "fuente": "nasa_rad_marte"},
]
