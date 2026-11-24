from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from ChivoBits_app.dupont_proforma import (FILAS_BG, FILAS_ER, armar_tabla, calcular_dupont, efectos_dupont,
                                           generar_plantilla_proforma, proyectar, supuestos_historicos)
from ChivoBits_app.forms import ImportarProformaForm, ProformaForm
from ChivoBits_app.models import AnalisisFinanciero, Proforma

# (clave, nombre, unidad, fórmula)
FACTORES_3 = [
    ("margen_neto", "Margen neto", "%", "Utilidad neta / Ventas netas"),
    ("rotacion", "Rotación de activos totales", "veces", "Ventas netas / Activo total"),
    ("roa", "ROA", "%", "Margen neto × Rotación de activos"),
    ("multiplicador", "Multiplicador del capital (apalancamiento)", "veces", "Activo total / Patrimonio"),
    ("roe", "ROE (DuPont)", "%", "ROA × Multiplicador del capital"),
    ("roe_directo", "ROE directo (comprobación)", "%", "Utilidad neta / Patrimonio"),
]
FACTORES_5 = [
    ("carga_fiscal", "Carga fiscal", "veces", "Utilidad neta / Utilidad antes de impuestos"),
    ("carga_intereses", "Carga de intereses", "veces", "Utilidad antes de impuestos / Utilidad de operación"),
    ("margen_operativo", "Margen operativo", "%", "Utilidad de operación / Ventas netas"),
    ("rotacion", "Rotación de activos totales", "veces", "Ventas netas / Activo total"),
    ("multiplicador", "Multiplicador del capital", "veces", "Activo total / Patrimonio"),
    ("roe_5", "ROE (DuPont ampliado)", "%", "Producto de los cinco factores"),
]


def _tabla(filas, factores):
    tabla = []
    for clave, nombre, unidad, formula in factores:
        valores = []
        for f in filas:
            v = f[clave]
            valores.append(v * 100 if v is not None and unidad == "%" else v)
        tabla.append({"nombre": nombre, "unidad": unidad, "formula": formula, "valores": valores,
                      "es_total": clave in ("roe", "roe_5")})
    return tabla

def _r(v, d=2, factor=1):
    return None if v is None else round(v * factor, d)

def _sin_datos(request, analisis):
    messages.warning(request, "Primero agrega o importa los estados financieros con el botón «Importar Excel».")
    return redirect("ratios_detalle", pk=analisis.pk)


def dupont_detalle(request, pk):
    analisis = get_object_or_404(AnalisisFinanciero, pk=pk)
    periodos = analisis.periodos_lista()
    if not periodos:
        return _sin_datos(request, analisis)

    filas = calcular_dupont(periodos, analisis.usar_promedios)
    efectos = [{k: (v * 100 if isinstance(v, float) else v) for k, v in e.items()} for e in efectos_dupont(filas)]
    ultimo = filas[-1]
    arbol = {k: (ultimo[k] * 100 if ultimo[k] is not None and k in ("margen_neto", "roa", "roe") else ultimo[k])
             for k in ("margen_neto", "rotacion", "roa", "multiplicador", "roe", "utilidad_neta",
                       "ventas", "activo", "patrimonio")}

    
    grafica = {
        "anios": [str(f["anio"]) for f in filas],
        "roe": [_r(f["roe"], factor=100) for f in filas],
        "roa": [_r(f["roa"], factor=100) for f in filas],
        "margen": [_r(f["margen_neto"], factor=100) for f in filas],
        "rotacion": [_r(f["rotacion"], 4) for f in filas],
        "multiplicador": [_r(f["multiplicador"], 4) for f in filas],
        "efectos": {
            "periodos": [e["periodo"] for e in efectos],
            "margen": [_r(e["margen"]) for e in efectos],
            "rotacion": [_r(e["rotacion"]) for e in efectos],
            "multiplicador": [_r(e["multiplicador"]) for e in efectos],
        },
    }
    return render(request, "ratios/dupont.html", {
        "analisis": analisis,
        "grafica": grafica,
        "anios": [f["anio"] for f in filas],
        "tabla3": _tabla(filas, FACTORES_3),
        "tabla5": _tabla(filas, FACTORES_5),
        "efectos": efectos,
        "arbol": arbol,
        "anio_arbol": ultimo["anio"],
        "url_actual": "ratios_lista",
    })


def proforma_detalle(request, pk):
    analisis = get_object_or_404(AnalisisFinanciero, pk=pk)
    periodos = analisis.periodos_lista()
    if not periodos:
        return _sin_datos(request, analisis)
    anios = [a for a, _ in periodos]

    guardado = Proforma.objects.filter(analisis=analisis).first()
    restablecer = request.GET.get("restablecer") == "1"
    if restablecer or guardado is None:
        base = request.GET.get("base", "")
        s = supuestos_historicos(periodos, int(base) if base.isdigit() else None)
    else:
        s = guardado.supuestos
        if s.get("anio_base") not in anios:
            messages.warning(request, f"El año base {s.get('anio_base')} ya no existe; se usan los datos del último año.")
            s = supuestos_historicos(periodos)

    form = ProformaForm(request.POST or None, anios=anios, supuestos=s)
    if request.method == "POST" and form.is_valid():
        Proforma.objects.update_or_create(analisis=analisis, defaults={"supuestos": form.supuestos()})
        messages.success(request, "Supuestos guardados y proforma recalculado.")
        return redirect("proforma_detalle", pk=analisis.pk)

    columnas = proyectar(dict(periodos)[s["anio_base"]], s)
    grafica = {
        "anios": [str(c["anio"]) for c in columnas],
        "real": [c["real"] for c in columnas],
        "ventas": [_r(c["ventas_netas"]) for c in columnas],
        "utilidad": [_r(c["utilidad_neta"]) for c in columnas],
        "fer": [_r(c["fer_acumulado"]) for c in columnas[1:]],
        "anios_fer": [str(c["anio"]) for c in columnas[1:]],
    }
    return render(request, "ratios/proforma.html", {
        "analisis": analisis,
        "grafica": grafica,
        "form": form,
        "anios": anios,
        "s": s,
        "columnas": columnas,
        "tabla_er": armar_tabla(columnas, FILAS_ER),
        "tabla_bg": armar_tabla(columnas, FILAS_BG),
        "fer": columnas[-1]["fer_acumulado"],
        "excedente": -columnas[-1]["fer_acumulado"],
        "ultimo_anio": columnas[-1]["anio"],
        "sin_guardar": restablecer or guardado is None,
        "url_actual": "ratios_lista",
    })

def proforma_importar(request, pk):
    analisis = get_object_or_404(AnalisisFinanciero, pk=pk)
    anios = [p.anio for p in analisis.periodos.all()]
    form = ImportarProformaForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        s = form.supuestos
        if s["anio_base"] not in anios:
            form.add_error("archivo", f"El año base {s['anio_base']} no existe en este análisis. "
                                      f"Años disponibles: {', '.join(map(str, anios)) or 'ninguno'}.")
        else:
            Proforma.objects.update_or_create(analisis=analisis, defaults={"supuestos": s})
            messages.success(request, f"Supuestos importados: año base {s['anio_base']}, "
                                      f"{len(s['crecimiento'])} años proyectados.")
            return redirect("proforma_detalle", pk=analisis.pk)
    return render(request, "ratios/proforma_importar.html", {
        "form": form, "analisis": analisis, "url_actual": "ratios_lista",
    })


def proforma_plantilla(request, pk):
    analisis = get_object_or_404(AnalisisFinanciero, pk=pk)
    periodos = analisis.periodos_lista()
    if not periodos:
        return _sin_datos(request, analisis)
    guardado = Proforma.objects.filter(analisis=analisis).first()
    s = guardado.supuestos if guardado else supuestos_historicos(periodos)
    respuesta = HttpResponse(
        generar_plantilla_proforma(s),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    respuesta["Content-Disposition"] = f'attachment; filename="supuestos_proforma_{analisis.pk}.xlsx"'
    return respuesta