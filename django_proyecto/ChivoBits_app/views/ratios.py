from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ChivoBits_app.excel_ratios import generar_plantilla
from ChivoBits_app.forms import AnalisisForm, EstadoPeriodoForm, ImportarRatiosForm
from ChivoBits_app.models import AnalisisFinanciero, EstadoPeriodo
from ChivoBits_app.ratios_calculos import CONCEPTOS, GRUPOS, RATIOS, calcular_ratios, verificar_balance


def ratios_lista(request):
    analisis = AnalisisFinanciero.objects.annotate(num_periodos=Count("periodos")).order_by("-creado")
    return render(request, "ratios/lista.html", {"analisis": analisis, "url_actual": "ratios_lista"})


def ratios_crear(request):
    form = AnalisisForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        analisis = form.save()
        messages.success(request, f"Análisis '{analisis}' creado. Ahora agrega los estados financieros.")
        return redirect("ratios_detalle", pk=analisis.pk)
    return render(request, "ratios/analisis_form.html", {"form": form, "url_actual": "ratios_lista"})


def ratios_detalle(request, pk):
    analisis = get_object_or_404(AnalisisFinanciero, pk=pk)
    periodos = list(analisis.periodos.all())
    anios = [p.anio for p in periodos]
    resultados = calcular_ratios(analisis.periodos_lista(), analisis.usar_promedios)

    grupos = []
    for grupo in GRUPOS:
        filas = []
        for clave, (g, nombre, unidad, formula, descripcion, _) in RATIOS.items():
            if g != grupo:
                continue
            valores = [resultados[clave].get(a) for a in anios]
            variacion = None
            if len(valores) >= 2 and None not in valores[-2:]:
                variacion = valores[-1] - valores[-2]
            filas.append({
                "nombre": nombre, "unidad": unidad, "formula": formula,
                "descripcion": descripcion, "valores": valores, "variacion": variacion,
            })
        grupos.append((grupo, filas))

    conceptos = [
        {"etiqueta": etiqueta, "estado": estado, "valores": [p.valores.get(clave, 0) for p in periodos]}
        for clave, (etiqueta, estado) in CONCEPTOS.items()
    ]

    advertencias = []
    for p in periodos:
        msg = verificar_balance(p.valores)
        if msg:
            advertencias.append(f"{p.anio}: {msg}")

    return render(request, "ratios/detalle.html", {
        "analisis": analisis, "periodos": periodos, "anios": anios,
        "grupos": grupos, "conceptos": conceptos, "advertencias": advertencias,
        "url_actual": "ratios_lista",
    })


def ratios_periodo(request, pk, periodo_id=None):
    analisis = get_object_or_404(AnalisisFinanciero, pk=pk)
    instancia = get_object_or_404(EstadoPeriodo, pk=periodo_id, analisis=analisis) if periodo_id else None
    form = EstadoPeriodoForm(request.POST or None, analisis=analisis, instancia=instancia)

    if request.method == "POST" and form.is_valid():
        valores = form.valores()
        if instancia:
            instancia.anio = form.cleaned_data["anio"]
            instancia.valores = valores
            instancia.save()
        else:
            EstadoPeriodo.objects.create(analisis=analisis, anio=form.cleaned_data["anio"], valores=valores)
        messages.success(request, f"Año {form.cleaned_data['anio']} guardado.")
        aviso = verificar_balance(valores)
        if aviso:
            messages.warning(request, aviso)
        return redirect("ratios_detalle", pk=analisis.pk)

    return render(request, "ratios/periodo_form.html", {
        "form": form, "analisis": analisis, "instancia": instancia, "url_actual": "ratios_lista",
    })


@require_POST
def ratios_periodo_eliminar(request, pk, periodo_id):
    periodo = get_object_or_404(EstadoPeriodo, pk=periodo_id, analisis_id=pk)
    periodo.delete()
    messages.success(request, f"Año {periodo.anio} eliminado.")
    return redirect("ratios_detalle", pk=pk)


def ratios_importar(request, pk):
    analisis = get_object_or_404(AnalisisFinanciero, pk=pk)
    form = ImportarRatiosForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            for anio, valores in form.periodos:
                EstadoPeriodo.objects.update_or_create(
                    analisis=analisis, anio=anio, defaults={"valores": valores})
        anios = ", ".join(str(a) for a, _ in form.periodos)
        messages.success(request, f"Se importaron los años: {anios}.")
        for anio, valores in form.periodos:
            aviso = verificar_balance(valores)
            if aviso:
                messages.warning(request, f"{anio}: {aviso}")
        return redirect("ratios_detalle", pk=analisis.pk)
    return render(request, "ratios/importar.html", {
        "form": form, "analisis": analisis, "url_actual": "ratios_lista",
    })


def ratios_plantilla(request, pk):
    analisis = get_object_or_404(AnalisisFinanciero, pk=pk)
    contenido = generar_plantilla(analisis.periodos_lista())
    respuesta = HttpResponse(
        contenido, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    respuesta["Content-Disposition"] = f'attachment; filename="plantilla_ratios_{analisis.pk}.xlsx"'
    return respuesta


@require_POST
def ratios_eliminar(request, pk):
    get_object_or_404(AnalisisFinanciero, pk=pk).delete()
    messages.success(request, "Análisis eliminado.")
    return redirect("ratios_lista")