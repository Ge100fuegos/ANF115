from datetime import date

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from ChivoBits_app.dupont_proforma import (FILAS_BG, FILAS_ER, PCT_TODOS, armar_tabla, calcular_dupont,
                                           efectos_dupont, proyectar, supuestos_historicos)
from ChivoBits_app.models import AnalisisFinanciero, Proforma
from ChivoBits_app.ratios_calculos import CONCEPTOS, GRUPOS, RATIOS, calcular_ratios, verificar_balance
from ChivoBits_app.views.analisis_vh import _datos_estado
from ChivoBits_app.views.dupont_proforma import FACTORES_3, FACTORES_5, _r, _tabla


def _seccion_ratios(analisis, periodos):
    anios = [p.anio for p in periodos]
    resultados = calcular_ratios(analisis.periodos_lista(), analisis.usar_promedios)
    sin_inventario = all(not (p.valores.get("inventarios") or 0) for p in periodos)
    omitir = {"rotacion_inventario", "dias_inventario"} if sin_inventario else set()

    grupos = []
    for grupo in GRUPOS:
        filas = []
        for clave, (g, nombre, unidad, formula, descripcion, _) in RATIOS.items():
            if g != grupo or clave in omitir:
                continue
            valores = [resultados[clave].get(a) for a in anios]
            variacion = None
            if len(valores) >= 2 and None not in valores[-2:]:
                variacion = valores[-1] - valores[-2]
            filas.append({"nombre": nombre, "unidad": unidad, "formula": formula,
                          "valores": valores, "variacion": variacion})
        grupos.append((grupo, filas))

    conceptos = [{"etiqueta": etq, "estado": est, "valores": [p.valores.get(clave, 0) for p in periodos]}
                 for clave, (etq, est) in CONCEPTOS.items()]
    advertencias = [f"{p.anio}: {m}" for p in periodos if (m := verificar_balance(p.valores))]
    return {"anios": anios, "grupos": grupos, "conceptos": conceptos,
            "advertencias": advertencias, "sin_inventario": sin_inventario}


def _seccion_dupont(analisis):
    filas = calcular_dupont(analisis.periodos_lista(), analisis.usar_promedios)
    efectos = [{k: (v * 100 if isinstance(v, float) else v) for k, v in e.items()} for e in efectos_dupont(filas)]
    return {
        "anios": [f["anio"] for f in filas],
        "tabla3": _tabla(filas, FACTORES_3),
        "tabla5": _tabla(filas, FACTORES_5),
        "efectos": efectos,
        "grafica": {
            "anios": [str(f["anio"]) for f in filas],
            "roe": [_r(f["roe"], factor=100) for f in filas],
            "roa": [_r(f["roa"], factor=100) for f in filas],
            "margen": [_r(f["margen_neto"], factor=100) for f in filas],
        },
    }


def _seccion_proforma(analisis):
    periodos = analisis.periodos_lista()
    anios = [a for a, _ in periodos]
    guardado = Proforma.objects.filter(analisis=analisis).first()
    s = guardado.supuestos if guardado and guardado.supuestos.get("anio_base") in anios \
        else supuestos_historicos(periodos)
    columnas = proyectar(dict(periodos)[s["anio_base"]], s)
    etiquetas = dict(PCT_TODOS)
    return {
        "s": s,
        "guardado": guardado is not None,
        "pct": [(etiquetas[k], v) for k, v in s["pct"].items() if k in etiquetas],
        "columnas": columnas,
        "tabla_er": armar_tabla(columnas, FILAS_ER),
        "tabla_bg": armar_tabla(columnas, FILAS_BG),
        "fer": columnas[-1]["fer_acumulado"],
        "excedente": -columnas[-1]["fer_acumulado"],
        "ultimo_anio": columnas[-1]["anio"],
        "grafica": {
            "anios": [str(c["anio"]) for c in columnas],
            "real": [c["real"] for c in columnas],
            "ventas": [_r(c["ventas_netas"]) for c in columnas],
            "utilidad": [_r(c["utilidad_neta"]) for c in columnas],
        },
    }


def reporte_analisis(request, pk):
    analisis = get_object_or_404(AnalisisFinanciero, pk=pk)
    periodos = list(analisis.periodos.all())
    estados_vh = [d for d in (_datos_estado(analisis, "BG"), _datos_estado(analisis, "ER")) if d]
    if not periodos and not estados_vh:
        messages.warning(request, "El análisis no tiene datos para generar el reporte.")
        return redirect("ratios_detalle", pk=analisis.pk)

    return render(request, "ratios/reporte.html", {
        "analisis": analisis,
        "fecha": date.today(),
        "periodos": periodos,
        "ratios": _seccion_ratios(analisis, periodos) if periodos else None,
        "estados_vh": estados_vh,
        "dupont": _seccion_dupont(analisis) if periodos else None,
        "proforma": _seccion_proforma(analisis) if periodos else None,
    })