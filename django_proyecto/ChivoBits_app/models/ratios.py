from django.db import models


class AnalisisFinanciero(models.Model):
    empresa = models.CharField("Empresa", max_length=150)
    descripcion = models.CharField("Descripción", max_length=255, blank=True)
    usar_promedios = models.BooleanField(
        "Usar saldos promedio (año actual + anterior) en rotaciones y rentabilidad", default=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.empresa

    def periodos_lista(self):
        return [(p.anio, p.valores) for p in self.periodos.all()]


class EstadoPeriodo(models.Model):
    analisis = models.ForeignKey(AnalisisFinanciero, on_delete=models.CASCADE, related_name="periodos")
    anio = models.PositiveIntegerField("Año")
    valores = models.JSONField(default=dict)

    class Meta:
        ordering = ["anio"]
        unique_together = ("analisis", "anio")

    def __str__(self):
        return f"{self.analisis} - {self.anio}"

class LineaEstado(models.Model):
    ESTADOS = [("BG", "Balance General"), ("ER", "Estado de Resultados")]

    analisis = models.ForeignKey(AnalisisFinanciero, on_delete=models.CASCADE, related_name="lineas")
    estado = models.CharField(max_length=2, choices=ESTADOS)
    orden = models.PositiveIntegerField()
    nombre = models.CharField(max_length=255)
    es_titulo = models.BooleanField(default=False)
    es_base = models.BooleanField(default=False)
    valores = models.JSONField(default=dict)   # {"2019": 123.0, "2020": 456.0}

    class Meta:
        ordering = ["estado", "orden"]

    def __str__(self):
        return self.nombre


class Proforma(models.Model):
    analisis = models.OneToOneField(AnalisisFinanciero, on_delete=models.CASCADE, related_name="proforma")
    supuestos = models.JSONField(default=dict)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Proforma - {self.analisis}"