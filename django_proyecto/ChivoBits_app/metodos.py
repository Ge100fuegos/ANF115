"""Cada método recibe la serie (y) y cuántos períodos proyectar.
Devuelve (futuros, ajustados, parametros). 'ajustados' son los valores que el
método habría dado sobre los datos históricos; sirven para medir el error."""
from django.db import transaction


def minimos_cuadrados(y, n_futuros):
    n = len(y)
    x = list(range(1, n + 1))
    sx, sy = sum(x), sum(y)
    sxy = sum(a * b for a, b in zip(x, y))
    sx2 = sum(a * a for a in x)
    b = (n * sxy - sx * sy) / (n * sx2 - sx ** 2)
    a = (sy - b * sx) / n
    futuros = [a + b * xi for xi in range(n + 1, n + n_futuros + 1)]
    ajustados = [a + b * xi for xi in x]
    return futuros, ajustados, {"a": a, "b": b, "ecuación": f"Y = {a:,.4f} + {b:,.4f}X"}


def incremento_absoluto(y, n_futuros):
    incrementos = [y[i] - y[i - 1] for i in range(1, len(y))]
    inc = sum(incrementos) / len(incrementos)
    futuros = [y[-1] + inc * i for i in range(1, n_futuros + 1)]
    ajustados = [None] + [y[i - 1] + inc for i in range(1, len(y))]
    return futuros, ajustados, {"incremento promedio": inc}


def incremento_porcentual(y, n_futuros):
    if any(v == 0 for v in y[:-1]):
        raise ValueError("Incremento porcentual: la serie tiene valores en 0 (no se puede dividir).")
    tasas = [(y[i] - y[i - 1]) / y[i - 1] for i in range(1, len(y))]
    t = sum(tasas) / len(tasas)
    futuros, ultimo = [], y[-1]
    for _ in range(n_futuros):
        ultimo = ultimo * (1 + t)
        futuros.append(ultimo)
    ajustados = [None] + [y[i - 1] * (1 + t) for i in range(1, len(y))]
    return futuros, ajustados, {"tasa promedio (%)": t * 100}


def promedio_movil(y, n_futuros, k=3):
    k = min(k, len(y))
    datos, futuros = list(y), []
    for _ in range(n_futuros):
        v = sum(datos[-k:]) / k
        futuros.append(v)
        datos.append(v)
    ajustados = [None] * k + [sum(y[i - k:i]) / k for i in range(k, len(y))]
    return futuros, ajustados, {"k": k}


# clave: (nombre, función, color en la gráfica)
METODOS = {
    "minimos_cuadrados": ("Mínimos cuadrados", minimos_cuadrados, "#2563eb"),
    "incremento_absoluto": ("Incremento absoluto", incremento_absoluto, "#16a34a"),
    "incremento_porcentual": ("Incremento porcentual", incremento_porcentual, "#ea580c"),
    "promedio_movil": ("Promedio móvil", promedio_movil, "#9333ea"),
}


def calcular_errores(y, ajustados):
    pares = [(r, a) for r, a in zip(y, ajustados) if a is not None]
    if not pares:
        return None, None
    mad = sum(abs(r - a) for r, a in pares) / len(pares)
    mape = sum(abs((r - a) / r) for r, a in pares if r) / len(pares) * 100
    return mad, mape


def generar_pronosticos(serie, metodos, n_periodos, k=3):
    from .models.pronosticos import Pronostico

    y = serie.valores()
    if len(y) < 2:
        raise ValueError("La serie necesita al menos 2 datos.")

    with transaction.atomic():
        serie.pronosticos.exclude(metodo__in=metodos).delete()
        for clave in metodos:
            funcion = METODOS[clave][1]
            extra = {"k": k} if clave == "promedio_movil" else {}
            futuros, ajustados, params = funcion(y, n_periodos, **extra)
            mad, mape = calcular_errores(y, ajustados)
            Pronostico.objects.update_or_create(
                serie=serie, metodo=clave,
                defaults={
                    "n_periodos": n_periodos,
                    "resultados": [round(v, 2) for v in futuros],
                    "ajustados": [None if v is None else round(v, 2) for v in ajustados],
                    "parametros": {p: round(v, 4) if isinstance(v, float) else v for p, v in params.items()},
                    "mad": mad,
                    "mape": mape,
                },
            )