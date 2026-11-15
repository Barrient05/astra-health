from idiomas import _

CAPACIDADES = [(80, "no_disponible"), (60, "reducida"), (35, "limitada"), (0, "plena")]


def nombre_capacidad(clave):
    if clave == "no_disponible":
        return _("No disponible")
    if clave == "reducida":
        return _("Reducida")
    if clave == "limitada":
        return _("Limitada")
    return _("Plena")

ROL_MEDICO = "Especialista médica"
ROL_MANDO = "Comandante"

SISTEMAS_QUE_IMPIDEN_ASISTIR = ("mental", "cardiovascular", "trombosis", "respiratorio")


def capacidad(puntajes):
    peor = max(puntajes.get(s, 0) for s in SISTEMAS_QUE_IMPIDEN_ASISTIR)
    for limite, clave in CAPACIDADES:
        if peor >= limite:
            return clave, peor
    return "plena", peor


def puede_asistir(clave):
    return clave in ("plena", "limitada")


def estado(tarjetas, rol_original):
    gente = []
    for t in tarjetas:
        clave, peor = capacidad(t["puntajes"])
        gente.append({**t, "capacidad": clave, "capacidad_txt": nombre_capacidad(clave), "limitante": peor,
                      "asiste": puede_asistir(clave),
                      "medico": rol_original.get(t["id"]) == ROL_MEDICO,
                      "mando": rol_original.get(t["id"]) == ROL_MANDO})
    return gente


def respaldo_de(gente, quien_id):
    otros = [g for g in gente if g["id"] != quien_id and g["asiste"]]
    if not otros:
        return None
    otros.sort(key=lambda g: (not g["medico"], g["limitante"]))
    return otros[0]


def resumen(gente, quien_id):
    disponibles = [g for g in gente if g["asiste"]]
    medico = next((g for g in gente if g["medico"]), None)
    respaldo = respaldo_de(gente, quien_id)

    if not respaldo:
        nivel = "critico"
        aviso = _("Nadie más de la tripulación está en condiciones de asistir hoy. Todo protocolo que diga «avisa a tu tripulación» depende de tierra, con el retraso del entorno.")
    elif medico and not medico["asiste"]:
        nivel = "atencion"
        aviso = _("La especialista médica no está en condiciones de asistir. El respaldo de hoy es {nombre} ({rol}), sin formación médica.", nombre=respaldo["nombre"], rol=respaldo["rol"])
    elif len(disponibles) <= 2:
        nivel = "vigilar"
        aviso = _("Solo {n} de {total} están en condiciones de asistir. La tripulación tiene poco margen si alguien más se deteriora.", n=len(disponibles), total=len(gente))
    else:
        nivel = "normal"
        aviso = _("La tripulación tiene respaldo: {n} de {total} pueden asistir.", n=len(disponibles), total=len(gente))

    return {"gente": gente, "disponibles": len(disponibles), "total": len(gente),
            "respaldo": respaldo, "nivel": nivel, "aviso": aviso}
