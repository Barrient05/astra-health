import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

CARPETA = Path(__file__).resolve().parent.parent
ENTRADA = CARPETA / "datos" / "reloj"
SALIDA = CARPETA / "datos" / "reloj.json"
MINIMO_LECTURAS = 30
NOCHE = ("00:00", "06:00")


def leer(carpeta):
    por_dia = defaultdict(list)
    archivos = sorted(carpeta.glob("*.csv"))
    if not archivos:
        raise SystemExit(f"No hay ningún CSV en {carpeta}")
    for archivo in archivos:
        with archivo.open(encoding="utf-8-sig", newline="") as f:
            for fila in csv.DictReader(f):
                marca = fila.get("fecha_hora_mexico") or fila.get("fecha_hora_utc")
                pulso = fila.get("bpm")
                if not marca or not pulso:
                    continue
                try:
                    por_dia[marca[:10]].append((marca[11:16], int(pulso)))
                except ValueError:
                    continue
    return por_dia, [a.name for a in archivos]


def en_reposo(lecturas):
    noche = sorted(p for hora, p in lecturas if NOCHE[0] <= hora <= NOCHE[1])
    if noche:
        cuarto_bajo = noche[:max(1, len(noche) // 4)]
        return round(statistics.median(cuarto_bajo))
    todo = sorted(p for _, p in lecturas)
    return todo[int(len(todo) * 0.05)]


def resumir(por_dia):
    dias = []
    for fecha in sorted(por_dia):
        lecturas = por_dia[fecha]
        if len(lecturas) < MINIMO_LECTURAS:
            continue
        pulsos = [p for _, p in lecturas]
        dias.append({"fecha": fecha, "reposo": en_reposo(lecturas),
                     "media": round(statistics.mean(pulsos)), "maximo": max(pulsos),
                     "lecturas": len(lecturas)})
    return dias


def main():
    por_dia, archivos = leer(ENTRADA)
    dias = resumir(por_dia)
    if not dias:
        raise SystemExit("Ningún día llegó al mínimo de lecturas.")
    reposos = [d["reposo"] for d in dias]
    datos = {
        "origen": "Exportación de un reloj inteligente (Mi Fitness)",
        "archivos": archivos,
        "lecturas_totales": sum(len(v) for v in por_dia.values()),
        "metodo": ("Pulso en reposo por día: mediana del cuarto más bajo de las lecturas "
                   "de 00:00 a 06:00; si ese día no hubo lecturas de madrugada, percentil 5 "
                   "de todo el día."),
        "linea_base": round(statistics.median(reposos[:30])),
        "dias": dias,
    }
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(dias)} días ({dias[0]['fecha']} a {dias[-1]['fecha']}) "
          f"de {datos['lecturas_totales']} lecturas → {SALIDA.name}")
    print(f"Pulso en reposo: mínimo {min(reposos)}, mediana {round(statistics.median(reposos))}, "
          f"máximo {max(reposos)} lpm. Línea base: {datos['linea_base']} lpm.")


if __name__ == "__main__":
    main()
