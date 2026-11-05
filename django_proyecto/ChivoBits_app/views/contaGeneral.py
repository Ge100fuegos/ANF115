from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from datetime import date, datetime
import json
from ChivoBits_app.models.contaGeneral import *
from decimal import Decimal


def libro(request):
    return render(request, 'ContaGeneral/libroMayor.html')

def menu_conta(request):
    return render(request, 'ContaGeneral/menu.html')


def catalogo_cuentas(request):
    # Obtener todas las cuentas ordenadas por código
    cuentas = Cuenta.objects.all().order_by('codigo')

    # Calcular estadísticas
    total_cuentas = Cuenta.objects.filter(nivel__in=[3, 4]).count()
    cuentas_activo = cuentas.filter(tipo='ACTIVO').count()
    cuentas_pasivo = cuentas.filter(tipo='PASIVO').count()
    cuentas_patrimonio = cuentas.filter(tipo='PATRIMONIO').count()
    cuentas_ingreso = cuentas.filter(tipo='INGRESO').count()
    cuentas_gasto = cuentas.filter(tipo='GASTO').count()

    context = {
        'cuentas': cuentas,
        'total_cuentas': total_cuentas,
        'cuentas_activo': cuentas_activo,
        'cuentas_pasivo': cuentas_pasivo,
        'cuentas_patrimonio': cuentas_patrimonio,
        'cuentas_ingreso': cuentas_ingreso,
        'cuentas_gasto': cuentas_gasto
    }
    return render(request, 'ContaGeneral/catalogoCuentas.html', context)

def libro_mayor(request):
    # Obtener periodo activo
    periodo_activo = PeriodoContable.objects.filter(estado='ACTIVO').first()
    
    # Obtener todos los periodos para el selector
    periodos = PeriodoContable.objects.all().order_by('-año')
    
    # Obtener periodo seleccionado (si se especifica)
    periodo_id = request.GET.get('periodo_id')
    periodo_seleccionado = None
    
    if periodo_id:
        periodo_seleccionado = get_object_or_404(PeriodoContable, id=periodo_id)
    else:
        periodo_seleccionado = periodo_activo
    
    # Obtener cuentas para el filtro
    cuentas = Cuenta.objects.filter(activa=True, nivel__in=[3, 4]).order_by('codigo')
    
    # Obtener transacciones si hay periodo seleccionado
    transacciones = []
    resumen_cuentas = []
    
    if periodo_seleccionado:
        # CAMBIO 1: Excluir ajustes de las transacciones
        transacciones = Transaccion.objects.filter(
            periodo=periodo_seleccionado,
            es_ajuste=False  # ← EXCLUIR AJUSTES
        ).select_related('cuenta', 'centro_costo').order_by('fecha', 'numero_transaccion')
        
        # Calcular resumen por cuenta
        from django.db.models import Sum
        # CAMBIO 2: Excluir ajustes del resumen
        resumen = Transaccion.objects.filter(
            periodo=periodo_seleccionado,
            es_ajuste=False  # ← EXCLUIR AJUSTES
        ).values('cuenta').annotate(
            total_debe=Sum('debe'),
            total_haber=Sum('haber')
        ).order_by('cuenta__codigo')
        
        for item in resumen:
            cuenta = Cuenta.objects.get(id=item['cuenta'])
            saldo_final = item['total_debe'] - item['total_haber']
            resumen_cuentas.append({
                'cuenta': cuenta,
                'total_debe': item['total_debe'],
                'total_haber': item['total_haber'],
                'saldo_final': abs(saldo_final),
                'naturaleza_saldo': 'DEBE' if saldo_final > 0 else 'HABER'
            })
    
    context = {
        'periodo_activo': periodo_activo,
        'periodo_seleccionado': periodo_seleccionado,
        'periodos': periodos,
        'cuentas': cuentas,
        'transacciones': transacciones,
        'resumen_cuentas': resumen_cuentas,
        'puede_crear_periodo': not PeriodoContable.objects.filter(estado__in=['ACTIVO', 'CERRADO']).exists(),
    }
    
    return render(request, 'ContaGeneral/libroMayor.html', context)

def crear_periodo_contable(request):
    if request.method == 'POST':
        año = request.POST.get('año')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        
        # Verificar que no hay periodo activo
        if PeriodoContable.objects.filter(estado='ACTIVO').exists():
            messages.error(request, 'Ya existe un periodo contable activo. Debe cerrarlo antes de crear uno nuevo.')
            return redirect('libro_mayor')
        
        # Verificar que el año no existe
        if PeriodoContable.objects.filter(año=año).exists():
            messages.error(request, f'Ya existe un periodo contable para el año {año}.')
            return redirect('libro_mayor')
        
        try:
            periodo = PeriodoContable.objects.create(
                año=año,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                estado='ACTIVO'
            )
            messages.success(request, f'Periodo contable {año} creado exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al crear el periodo: {str(e)}')
        
        return redirect('libro_mayor')
    
    return redirect('libro_mayor')

def crear_transaccion(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            fecha = data.get('fecha')
            descripcion = data.get('descripcion')
            cuentas_afectadas = data.get('cuentas_afectadas', [])
            
            # Verificar que hay un periodo activo
            periodo_activo = PeriodoContable.objects.filter(estado='ACTIVO').first()
            if not periodo_activo:
                return JsonResponse({
                    'success': False,
                    'message': 'No hay un periodo contable activo.'
                })
            
            # Verificar que la fecha está dentro del periodo
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
            if not (periodo_activo.fecha_inicio <= fecha_obj <= periodo_activo.fecha_fin):
                return JsonResponse({
                    'success': False,
                    'message': f'La fecha debe estar entre {periodo_activo.fecha_inicio} y {periodo_activo.fecha_fin}'
                })
            
            # Verificar que la transacción esté balanceada (usando Decimal)
            total_debe = sum(Decimal(str(item['monto'])) for item in cuentas_afectadas if item['tipo'] == 'debe')
            total_haber = sum(Decimal(str(item['monto'])) for item in cuentas_afectadas if item['tipo'] == 'haber')
            
            if abs(total_debe - total_haber) > Decimal('0.01'):
                return JsonResponse({
                    'success': False,
                    'message': f'La transacción no está balanceada. Debe (${total_debe:.2f}) ≠ Haber (${total_haber:.2f})'
                })
            
            # Obtener el próximo número de transacción
            ultima_transaccion = Transaccion.objects.filter(
                periodo=periodo_activo
            ).order_by('-numero_transaccion').first()
            numero_transaccion = (ultima_transaccion.numero_transaccion + 1) if ultima_transaccion else 1
            
            # Obtener el primer usuario de la base de datos (que ya existe)
            usuario_por_defecto = Usuario.objects.first()
            
            # Crear las transacciones en una sola operación atómica
            with transaction.atomic():
                for cuenta_data in cuentas_afectadas:
                    cuenta_id = cuenta_data.get('cuenta_id')
                    tipo = cuenta_data.get('tipo')
                    monto = Decimal(str(cuenta_data.get('monto', 0)))  # Convertir a Decimal
                    
                    cuenta = get_object_or_404(Cuenta, id=cuenta_id)
                    
                    Transaccion.objects.create(
                        fecha=fecha_obj,
                        cuenta=cuenta,
                        debe=monto if tipo == 'debe' else Decimal('0'),
                        haber=monto if tipo == 'haber' else Decimal('0'),
                        descripcion=descripcion,
                        usuario=usuario_por_defecto,
                        periodo=periodo_activo,
                        numero_transaccion=numero_transaccion
                    )
                    
                    # Actualizar saldo de la cuenta (ambos son Decimal ahora)
                    if tipo == 'debe':
                        cuenta.saldo += monto
                    else:
                        cuenta.saldo -= monto
                    cuenta.save()
            
            return JsonResponse({
                'success': True,
                
                'numero_transaccion': numero_transaccion
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al crear la transacción: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

def detalle_transaccion(request, numero_transaccion):
    periodo_id = request.GET.get('periodo_id')
    periodo = get_object_or_404(PeriodoContable, id=periodo_id) if periodo_id else None
    
    if not periodo:
        periodo = PeriodoContable.objects.filter(estado='ACTIVO').first()
    
    transacciones = Transaccion.objects.filter(
        periodo=periodo,
        numero_transaccion=numero_transaccion
    ).select_related('cuenta', 'centro_costo')
    
    if not transacciones.exists():
        return JsonResponse({'success': False, 'message': 'Transacción no encontrada'})
    
    primera_transaccion = transacciones.first()
    datos_transaccion = {
        'numero': numero_transaccion,
        'fecha': primera_transaccion.fecha.strftime('%d/%m/%Y'),
        'descripcion': primera_transaccion.descripcion,
        'cuentas': []
    }
    
    for trans in transacciones:
        datos_transaccion['cuentas'].append({
            'cuenta': f"{trans.cuenta.codigo} - {trans.cuenta.nombre}",
            'tipo': 'DEBE' if trans.debe > 0 else 'HABER',
            'monto': trans.debe if trans.debe > 0 else trans.haber
        })
    
    return JsonResponse({'success': True, 'transaccion': datos_transaccion})
