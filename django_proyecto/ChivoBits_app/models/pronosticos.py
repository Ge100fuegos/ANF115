from django.db import models
from ChivoBits_app.metodos import METODOS


class SerieHistorica(models.Model):
    FRECUENCIAS = [("periodo", "Período genérico (1, 2, 3…)"), ("mensual", "Mensual"), ("anual", "Anual")]

    nombre = models.CharField("Nombre", max_length=150)
    descripcion = models.CharField("Descripción", max_length=255, blank=True)
    frecuencia = models.CharField("Frecuencia", max_length=10, choices=FRECUENCIAS, default="periodo")
    anio_inicio = models.PositiveIntegerField("Año inicial", null=True, blank=True)
    mes_inicio = models.PositiveSmallIntegerField("Mes inicial", null=True, blank=True)
    creada = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

    def etiqueta(self, periodo):
        if self.frecuencia == "anual" and self.anio_inicio:
            return str(self.anio_inicio + periodo - 1)
        if self.frecuencia == "mensual" and self.anio_inicio:
            total = (self.mes_inicio or 1) - 1 + periodo - 1
            return f"{self.anio_inicio + total // 12}-{total % 12 + 1:02d}"
        return str(periodo)

    def valores(self):
        return [float(d.valor) for d in self.datos.all()]


class DatoSerie(models.Model):
    serie = models.ForeignKey(SerieHistorica, on_delete=models.CASCADE, related_name="datos")
    periodo = models.PositiveIntegerField()
    valor = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        ordering = ["periodo"]
        unique_together = ("serie", "periodo")


class Pronostico(models.Model):
    serie = models.ForeignKey(SerieHistorica, on_delete=models.CASCADE, related_name="pronosticos")
    metodo = models.CharField(max_length=30, choices=[(k, v[0]) for k, v in METODOS.items()])
    n_periodos = models.PositiveIntegerField()
    resultados = models.JSONField(default=list)
    ajustados = models.JSONField(default=list)
    parametros = models.JSONField(default=dict)
    mad = models.FloatField(null=True, blank=True)
    mape = models.FloatField(null=True, blank=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        unique_together = ("serie", "metodo")

    @property
    def nombre_metodo(self):
        return METODOS[self.metodo][0]

    @property
    def color(self):
        return METODOS[self.metodo][2]