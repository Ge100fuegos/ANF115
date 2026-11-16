# costos/models.py
from django.db import models
from .contaGeneral import CentroCosto

class Proyecto(models.Model):
    ESTADOS_PROYECTO = [
        ('ACTIVO', 'Activo'),
        ('COMPLETADO', 'Completado'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)
    cliente = models.CharField(max_length=100)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    presupuesto = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    estado = models.CharField(max_length=15, choices=ESTADOS_PROYECTO, default='ACTIVO')
    centro_costo = models.OneToOneField(CentroCosto, on_delete=models.RESTRICT)
    
    class Meta:
        db_table = 'proyecto'
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class Empleado(models.Model):
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)
    puesto = models.CharField(max_length=50)
    salario_hora = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'empleado'
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class CostoDirecto(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.RESTRICT)
    empleado = models.ForeignKey(Empleado, on_delete=models.RESTRICT)
    fecha = models.DateField()
    horas = models.DecimalField(max_digits=6, decimal_places=2)
    descripcion = models.TextField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.proyecto} - {self.empleado} - {self.fecha}"
    
    class Meta:
        db_table = 'costo_directo'
        ordering = ['-fecha', '-id']