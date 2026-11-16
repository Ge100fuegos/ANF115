from django import forms
from ChivoBits_app.importador import leer_columna_excel, agrupar_anual
from ChivoBits_app.metodos import METODOS
from ChivoBits_app.models import SerieHistorica

from ChivoBits_app.excel_ratios import leer_plantilla
from ChivoBits_app.models import AnalisisFinanciero
from ChivoBits_app.ratios_calculos import CONCEPTOS, SIEMPRE_POSITIVOS

import re
from ChivoBits_app.analisis_vh import leer_estado_excel, leer_texto_pegado
from ChivoBits_app.models import LineaEstado


class SerieBaseForm(forms.ModelForm):
    class Meta:
        model = SerieHistorica
        fields = ["nombre", "descripcion", "frecuencia", "anio_inicio", "mes_inicio"]

    def clean(self):
        c = super().clean()
        if c.get("frecuencia") == "mensual" and c.get("anio_inicio") and not c.get("mes_inicio"):
            c["mes_inicio"] = 1
        mes = c.get("mes_inicio")
        if mes and not 1 <= mes <= 12:
            self.add_error("mes_inicio", "Debe estar entre 1 y 12.")
        return c


class SerieManualForm(SerieBaseForm):
    valores = forms.CharField(
        label="Valores",
        widget=forms.Textarea(attrs={"rows": 12}),
        help_text="Un valor por línea, en orden. Puedes pegar una columna copiada de Excel.",
    )

    def clean_valores(self):
        valores = []
        for n, linea in enumerate(self.cleaned_data["valores"].splitlines(), start=1):
            texto = linea.strip().replace("$", "").replace(",", "").replace(" ", "")
            if not texto:
                continue
            try:
                valores.append(float(texto))
            except ValueError:
                raise forms.ValidationError(f"Línea {n}: '{linea.strip()}' no es un número.")
        if len(valores) < 2:
            raise forms.ValidationError("Ingresa al menos 2 valores.")
        return valores


class SerieExcelForm(SerieBaseForm):
    archivo = forms.FileField(label="Archivo Excel (.xlsx)")
    hoja = forms.CharField(label="Hoja", required=False, help_text="Vacío = primera hoja")
    columna = forms.CharField(label="Columna de valores", max_length=3, help_text="Ej.: D")
    fila_inicio = forms.IntegerField(label="Fila inicial", min_value=1)
    fila_fin = forms.IntegerField(label="Fila final", min_value=1)
    agrupar = forms.BooleanField(label="Sumar cada 12 meses (convertir a anual)", required=False)

    def clean(self):
        c = super().clean()
        archivo = c.get("archivo")
        if not archivo or self.errors:
            return c
        if not archivo.name.lower().endswith(".xlsx"):
            self.add_error("archivo", "Solo se aceptan archivos .xlsx")
            return c
        if c["fila_fin"] < c["fila_inicio"]:
            self.add_error("fila_fin", "Debe ser mayor o igual a la fila inicial.")
            return c
        try:
            valores = leer_columna_excel(archivo, c.get("hoja"), c["columna"], c["fila_inicio"], c["fila_fin"])
            if c.get("agrupar"):
                valores = agrupar_anual(valores)
                c["frecuencia"] = "anual"
        except ValueError as e:
            raise forms.ValidationError(str(e))
        c["lista_valores"] = valores
        return c


class GenerarPronosticoForm(forms.Form):
    metodos = forms.MultipleChoiceField(
        label="Métodos",
        choices=[(k, v[0]) for k, v in METODOS.items()],
        initial=list(METODOS.keys()),
        widget=forms.CheckboxSelectMultiple,
    )
    n_periodos = forms.IntegerField(label="Períodos a pronosticar", min_value=1, max_value=120, initial=5)
    k = forms.IntegerField(label="Períodos del promedio móvil", min_value=2, initial=3)


class AnalisisForm(forms.ModelForm):
    class Meta:
        model = AnalisisFinanciero
        fields = ["empresa", "descripcion", "usar_promedios"]


class EstadoPeriodoForm(forms.Form):
    anio = forms.IntegerField(label="Año", min_value=1900, max_value=2100)

    def __init__(self, *args, analisis=None, instancia=None, **kwargs):
        if instancia is not None:
            kwargs["initial"] = {"anio": instancia.anio, **instancia.valores}
        super().__init__(*args, **kwargs)
        self.analisis = analisis
        self.instancia = instancia
        for clave, (etiqueta, _) in CONCEPTOS.items():
            self.fields[clave] = forms.DecimalField(
                label=etiqueta, max_digits=18, decimal_places=2, required=False, initial=0)

    def clean_anio(self):
        anio = self.cleaned_data["anio"]
        qs = self.analisis.periodos.filter(anio=anio)
        if self.instancia is not None:
            qs = qs.exclude(pk=self.instancia.pk)
        if qs.exists():
            raise forms.ValidationError(f"Ya existe el año {anio} en este análisis.")
        return anio

    def valores(self):
        datos = {}
        for clave in CONCEPTOS:
            v = float(self.cleaned_data.get(clave) or 0)
            datos[clave] = abs(v) if clave in SIEMPRE_POSITIVOS else v
        return datos

    def campos_por_estado(self):
        grupos = {}
        for clave, (_, estado) in CONCEPTOS.items():
            grupos.setdefault(estado, []).append(self[clave])
        return list(grupos.items())


class ImportarRatiosForm(forms.Form):
    archivo = forms.FileField(label="Plantilla de Excel (.xlsx)")

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if not archivo.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Solo se aceptan archivos .xlsx")
        try:
            self.periodos = leer_plantilla(archivo)
        except ValueError as e:
            raise forms.ValidationError(str(e))
        return archivo

class CargarEstadoForm(forms.Form):
    METODOS = [("excel", "Subir archivo Excel"), ("pegar", "Pegar filas copiadas de Excel")]

    estado = forms.ChoiceField(label="Estado financiero", choices=LineaEstado.ESTADOS)
    metodo = forms.ChoiceField(label="Forma de carga", choices=METODOS,
                               widget=forms.RadioSelect, initial="excel")
    # Excel
    archivo = forms.FileField(label="Archivo (.xlsx)", required=False)
    hoja = forms.CharField(label="Hoja", required=False, help_text="Vacío = primera hoja")
    columna_nombres = forms.CharField(label="Columna de nombres de cuentas", max_length=3,
                                      initial="A", required=False)
    fila_encabezado = forms.IntegerField(label="Fila donde están los años", min_value=1, required=False)
    fila_inicio = forms.IntegerField(label="Primera fila de cuentas", min_value=1, required=False)
    fila_fin = forms.IntegerField(label="Última fila de cuentas", min_value=1, required=False)
    # Pegar
    anios = forms.CharField(label="Años (en el orden de las columnas que pegas)", required=False,
                            help_text="Ej.: 2020, 2019")
    texto = forms.CharField(label="Filas copiadas de Excel", required=False,
                            widget=forms.Textarea(attrs={"rows": 14}),
                            help_text="Selecciona en Excel la columna de nombres y las de montos, copia y pega aquí.")

    def clean(self):
        c = super().clean()
        if self.errors:
            return c
        try:
            if c["metodo"] == "excel":
                if not all(c.get(f) for f in ("archivo", "fila_encabezado", "fila_inicio", "fila_fin")):
                    raise ValueError("Completa: archivo, fila de los años, primera y última fila.")
                if not c["archivo"].name.lower().endswith(".xlsx"):
                    raise ValueError("Solo se aceptan archivos .xlsx")
                if c["fila_fin"] < c["fila_inicio"]:
                    raise ValueError("La última fila debe ser mayor o igual a la primera.")
                self.anios, self.lineas = leer_estado_excel(
                    c["archivo"], c.get("hoja"), c.get("columna_nombres") or "A",
                    c["fila_encabezado"], c["fila_inicio"], c["fila_fin"])
            else:
                if not c.get("anios") or not c.get("texto"):
                    raise ValueError("Escribe los años y pega las filas.")
                try:
                    anios = [int(x) for x in re.split(r"[,\s;]+", c["anios"].strip()) if x]
                except ValueError:
                    raise ValueError("Los años deben ser números separados por coma. Ej.: 2020, 2019")
                self.anios, self.lineas = anios, leer_texto_pegado(c["texto"], anios)
        except ValueError as e:
            raise forms.ValidationError(str(e))
        return c