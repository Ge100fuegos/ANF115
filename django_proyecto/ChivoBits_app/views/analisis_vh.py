from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ChivoBits_app.analisis_vh import calcular_vertical_horizontal, detectar_base
from ChivoBits_app.forms import CargarEstadoForm
from ChivoBits_app.models import AnalisisFinanciero, LineaEstado


def _datos_estado(analisis, estado):
    lineas_db = list(analisis.lineas.filter(estado=estado))
    if not lineas_db:
        return None
    lineas = [{"nombre": l.nombre, "es_titulo": l.es_titulo, "valores": l.valores} for l in lineas_db]
    anios = sorted({int(a) for l in lineas_db for a in l.valores})

    indice = next((i for i, l in enumerate(lineas_db) if l.es_base), None)
    if indice is None:
        indice = detectar_base(lineas, estado)

    filas = calcular_vertical_horizontal(lineas, anios, indice)
    pares = [f"{anios[i - 1]} – {anios[i]}" for i in range(1, len(anios))]
    return {
        "codigo": estado,
        "nombre": dict(LineaEstado.ESTADOS)[estado],
        "anios": anios,
        "pares": pares,
        "filas": filas,
        "base_id": lineas_db[indice].pk,
        "base_nombre": lineas_db[indice].nombre,
        "opciones_base": [(l.pk, l.nombre) for l in lineas_db if not l.es_titulo],
        "total_columnas": 1 + 2 * len(anios) + 2 * len(pares),
    }


def vh_detalle(request, pk):
    analisis = get_object_or_404(AnalisisFinanciero, pk=pk)
    estados = [d for d in (_datos_estado(analisis, "BG"), _datos_estado(analisis, "ER")) if d]
    return render(request, "ratios/vh_detalle.html", {
        "analisis": analisis, "estados": estados, "url_actual": "ratios_lista",
    })


def vh_cargar(request, pk):
    analisis = get_object_or_404(AnalisisFinanciero, pk=pk)
    form = CargarEstadoForm(request.POST or None, request.FILES or None,
                            initial={"estado": request.GET.get("estado", "BG")})
    if request.method == "POST" and form.is_valid():
        estado = form.cleaned_data["estado"]
        indice = detectar_base(form.lineas, estado)
        with transaction.atomic():
            analisis.lineas.filter(estado=estado).delete()
            LineaEstado.objects.bulk_create([
                LineaEstado(analisis=analisis, estado=estado, orden=i, nombre=l["nombre"][:255],
                            es_titulo=l["es_titulo"], es_base=(i == indice), valores=l["valores"])
                for i, l in enumerate(form.lineas)
            ])
        nombre = dict(LineaEstado.ESTADOS)[estado]
        messages.success(request, f"{nombre} cargado: {len(form.lineas)} filas, años "
                                  f"{', '.join(str(a) for a in form.anios)}. "
                                  f"Base del análisis vertical: {form.lineas[indice]['nombre']}.")
        return redirect("vh_detalle", pk=analisis.pk)
    return render(request, "ratios/vh_cargar.html", {
        "form": form, "analisis": analisis, "url_actual": "ratios_lista",
    })


@require_POST
def vh_cambiar_base(request, pk, estado):
    linea = get_object_or_404(LineaEstado, pk=request.POST.get("linea"),
                              analisis_id=pk, estado=estado, es_titulo=False)
    with transaction.atomic():
        LineaEstado.objects.filter(analisis_id=pk, estado=estado).update(es_base=False)
        linea.es_base = True
        linea.save(update_fields=["es_base"])
    messages.success(request, f"Nueva base del análisis vertical: {linea.nombre}.")
    return redirect("vh_detalle", pk=pk)


@require_POST
def vh_eliminar(request, pk, estado):
    LineaEstado.objects.filter(analisis_id=pk, estado=estado).delete()
    messages.success(request, f"{dict(LineaEstado.ESTADOS).get(estado, estado)} eliminado.")
    return redirect("vh_detalle", pk=pk)