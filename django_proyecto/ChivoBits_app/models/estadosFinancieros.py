from django.db import models
from .usuario import Usuario

class BalanceComprobacion(models.Model):
    año = models.IntegerField()
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.RESTRICT, null=True, blank=True)
    
    def __str__(self):
        return f"Balance Comprobación {self.año}"
    
    class Meta:
        unique_together = ['año']

class EstadoResultados(models.Model):
    año = models.IntegerField()
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.RESTRICT, null=True, blank=True)
    ingresos_totales = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    gastos_totales = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    utilidad_neta = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    def __str__(self):
        return f"Estado Resultados {self.año}"
    
    class Meta:
        unique_together = ['año']

class BalanceGeneral(models.Model):
    año = models.IntegerField()
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.RESTRICT, null=True, blank=True)
    activos_totales = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    pasivos_totales = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    patrimonio_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    def __str__(self):
        return f"Balance General {self.año}"
    
    class Meta:
        unique_together = ['año']