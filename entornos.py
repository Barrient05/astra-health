from idiomas import N_

ENTORNOS = {
    "nave": {
        "nombre": N_("Nave en tránsito a Marte"),
        "gravedad": 0.0, "gravedad_txt": N_("Microgravedad"),
        "dosis": 1.8,
        "retraso_txt": N_("de 4 a 24 minutos"), "retraso_largo": True,
        "factor_resistencia": 1.0,
        "nota": N_("Lejos de la Tierra: la tripulación debe resolver casi todo por su cuenta."),
        "fuentes": ["nasa_rad_crucero", "nasa_retraso"],
    },
    "estacion": {
        "nombre": N_("Estación espacial en órbita baja"),
        "gravedad": 0.0, "gravedad_txt": N_("Microgravedad"),
        "dosis": 0.4,
        "retraso_txt": N_("menos de un segundo"), "retraso_largo": False,
        "factor_resistencia": 1.0,
        "nota": N_("Comunicación casi inmediata con los médicos de vuelo; regreso a la Tierra posible en horas."),
        "fuentes": ["nasa_iss_dosis"],
    },
    "rover": {
        "nombre": N_("Vehículo explorador en la Luna"),
        "gravedad": 0.166, "gravedad_txt": N_("Gravedad lunar (16.6 % de la terrestre)"),
        "dosis": 1.37,
        "retraso_txt": N_("de 3 a 10 segundos"), "retraso_largo": False,
        "factor_resistencia": 0.5,
        "nota": N_("Espacio reducido: sin equipo grande de resistencia; se usan bandas elásticas."),
        "fuentes": ["luna_change4", "nasa_retraso", "gravedad"],
    },
    "base_marte": {
        "nombre": N_("Base en la superficie de Marte"),
        "gravedad": 0.38, "gravedad_txt": N_("Gravedad marciana (38 % de la terrestre)"),
        "dosis": 0.67,
        "retraso_txt": N_("de 4 a 24 minutos"), "retraso_largo": True,
        "factor_resistencia": 1.0,
        "nota": N_("La atmósfera delgada protege un poco de la radiación; la Tierra sigue a minutos de distancia."),
        "fuentes": ["nasa_rad_marte", "nasa_retraso", "gravedad"],
    },
}

ENTORNO_INICIAL = "nave"

FASES = [
    {"inicio": 1, "fin": 1, "nombre": N_("Lanzamiento y órbita baja"), "tasa": 0.6},
    {"inicio": 2, "fin": 2, "nombre": N_("Cruce de los cinturones de Van Allen"), "tasa": 3.0},
    {"inicio": 3, "fin": 100000, "nombre": N_("Crucero interplanetario"), "tasa": 1.8},
]


def fase_del_dia(dia, entorno=ENTORNO_INICIAL):
    if entorno != "nave":
        return {"inicio": 1, "fin": 100000, "nombre": ENTORNOS[entorno]["nombre"], "tasa": ENTORNOS[entorno]["dosis"]}
    for fase in FASES:
        if fase["inicio"] <= dia <= fase["fin"]:
            return fase
    return FASES[-1]


def entorno_de(mision):
    return ENTORNOS.get(mision.get("entorno", ENTORNO_INICIAL), ENTORNOS[ENTORNO_INICIAL])


def factor_gravedad(g):
    return 1 - 0.6 * min(1.0, (g or 0) / 0.38)
