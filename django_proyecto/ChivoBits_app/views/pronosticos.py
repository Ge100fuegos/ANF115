from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ChivoBits_app.forms import GenerarPronosticoForm, SerieExcelForm, SerieManualForm
from ChivoBits_app.metodos import generar_pronosticos
from ChivoBits_app.models import DatoSerie, SerieHistorica


def pronostico_lista(request):
    series = SerieHistorica.objects.annotate(num_datos=Count("datos")).order_by("-creada")
    return render(request, "pronosticos/lista.html", {"series": series})


def _guardar_serie(form, valores):
    with transaction.atomic():
        serie = form.save()
        DatoSerie.objects.bulk_create([
            DatoSerie(serie=serie, periodo=i, valor=Decimal(str(round(v, 2))))
            for i, v in enumerate(valores, start=1)
        ])
    return serie


def crear_manual(request):
    form = SerieManualForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        serie = _guardar_serie(form, form.cleaned_data["valores"])
        messages.success(request, f"Serie '{serie}' creada con {serie.datos.count()} datos.")
        return redirect("pronostico_detalle", pk=serie.pk)
    return render(request, "pronosticos/serie_form.html",
                  {"form": form, "titulo": "Nueva serie (ingreso manual)"})


def importar_excel(request):
    form = SerieExcelForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        serie = _guardar_serie(form, form.cleaned_data["lista_valores"])
        messages.success(request, f"Se importaron {serie.datos.count()} datos.")
        return redirect("pronostico_detalle", pk=serie.pk)
    return render(request, "pronosticos/serie_form.html",
                  {"form": form, "titulo": "Importar serie desde Excel"})


def pronostico_detalle(request, pk):
    serie = get_object_or_404(SerieHistorica, pk=pk)
    y = serie.valores()

    if request.method == "POST":
        form = GenerarPronosticoForm(request.POST)
        if form.is_valid():
            try:
                generar_pronosticos(serie, form.cleaned_data["metodos"],
                                    form.cleaned_data["n_periodos"], form.cleaned_data["k"])
                return redirect("pronostico_detalle", pk=serie.pk)
            except ValueError as e:
                form.add_error(None, str(e))
    else:
        form = GenerarPronosticoForm()

    pronosticos = list(serie.pronosticos.all())
    n_hist = len(y)
    max_n = max((len(p.resultados) for p in pronosticos), default=0)

    historicos = [{"etiqueta": serie.etiqueta(i), "valor": v} for i, v in enumerate(y, start=1)]
    filas = [
        {
            "etiqueta": serie.etiqueta(n_hist + i + 1),
            "valores": [p.resultados[i] if i < len(p.resultados) else None for p in pronosticos],
        }
        for i in range(max_n)
    ]

    grafica = {
        "titulo": serie.nombre,
        "labels": [serie.etiqueta(i) for i in range(1, n_hist + max_n + 1)],
        "datasets": [{"label": "Histórico", "color": "#6b7280", "data": y + [None] * max_n}] + [
            {
                "label": p.nombre_metodo,
                "color": p.color,
                # arranca en el último dato real para que la línea quede unida
                "data": [None] * (n_hist - 1) + [y[-1]] + p.resultados
                        + [None] * (max_n - len(p.resultados)),
            }
            for p in pronosticos
        ],
    }

    con_error = [p for p in pronosticos if p.mape is not None]
    mejor = min(con_error, key=lambda p: p.mape) if con_error else None

    return render(request, "pronosticos/detalle.html", {
        "serie": serie, "form": form, "historicos": historicos,
        "pronosticos": pronosticos, "filas": filas, "grafica": grafica, "mejor": mejor,
    })


@require_POST
def pronostico_eliminar(request, pk):
    get_object_or_404(SerieHistorica, pk=pk).delete()
    messages.success(request, "Serie eliminada.")
    return redirect("pronostico_lista")   