import re
import unicodedata

from datos import INDICADORES
from idiomas import _, numero

UNIDADES = {
    "cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
    "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16, "diecisiete": 17,
    "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiun": 21, "veintiuno": 21,
    "veintiuna": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25,
    "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
}
DECENAS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70,
           "ochenta": 80, "noventa": 90}
CENTENAS = {"cien": 100, "ciento": 100, "doscientos": 200, "doscientas": 200, "trescientos": 300, "trescientas": 300,
            "cuatrocientos": 400, "cuatrocientas": 400, "quinientos": 500, "quinientas": 500, "seiscientos": 600,
            "seiscientas": 600, "setecientos": 700, "setecientas": 700, "ochocientos": 800, "ochocientas": 800,
            "novecientos": 900, "novecientas": 900}


def _normalizar(texto):
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"(\d),(\d{3})\b", r"\1\2", t)
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)
    return t


def _palabras_a_numeros(texto):
    tokens = re.findall(r"\d+(?:\.\d+)?|[a-zñ]+|[^\sa-zñ\d]", texto)
    salida, i = [], 0

    def es_num(tok):
        return tok in UNIDADES or tok in DECENAS or tok in CENTENAS or tok == "mil"

    while i < len(tokens):
        tok = tokens[i]
        if not es_num(tok):
            salida.append(tok); i += 1
            continue
        valor = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok == "mil":
                valor = max(1, valor) * 1000; i += 1
            elif tok in CENTENAS:
                valor += CENTENAS[tok]; i += 1
            elif tok in DECENAS:
                valor += DECENAS[tok]; i += 1
                if i + 1 < len(tokens) and tokens[i] == "y" and tokens[i + 1] in UNIDADES and UNIDADES[tokens[i + 1]] < 10:
                    valor += UNIDADES[tokens[i + 1]]; i += 2
            elif tok in UNIDADES:
                valor += UNIDADES[tok]; i += 1
            else:
                break
        decimal = ""
        if i + 1 < len(tokens) and tokens[i] in ("punto", "coma") and (tokens[i + 1] in UNIDADES or tokens[i + 1].isdigit()):
            d = tokens[i + 1]
            decimal = "." + (d if d.isdigit() else str(UNIDADES[d])); i += 2
        salida.append(f"{valor}{decimal}")
    texto = " ".join(salida)
    texto = re.sub(r"(\d+(?:\.\d+)?)\s+(litros?|horas?|l)\s+y\s+medi[oa]",
                   lambda m: f"{float(m.group(1)) + 0.5:g} {m.group(2)}", texto)
    texto = re.sub(r"\b(?:un\s+|1\s+)?litro\s+y\s+medio", "1.5 litros", texto)
    texto = re.sub(r"\bmedio\s+litro", "0.5 litros", texto)
    return texto


NUM = r"(\d+(?:\.\d+)?)"

REGLAS = [
    ("spo2", r"saturacion|oxigeno|oximetro|spo2", NUM + r"\s*(?:%|por\s*ciento)?", (70, 100)),
    ("temp", r"temperatura|fiebre|termometro|grados", NUM + r"\s*(?:grados|°)?", (34, 42)),
    ("fc", r"pulso|frecuencia|latidos|pulsaciones|lpm|corazon", NUM, (30, 200)),
    ("sueno", r"dormi|sueno|descanse|horas de sueno", NUM + r"\s*(?:horas?|h)\b", (0, 16)),
    ("agua", r"agua|litros?|tome|bebi|hidrat|liquidos", NUM + r"\s*(?:litros?|l)\b", (0, 8)),
    ("calorias", r"calorias|kcal", NUM + r"\s*(?:calorias|kcal)", (300, 6000)),
    ("peso", r"\bpeso\b|\bpese\b|kilos|kilogramos|\bkg\b", NUM + r"\s*(?:kilos?|kilogramos?|kg)?", (30, 200)),
    ("animo", r"animo|humor", NUM, (1, 10)),
    ("estres", r"estres|estresad|ansiedad", NUM, (1, 10)),
    ("resistencia", r"resistencia|pesas|fuerza|ared|sentadillas", NUM + r"\s*(?:minutos|min)\b", (0, 300)),
    ("aerobico", r"aerobic|caminadora|bicicleta|cicloergometro|correr|corri|trote", NUM + r"\s*(?:minutos|min)\b", (0, 300)),
]

def _nombre(campo):
    if campo == "peso":
        return _("Peso"), "kg"
    nombre, unidad, _rango, _dec = INDICADORES[campo]
    return _(nombre), _(unidad)


SINTOMAS_CLAVE = {
    "cefalea": r"dolor de cabeza|me duele la cabeza|cefalea|jaqueca|migrana",
    "vision_borrosa": r"vision borrosa|veo borroso|borros|cambios? en la vista|no veo bien|vista cansada",
    "congestion": r"congestion|nariz tapada|congestionad|nariz congestionada",
    "dolor_espalda": r"dolor de espalda|me duele la espalda|espalda adolorida|lumbago",
    "nauseas": r"nausea|ganas de vomitar|vomit|asco",
    "mareo": r"mare|desorient|vertigo|todo me da vueltas|perdi el equilibrio",
    "fatiga": r"fatiga|cansad|agotad|sin energia|exhaust",
    "palpitaciones": r"palpitacion|corazon acelerado|latido irregular|el corazon me brinca|taquicardia|arritmia",
    "erupcion": r"erupcion|sarpullido|ronchas|comezon|irritacion en la piel|granitos",
    "hinchazon_cuello": r"cuello hinchado|hinchazon en el cuello|se me hincho el cuello",
    "edema_facial": r"cara hinchada|cara inflamada|rostro hinchado|hinchazon en la cara",
    "edema_parpados": r"parpados hinchados|ojos hinchados|parpados inflamados",
    "dolor_orinar": r"ardor al orinar|dolor al orinar|me arde al orinar|arde orinar|ardor en la orina",
    "dificultad_orinar": r"dificultad para orinar|no puedo orinar|cuesta orinar|cuesta trabajo orinar|no vacio la vejiga|retencion",
    "dolor_costado": r"dolor en el costado|dolor de costado|dolor de rinon|me duele el costado|dolor en la espalda baja|colico",
}
NEGACION = r"\b(no|sin|nada de|ningun|ninguna|tampoco|ya no)\b"

ECO_CLAVE = [("trombo", r"trombo|coagulo"), ("retrogrado", r"retrogrado|invertido|al reves"),
             ("estasis", r"estasis|lento|estancado"), ("normal", r"normal|bien|sin hallazgos")]


def _frases(texto):
    partes = re.split(r"(?<!\d)\.|\.(?!\d)|[;:!?\n,]|\bpero\b|\bademas\b|\btambien\b", texto)
    return [f.strip() for f in partes if f and f.strip()]


def _negada(frase, inicio):
    previo = " ".join(frase[:inicio].split()[-4:])
    return re.search(NEGACION, previo) is not None


def interpretar(texto):
    texto = (texto or "")[:2000]
    limpio = _palabras_a_numeros(_normalizar(texto))
    valores, sintomas, descartados, eco, reconocido, usadas = {}, [], [], None, [], set()

    m = re.search(r"\b(?:presion|tension|ta|pa)\b\D{0,20}?(\d{2,3})\s*(?:/|sobre|entre|con|y)?\s*(\d{2,3})", limpio) \
        or re.search(r"\b(\d{2,3})\s*(?:/|sobre)\s*(\d{2,3})\b", limpio)
    if m:
        sis, dia = int(m.group(1)), int(m.group(2))
        if 70 <= sis <= 220 and 40 <= dia <= 140 and sis > dia:
            valores["pa_sis"], valores["pa_dia"] = sis, dia
            limpio = limpio[:m.start()] + " " + limpio[m.end():]

    for i, frase in enumerate(_frases(limpio)):
        consumidos = []
        for campo, claves, patron, (lo, hi) in REGLAS:
            if campo in valores:
                continue
            k = re.search(claves, frase)
            if not k:
                continue
            candidatos = [n for n in re.finditer(patron, frase)
                          if not any(n.start(1) < b and a < n.end(1) for a, b in consumidos)]
            if not candidatos:
                continue
            def dist(n):
                hueco = frase[n.end():k.start()] if n.end() <= k.start() else frase[k.end():n.start()]
                return len(hueco) + (30 if re.search(r"\by\b", hueco) else 0)
            n = min(candidatos, key=dist)
            if dist(n) > 40:
                continue
            v = float(n.group(1))
            if campo == "temp" and v > 50:
                v = round((v - 32) * 5 / 9, 1)
            if lo <= v <= hi:
                valores[campo] = round(v, 1) if campo in ("temp", "sueno", "agua", "peso") else int(round(v))
                consumidos.append((n.start(1), n.end(1)))
                usadas.add(i)

        for s, patron in SINTOMAS_CLAVE.items():
            k = re.search(patron, frase)
            if k and s not in sintomas:
                if _negada(frase, k.start()):
                    if s not in descartados:
                        descartados.append(s)
                else:
                    sintomas.append(s)
                usadas.add(i)

    u = re.search(r"ultrasonido|\beco(?:grafia)?\b|yugular", limpio)
    if u:
        ventana = limpio[u.start():u.end() + 60]
        for clave, patron in ECO_CLAVE:
            if re.search(patron, ventana):
                eco = clave
                break
        frases = _frases(limpio)
        for j, f in enumerate(frases):
            if f in ventana:
                usadas.add(j)

    for c, v in valores.items():
        nombre, unidad = _nombre(c)
        reconocido.append(f"{nombre}: {numero(v, 'g')} {unidad}".replace(" /10", "/10"))
    sintomas = [s for s in sintomas if s not in descartados]
    return {"valores": valores, "sintomas": sintomas, "descartados": descartados, "eco": eco,
            "reconocido": reconocido,
            "sin_reconocer": [f for j, f in enumerate(_frases(limpio)) if j not in usadas]}
