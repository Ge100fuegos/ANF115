from django.db import models
from .usuario import Usuario

class Cuenta(models.Model):
    TIPOS_CUENTA = [
        ('ACTIVO', 'Activo'),
        ('PASIVO', 'Pasivo'),
        ('PATRIMONIO', 'Patrimonio'),
        ('INGRESO', 'Ingreso'),
        ('GASTO', 'Gasto'),
    ]
    
    NIVELES = [
        (1, 'Grupo'),
        (2, 'Subgrupo'),
        (3, 'Cuenta'),
        (4, 'Subcuenta'),
    ]
    
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=15, choices=TIPOS_CUENTA)
    nivel = models.IntegerField(choices=NIVELES, default=3)
    saldo = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    cuenta_padre = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcuentas')
    activa = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    def save(self, *args, **kwargs):
        # Determinar nivel automáticamente basado en la longitud del código
        if len(self.codigo) == 1:
            self.nivel = 1
        elif len(self.codigo) == 2:
            self.nivel = 2
        elif len(self.codigo) == 4:
            self.nivel = 3
        else:
            self.nivel = 4
        super().save(*args, **kwargs)

class CentroCosto(models.Model):
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
class PeriodoContable(models.Model):
    ESTADOS = [
        ('ACTIVO', 'Activo'),
        ('CERRADO', 'Cerrado'),
        ('FINALIZADO', 'Finalizado'),
    ]
    
    año = models.IntegerField(unique=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(max_length=10, choices=ESTADOS, default='ACTIVO')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Periodo {self.año} - {self.estado}"
    
    class Meta:
        ordering = ['-año']
    
    @property
    def puede_cerrar(self):
        """Verifica si el periodo puede ser cerrado"""
        from django.db.models import Sum
        from decimal import Decimal
        
        total_debe = Transaccion.objects.filter(
            periodo=self
        ).aggregate(total=Sum('debe'))['total'] or Decimal('0')
        
        total_haber = Transaccion.objects.filter(
            periodo=self
        ).aggregate(total=Sum('haber'))['total'] or Decimal('0')
        
        return total_debe == total_haber

class Transaccion(models.Model):
    fecha = models.DateField()
    cuenta = models.ForeignKey(Cuenta, on_delete=models.RESTRICT)
    centro_costo = models.ForeignKey(CentroCosto, on_delete=models.RESTRICT, null=True, blank=True)
    debe = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    haber = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    descripcion = models.TextField()
    es_ajuste = models.BooleanField(default=False)
    usuario = models.ForeignKey(Usuario, on_delete=models.RESTRICT, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    periodo = models.ForeignKey('PeriodoContable', on_delete=models.RESTRICT, null=True, blank=True)  # Permitir null temporalmente
    numero_transaccion = models.IntegerField(default=1)  # Valor por defecto

    def __str__(self):
        return f"{self.fecha} - {self.descripcion[:30]}"
    
    class Meta:
        ordering = ['-fecha', '-id']
    
    def save(self, *args, **kwargs):
        if not self.numero_transaccion and self.periodo:
            # Obtener el último número de transacción para este periodo
            ultima_transaccion = Transaccion.objects.filter(
                periodo=self.periodo
            ).order_by('-numero_transaccion').first()
            self.numero_transaccion = (ultima_transaccion.numero_transaccion + 1) if ultima_transaccion else 1
        super().save(*args, **kwargs)