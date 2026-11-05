from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
# Asumo que tus modelos están en esta ruta
from ChivoBits_app.models.contaGeneral import *
# Asumo que tus modelos están en esta ruta
from ChivoBits_app.models.estadosFinancieros import *
from django.db import transaction
from django.db.models import Sum, Q, Case, When, Value, DecimalField
from decimal import Decimal


def financiero(request):
    return render(request, 'EstadosFinancieros/estadoFinanciero.html')

# --- SIN CAMBIOS EN ESTA VISTA ---
def ajustes_contables(request):
    # Obtener periodo CERRADO por defecto (para hacer ajustes)
    periodo_cerrado = PeriodoContable.objects.filter(estado='CERRADO').first()

    # Obtener el período seleccionado
    periodo_id = request.GET.get('periodo_id')
    if periodo_id:
        periodo_seleccionado = get_object_or_404(PeriodoContable, id=periodo_id)
    else:
        periodo_seleccionado = periodo_cerrado

    # Manejar el caso cuando no hay periodo seleccionado
    if periodo_seleccionado:
        # Obtener todos los ajustes del periodo seleccionado
        ajustes = Transaccion.objects.filter(
            periodo=periodo_seleccionado,
            es_ajuste=True
        ).select_related('cuenta').order_by('fecha', 'id')

        # Calcular totales - esto funciona porque ajustes es un QuerySet
        total_debe = ajustes.aggregate(total=Sum('debe'))['total'] or 0
        total_haber = ajustes.aggregate(total=Sum('haber'))['total'] or 0
    else:
        # Cuando no hay periodo seleccionado, usar valores por defecto
        ajustes = []
        total_debe = 0
        total_haber = 0

    # Obtener todos los periodos para el selector
    periodos = PeriodoContable.objects.all().order_by('-año')

    context = {
        'periodo_cerrado': periodo_cerrado,
        'periodo_seleccionado': periodo_seleccionado,
        'ajustes': ajustes,
        'total_debe': total_debe,
        'total_haber': total_haber,
        'periodos': periodos,
        'cuentas': Cuenta.objects.filter(activa=True, nivel__in=[3, 4]).order_by('codigo'),
        'puede_ajustar': periodo_seleccionado and periodo_seleccionado.estado == 'CERRADO',
        'puede_generar_estados': periodo_seleccionado and periodo_seleccionado.estado == 'CERRADO',
    }
    return render(request, 'EstadosFinancieros/ajustesContables.html', context)

# --- SIN CAMBIOS EN ESTA VISTA ---
# (Nota: La lógica de cuenta.saldo += / -= monto es simplista y fallará
# si no se tiene en cuenta la naturaleza (deudora/acreedora) de la cuenta,
# pero no afecta a la LECTURA de los reportes, que es el problema actual)
def crear_ajuste(request):
    if request.method == 'POST':
        try:
            import json
            from decimal import Decimal

            # Parsear JSON si viene como JSON
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                fecha = data.get('fecha')
                descripcion = data.get('descripcion')
                cuentas_afectadas = data.get('cuentas_afectadas', [])
            else:
                # Mantener compatibilidad con FormData
                fecha = request.POST.get('fecha')
                descripcion = request.POST.get('descripcion')
                cuentas_afectadas = []  # No disponible en FormData tradicional

            print("=== INICIANDO CREAR AJUSTE ===")
            print(f"Usuario: {request.user}")
            print(f"Fecha: {fecha}, Descripción: {descripcion}")
            print(f"Cuentas afectadas: {cuentas_afectadas}")

            periodo_activo = PeriodoContable.objects.filter(
                estado='CERRADO').first()
            if not periodo_activo:
                print("ERROR: No hay período cerrado")
                return JsonResponse({
                    'success': False,
                    'message': 'No hay un período contable cerrado.'
                })

            # --- CORRECCIÓN LÓGICA: Debería ser 'ACTIVO', no 'CERRADO' ---
            if periodo_activo.estado == 'ACTIVO':
                print("ERROR: Período cerrado")
                return JsonResponse({
                    'success': False,
                    'message': 'No se pueden hacer ajustes en períodos activos.'
                })
            # --- FIN CORRECIÓN ---
            # (Lo dejo como estaba para no alterar tu flujo, pero la validación es extraña)

            if not fecha or not descripcion:
                print("ERROR: Campos obligatorios faltantes")
                return JsonResponse({
                    'success': False,
                    'message': 'Fecha y descripción son obligatorios.'
                })

            if not cuentas_afectadas or len(cuentas_afectadas) < 2:
                print("ERROR: Se requieren al menos 2 cuentas")
                return JsonResponse({
                    'success': False,
                    'message': 'Se requieren al menos 2 cuentas para un ajuste contable.'
                })

            # Verificar que el ajuste esté balanceado
            total_debe = sum(Decimal(
                str(cuenta['monto'])) for cuenta in cuentas_afectadas if cuenta['tipo'] == 'debe')
            total_haber = sum(Decimal(str(
                cuenta['monto'])) for cuenta in cuentas_afectadas if cuenta['tipo'] == 'haber')

            if total_debe != total_haber:
                print("ERROR: Ajuste desbalanceado")
                return JsonResponse({
                    'success': False,
                    'message': f'El ajuste no está balanceado. DEBE: {total_debe}, HABER: {total_haber}'
                })

            # Crear el ajuste con todas las cuentas
            with transaction.atomic():
                for cuenta_data in cuentas_afectadas:
                    cuenta = get_object_or_404(
                        Cuenta, id=cuenta_data['cuenta_id'])
                    monto = Decimal(str(cuenta_data['monto']))
                    tipo = cuenta_data['tipo']

                    print(
                        f"Creando movimiento - Cuenta: {cuenta.codigo}, Tipo: {tipo}, Monto: {monto}")

                    # Crear transacción para cada cuenta
                    transaccion = Transaccion.objects.create(
                        fecha=fecha,
                        cuenta=cuenta,
                        descripcion=descripcion,
                        debe=monto if tipo == 'debe' else Decimal('0'),
                        haber=monto if tipo == 'haber' else Decimal('0'),
                        es_ajuste=True,
                        periodo=periodo_activo,
                        usuario=request.user if request.user.is_authenticated else None
                    )

                    # Actualizar saldo de la cuenta
                    if tipo == 'debe':
                        cuenta.saldo += monto
                    else:
                        cuenta.saldo -= monto
                    cuenta.save()

                    print(
                        f"Saldo actualizado - {cuenta.codigo}: {cuenta.saldo}")

            print("=== AJUSTE CREADO EXITOSAMENTE ===")
            return JsonResponse({'success': True})

        except Exception as e:
            print(f"ERROR EXCEPCIÓN: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'message': f'Error al crear el ajuste: {str(e)}'
            })

    print("Método no permitido")
    return JsonResponse({'success': False, 'message': 'Método no permitido.'})

# --- SIN CAMBIOS EN ESTA VISTA ---
def cerrar_periodo(request):
    if request.method == 'POST':
        try:
            periodo_activo = PeriodoContable.objects.filter(
                estado='ACTIVO').first()
            if not periodo_activo:
                messages.error(request, 'No hay un período contable activo.')
                return redirect('libro_mayor')  # Redirigir al libro mayor

            # Verificar que el periodo esté balanceado
            if not periodo_activo.puede_cerrar:
                messages.error(request,
                              'No se puede cerrar el período. Las transacciones no están balanceadas (DEBE ≠ HABER).')
                return redirect('libro_mayor')

            # Cerrar el periodo (ACTIVO → CERRADO)
            periodo_activo.estado = 'CERRADO'
            periodo_activo.save()

            messages.success(
                request, f'Período {periodo_activo.año} cerrado exitosamente. Ahora puede realizar ajustes contables.')
            return redirect('ajustes_contables')  # Redirigir a ajustes

        except Exception as e:
            messages.error(request, f'Error al cerrar el período: {str(e)}')
            return redirect('libro_mayor')

    return redirect('libro_mayor')

# --- MODIFICADO PARA USAR LA LÓGICA CORRECTA DE CÁLCULO ---
def generar_estados_financieros(request):
    if request.method == 'POST':
        try:
            periodo_id = request.POST.get('periodo_id')
            periodo = get_object_or_404(PeriodoContable, id=periodo_id)

            # Verificar que el período esté CERRADO (no ACTIVO)
            if periodo.estado != 'CERRADO':
                messages.error(
                    request, 'Solo se pueden generar estados financieros para períodos CERRADOS.')
                return redirect('ajustes_contables')

            # --- INICIO DE MODIFICACIÓN: Usar cálculos corregidos ---
            # Calcular totales para estados financieros (usando toda la data, incl. ajustes)
            ventas_totales = calcular_ventas_totales(periodo, incluir_ajustes=True)
            gastos_totales = calcular_gastos_totales(periodo, incluir_ajustes=True)
            utilidad_neta = ventas_totales - gastos_totales
            # --- FIN DE MODIFICACIÓN ---

            # Finalizar el periodo (CERRADO → FINALIZADO)
            periodo.estado = 'FINALIZADO'
            periodo.save()

            # Crear registros en todos los estados financieros
            balance_comprobacion = BalanceComprobacion.objects.create(
                año=periodo.año,
                usuario=request.user if request.user.is_authenticated else None
            )

            estado_resultados = EstadoResultados.objects.create(
                año=periodo.año,
                usuario=request.user if request.user.is_authenticated else None,
                ingresos_totales=ventas_totales,
                gastos_totales=gastos_totales,
                utilidad_neta=utilidad_neta
            )

            messages.success(
                request, f'Estados financieros generados exitosamente para el período {periodo.año}')
            return redirect('balance_comprobacion')

        except Exception as e:
            messages.error(
                request, f'Error al generar estados financieros: {str(e)}')
            return redirect('ajustes_contables')

    return redirect('ajustes_contables')

# --- SIN CAMBIOS EN ESTA VISTA, LA LÓGICA ERA CORRECTA ---
def balance_comprobacion(request):
    # Obtener el período seleccionado
    periodo_id = request.POST.get(
        'periodo_id') or request.GET.get('periodo_id')

    if periodo_id:
        try:
            periodo_actual = PeriodoContable.objects.get(id=periodo_id)
        except PeriodoContable.DoesNotExist:
            # Si no existe, usar el último período FINALIZADO
            periodo_actual = PeriodoContable.objects.filter(
                estado='FINALIZADO').first()
            messages.warning(
                request, "El período seleccionado no existe. Se mostró el último período finalizado.")
    else:
        # Por defecto mostrar el último período FINALIZADO
        periodo_actual = PeriodoContable.objects.filter(
            estado='FINALIZADO').first()

    # Si no hay período finalizado, mostrar cerrado como fallback
    if not periodo_actual:
        periodo_actual = PeriodoContable.objects.filter(
            estado='CERRADO').first()
        if periodo_actual:
            messages.info(
                request, "No hay períodos finalizados. Mostrando período cerrado.")

    # Obtener TODAS las cuentas activas (no solo nivel 3)
    todas_cuentas = Cuenta.objects.filter(activa=True).order_by('codigo')

    # Preparar datos para la tabla
    datos_cuentas = []
    totales = {
        'balance_debe': Decimal('0'),
        'balance_haber': Decimal('0'),
        'ajuste_debe': Decimal('0'),
        'ajuste_haber': Decimal('0'),
        'balance_ajustado_debe': Decimal('0'),
        'balance_ajustado_haber': Decimal('0')
    }

    for cuenta in todas_cuentas:
        if periodo_actual:
            # Obtener transacciones regulares (no ajustes)
            transacciones_regulares = Transaccion.objects.filter(
                cuenta=cuenta,
                periodo=periodo_actual,
                es_ajuste=False
            )

            # Obtener transacciones de ajuste
            transacciones_ajuste = Transaccion.objects.filter(
                cuenta=cuenta,
                periodo=periodo_actual,
                es_ajuste=True
            )

            # Calcular saldos regulares - CORRECCIÓN: CALCULAR SALDO NETO
            total_debe_regulares = transacciones_regulares.aggregate(
                total=Sum('debe')
            )['total'] or Decimal('0')

            total_haber_regulares = transacciones_regulares.aggregate(
                total=Sum('haber')
            )['total'] or Decimal('0')

            # CALCULAR SALDO NETO PARA BALANCE DE COMPROBACIÓN
            saldo_neto = total_debe_regulares - total_haber_regulares

            if saldo_neto > 0:
                balance_debe = saldo_neto
                balance_haber = Decimal('0')
            elif saldo_neto < 0:
                balance_debe = Decimal('0')
                balance_haber = abs(saldo_neto)
            else:
                balance_debe = Decimal('0')
                balance_haber = Decimal('0')

            # Calcular ajustes
            ajuste_debe = transacciones_ajuste.aggregate(
                total=Sum('debe')
            )['total'] or Decimal('0')

            ajuste_haber = transacciones_ajuste.aggregate(
                total=Sum('haber')
            )['total'] or Decimal('0')

            # APLICAR FÓRMULA EXACTA PARA BALANCE AJUSTADO
            if balance_debe > 0:  # La cuenta tiene saldo DEUDOR
                saldo_deudor = balance_debe
                # FÓRMULA: Saldo Deudor + Ajuste DEBE - Ajuste HABER
                resultado = saldo_deudor + ajuste_debe - ajuste_haber
                if resultado > 0:
                    balance_ajustado_debe = resultado
                    balance_ajustado_haber = Decimal('0')
                else:  # Si el resultado es negativo o cero
                    balance_ajustado_debe = Decimal('0')
                    balance_ajustado_haber = abs(
                        resultado) if resultado < 0 else Decimal('0')

            elif balance_haber > 0:  # La cuenta tiene saldo ACREEDOR
                saldo_acreedor = balance_haber
                # FÓRMULA: Saldo Acreedor + Ajuste HABER - Ajuste DEBE
                resultado = saldo_acreedor + ajuste_haber - ajuste_debe
                if resultado > 0:
                    balance_ajustado_debe = Decimal('0')
                    balance_ajustado_haber = resultado
                else:  # Si el resultado es negativo o cero
                    balance_ajustado_debe = abs(
                        resultado) if resultado < 0 else Decimal('0')
                    balance_ajustado_haber = Decimal('0')

            else:  # Saldo cero
                # Si no hay saldo inicial, los ajustes determinan la posición
                neto_ajustes = ajuste_debe - ajuste_haber
                if neto_ajustes > 0:
                    balance_ajustado_debe = neto_ajustes
                    balance_ajustado_haber = Decimal('0')
                elif neto_ajustes < 0:
                    balance_ajustado_debe = Decimal('0')
                    balance_ajustado_haber = abs(neto_ajustes)
                else:
                    balance_ajustado_debe = Decimal('0')
                    balance_ajustado_haber = Decimal('0')

        else:
            # Sin período seleccionado, mostrar ceros
            balance_debe = Decimal('0')
            balance_haber = Decimal('0')
            ajuste_debe = Decimal('0')
            ajuste_haber = Decimal('0')
            balance_ajustado_debe = Decimal('0')
            balance_ajustado_haber = Decimal('0')

        # Solo mostrar cuentas que tengan movimientos
        if balance_debe > 0 or balance_haber > 0 or ajuste_debe > 0 or ajuste_haber > 0 or balance_ajustado_debe > 0 or balance_ajustado_haber > 0:
            datos_cuenta = {
                'id': cuenta.id,
                'codigo': cuenta.codigo,
                'nombre': cuenta.nombre,
                'tipo': cuenta.tipo,
                'balance_debe': balance_debe,
                'balance_haber': balance_haber,
                'ajuste_debe': ajuste_debe,
                'ajuste_haber': ajuste_haber,
                'balance_ajustado_debe': balance_ajustado_debe,
                'balance_ajustado_haber': balance_ajustado_haber,
            }

            # Sumar a totales
            totales['balance_debe'] += balance_debe
            totales['balance_haber'] += balance_haber
            totales['ajuste_debe'] += ajuste_debe
            totales['ajuste_haber'] += ajuste_haber
            totales['balance_ajustado_debe'] += balance_ajustado_debe
            totales['balance_ajustado_haber'] += balance_ajustado_haber

            datos_cuentas.append(datos_cuenta)

    # Obtener todos los períodos disponibles
    periodos = PeriodoContable.objects.all().order_by('-año')

    context = {
        'cuentas': datos_cuentas,
        'totales': totales,
        'periodos': periodos,
        'periodo_actual': periodo_actual,
        'fecha_balance': periodo_actual.fecha_fin.strftime("%d de %B de %Y") if periodo_actual else None,
        # ENVIAR EL ESTADO DEL PERIODO AL TEMPLATE
        'estado_periodo': periodo_actual.estado if periodo_actual else None,
    }

    return render(request, 'EstadosFinancieros/balanceComprobacion.html', context)


# --- MODIFICADO PARA CALCULAR SALDO NETO ---
def calcular_ventas_totales(periodo, incluir_ajustes=False):
    """
    Calcula las ventas totales (ingresos por servicios de software)
    Calcula el saldo neto (Haber - Debe)
    """
    from django.db.models import Sum
    from decimal import Decimal

    cuentas_ventas = Cuenta.objects.filter(
        Q(codigo__startswith='5') | Q(tipo='INGRESO')
    )

    # --- INICIO DE MODIFICACIÓN ---
    query = Transaccion.objects.filter(
        periodo=periodo,
        cuenta__in=cuentas_ventas
    )
    
    if not incluir_ajustes:
        query = query.filter(es_ajuste=False)

    ventas_agg = query.aggregate(
        total_debe=Sum('debe'),
        total_haber=Sum('haber')
    )
    
    total_debe = ventas_agg['total_debe'] or Decimal('0')
    total_haber = ventas_agg['total_haber'] or Decimal('0')

    return total_haber - total_debe
    # --- FIN DE MODIFICACIÓN ---


# --- MODIFICADO PARA CALCULAR SALDO NETO ---
def calcular_gastos_totales(periodo, incluir_ajustes=False):
    """
    Calcula los gastos totales (grupos 41, 42 y 43)
    Calcula el saldo neto (Debe - Haber)
    """
    from django.db.models import Sum
    from decimal import Decimal

    cuentas_gastos = Cuenta.objects.filter(
        Q(codigo__startswith='4') | Q(tipo='GASTO')
    )

    # --- INICIO DE MODIFICACIÓN ---
    query = Transaccion.objects.filter(
        periodo=periodo,
        cuenta__in=cuentas_gastos
    )
    
    if not incluir_ajustes:
        query = query.filter(es_ajuste=False)
        
    gastos_agg = query.aggregate(
        total_debe=Sum('debe'),
        total_haber=Sum('haber')
    )
    
    total_debe = gastos_agg['total_debe'] or Decimal('0')
    total_haber = gastos_agg['total_haber'] or Decimal('0')

    return total_debe - total_haber
    # --- FIN DE MODIFICACIÓN ---


# --- MODIFICADO PARA CALCULAR SALDOS NETOS (CORRIGE ERROR 4311) ---
def estado_resultados(request):
    # Obtener el período seleccionado
    periodo_id = request.POST.get(
        'periodo_id') or request.GET.get('periodo_id')

    if periodo_id:
        try:
            periodo_actual = PeriodoContable.objects.get(id=periodo_id)
        except PeriodoContable.DoesNotExist:
            periodo_actual = PeriodoContable.objects.filter(
                estado='FINALIZADO').first()
            messages.warning(request, "El período seleccionado no existe.")
    else:
        periodo_actual = PeriodoContable.objects.filter(
            estado='FINALIZADO').first()

    # Inicializar datos
    ingresos = []
    gastos = []
    total_ingresos = Decimal('0')
    total_gastos = Decimal('0')
    utilidad_bruta = Decimal('0')
    fecha_inicio = ""
    fecha_fin = ""

    if periodo_actual:
        # Obtener fechas del período
        fecha_inicio = periodo_actual.fecha_inicio
        fecha_fin = periodo_actual.fecha_fin

        # Buscar cuentas de INGRESO (grupo 5)
        cuentas_ingresos = Cuenta.objects.filter(
            Q(codigo__startswith='5') | Q(tipo='INGRESO')
        )

        # Buscar cuentas de GASTO (grupo 4)
        cuentas_gastos = Cuenta.objects.filter(
            Q(codigo__startswith='4') | Q(tipo='GASTO')
        )

        # --- INICIO DE MODIFICACIÓN: Calcular ingresos netos ---
        for cuenta in cuentas_ingresos:
            transacciones = Transaccion.objects.filter(
                cuenta=cuenta,
                periodo=periodo_actual
            ).aggregate(
                total_debe=Sum('debe'),
                total_haber=Sum('haber')
            )

            saldo_haber = transacciones['total_haber'] or Decimal('0')
            saldo_debe = transacciones['total_debe'] or Decimal('0')
            
            # Saldo neto de ingreso (Haber - Debe)
            monto_neto = saldo_haber - saldo_debe

            if monto_neto != 0: # Mostrar si hay saldo (positivo o negativo)
                ingresos.append({
                    'codigo': cuenta.codigo,
                    'nombre': cuenta.nombre,
                    'monto': monto_neto
                })
                total_ingresos += monto_neto
        # --- FIN DE MODIFICACIÓN ---

        # --- INICIO DE MODIFICACIÓN: Calcular gastos netos ---
        for cuenta in cuentas_gastos:
            transacciones = Transaccion.objects.filter(
                cuenta=cuenta,
                periodo=periodo_actual
            ).aggregate(
                total_debe=Sum('debe'),
                total_haber=Sum('haber')
            )

            saldo_debe = transacciones['total_debe'] or Decimal('0')
            saldo_haber = transacciones['total_haber'] or Decimal('0')

            # Saldo neto de gasto (Debe - Haber)
            # Esto maneja el caso de 4311 - Otros Gastos (saldo acreedor)
            monto_neto = saldo_debe - saldo_haber

            if monto_neto != 0: # Mostrar si hay saldo (positivo o negativo)
                gastos.append({
                    'codigo': cuenta.codigo,
                    'nombre': cuenta.nombre,
                    'monto': monto_neto
                })
                total_gastos += monto_neto
        # --- FIN DE MODIFICACIÓN ---

        # Calcular utilidad bruta
        utilidad_bruta = total_ingresos - total_gastos

    # Obtener todos los períodos disponibles
    periodos = PeriodoContable.objects.all().order_by('-año')

    context = {
        'ingresos': ingresos,
        'gastos': gastos,
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'utilidad_bruta': utilidad_bruta,
        'periodo_actual': periodo_actual,
        'periodos': periodos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }

    return render(request, 'EstadosFinancieros/estadoResultados.html', context)


# --- MODIFICADO PARA CALCULAR SALDOS NETOS (CORRIGE ERROR 4311) ---
def estado_capital(request):
    # Obtener el período seleccionado (igual que en estado_resultados)
    periodo_id = request.POST.get(
        'periodo_id') or request.GET.get('periodo_id')

    if periodo_id:
        try:
            periodo_actual = PeriodoContable.objects.get(id=periodo_id)
        except PeriodoContable.DoesNotExist:
            periodo_actual = PeriodoContable.objects.filter(
                estado='FINALIZADO').first()
            messages.warning(request, "El período seleccionado no existe.")
    else:
        periodo_actual = PeriodoContable.objects.filter(
            estado='FINALIZADO').first()

    # Inicializar datos
    capital_inicial = Decimal('0')
    resultado_ejercicio = Decimal('0')
    reservas_actuales = Decimal('0') # Esto es 'Reservas Iniciales'
    hay_perdida = False
    año = ""

    if periodo_actual:
        # Obtener año del período
        año = periodo_actual.año

        # 1. OBTENER CAPITAL SOCIAL INICIAL (cuenta 3101)
        try:
            cuenta_capital = Cuenta.objects.get(codigo='3101')
            transacciones_capital = Transaccion.objects.filter(
                cuenta=cuenta_capital,
                periodo=periodo_actual
            ).aggregate(
                total_debe=Sum('debe'),
                total_haber=Sum('haber')
            )
            saldo_haber = transacciones_capital['total_haber'] or Decimal('0')
            saldo_debe = transacciones_capital['total_debe'] or Decimal('0')
            capital_inicial = saldo_haber - saldo_debe

        except Cuenta.DoesNotExist:
            capital_inicial = Decimal('0')

        # 2. OBTENER RESERVAS ACTUALES (INICIALES) (cuenta 3102)
        try:
            cuenta_reservas = Cuenta.objects.get(codigo='3102')
            transacciones_reservas = Transaccion.objects.filter(
                cuenta=cuenta_reservas,
                periodo=periodo_actual
            ).aggregate(
                total_debe=Sum('debe'),
                total_haber=Sum('haber')
            )
            saldo_haber = transacciones_reservas['total_haber'] or Decimal('0')
            saldo_debe = transacciones_reservas['total_debe'] or Decimal('0')
            reservas_actuales = saldo_haber - saldo_debe

        except Cuenta.DoesNotExist:
            reservas_actuales = Decimal('0')

        # 3. OBTENER RESULTADO DEL EJERCICIO (utilidad o pérdida)
        # --- INICIO DE MODIFICACIÓN: Usar funciones corregidas ---
        # Usamos las funciones helper que ya corregimos (incluye ajustes)
        total_ingresos = calcular_ventas_totales(periodo_actual, incluir_ajustes=True)
        total_gastos = calcular_gastos_totales(periodo_actual, incluir_ajustes=True)
        # --- FIN DE MODIFICACIÓN ---

        # Calcular resultado del ejercicio (puede ser positivo o negativo)
        resultado_ejercicio = total_ingresos - total_gastos

        # Determinar si hay pérdida
        hay_perdida = resultado_ejercicio < 0

    else:
        # Si no hay período, mostrar ceros
        año = "N/A"
        capital_inicial = Decimal('0')
        resultado_ejercicio = Decimal('0')
        reservas_actuales = Decimal('0')
        hay_perdida = False

    # CÁLCULOS DEL ESTADO DE CAPITAL
    if hay_perdida:
        # En caso de PÉRDIDA
        perdida_total = abs(resultado_ejercicio)
        capital_final = capital_inicial - perdida_total  # Se resta la pérdida del capital

        # No hay distribución de utilidades cuando hay pérdida
        reinversion = Decimal('0')
        reservas_utilidad = Decimal('0') # Reservas *del período*
        reservas_totales = reservas_actuales  # Las reservas *totales* se mantienen igual

    else:
        # En caso de UTILIDAD
        reinversion = resultado_ejercicio * Decimal('0.60')  # 60% para reinversión
        reservas_utilidad = resultado_ejercicio * Decimal('0.40')  # 40% para reservas *del período*
        
        capital_final = capital_inicial + reinversion
        # --- CORRECCIÓN CLAVE: Sumar las reservas nuevas a las actuales ---
        reservas_totales = reservas_actuales + reservas_utilidad

    # Calcular incremento (puede ser negativo en caso de pérdida)
    incremento_capital = capital_final - capital_inicial
    porcentaje_incremento = (
        incremento_capital / capital_inicial * 100) if capital_inicial > 0 else 0

    # Obtener todos los períodos disponibles
    periodos = PeriodoContable.objects.all().order_by('-año')

    context = {
        'año': año,
        'capital_inicial': capital_inicial,
        'resultado_ejercicio': resultado_ejercicio,
        'reinversion': reinversion,
        'reservas_utilidad': reservas_utilidad, # 40% del período
        'reservas_actuales': reservas_actuales, # Saldo inicial
        'reservas_totales': reservas_totales,   # Saldo final (inicial + 40%)
        'capital_final': capital_final,
        'incremento_capital': incremento_capital,
        'porcentaje_incremento': porcentaje_incremento,
        'periodo_actual': periodo_actual,
        'periodos': periodos,
        'hay_perdida': hay_perdida,
        'perdida_total': abs(resultado_ejercicio) if hay_perdida else Decimal('0'),
    }

    return render(request, 'EstadosFinancieros/estadoCapital.html', context)


# --- VISTA COMPLETAMENTE MODIFICADA ---
def balance_general(request):
    # Obtener el período seleccionado
    periodo_id = request.POST.get('periodo_id') or request.GET.get('periodo_id')

    if periodo_id:
        try:
            periodo_actual = PeriodoContable.objects.get(id=periodo_id)
        except PeriodoContable.DoesNotExist:
            periodo_actual = PeriodoContable.objects.filter(estado='FINALIZADO').first()
            messages.warning(request, "El período seleccionado no existe.")
    else:
        periodo_actual = PeriodoContable.objects.filter(estado='FINALIZADO').first()

    # Inicializar datos
    activos = []
    pasivos = []
    patrimonio = []
    total_debe = Decimal('0')
    total_haber = Decimal('0')
    
    # NUEVO: Totales por sección (DEBE y HABER separados)
    total_debe_activos = Decimal('0')
    total_haber_activos = Decimal('0')
    
    total_debe_pasivos = Decimal('0')
    total_haber_pasivos = Decimal('0')
    
    total_debe_patrimonio = Decimal('0')
    total_haber_patrimonio = Decimal('0')
    
    fecha_inicio = ""
    fecha_fin = ""

    if periodo_actual:
        # Obtener fechas del período
        fecha_inicio = periodo_actual.fecha_inicio
        fecha_fin = periodo_actual.fecha_fin

        # Obtener cuentas de ACTIVO (grupo 1)
        cuentas_activo = Cuenta.objects.filter(
            Q(codigo__startswith='1') | Q(tipo='ACTIVO'),
            activa=True
        )

        # Obtener cuentas de PASIVO (grupo 2)
        cuentas_pasivos = Cuenta.objects.filter(
            Q(codigo__startswith='2') | Q(tipo='PASIVO'),
            activa=True
        )

        # === Calcular ACTIVOS (MODIFICADO para sumar DEBE y HABER por separado) ===
        for cuenta in cuentas_activo:
            transacciones = Transaccion.objects.filter(
                cuenta=cuenta,
                periodo=periodo_actual
            )

            if transacciones.exists():
                total_debe_trans = transacciones.aggregate(total=Sum('debe'))['total'] or Decimal('0')
                total_haber_trans = transacciones.aggregate(total=Sum('haber'))['total'] or Decimal('0')

                saldo_final = total_debe_trans - total_haber_trans

                # Identificar tipos de cuentas
                es_contra_activo = cuenta.codigo.startswith('1202') or cuenta.codigo.startswith('1204')
                es_cuenta_bancaria = cuenta.codigo.startswith('1101')
                
                if es_contra_activo:
                    # Contra-activos (depreciación, amortización) - saldo en HABER
                    if saldo_final < 0:  # Saldo acreedor (normal para contra-activos)
                        saldo_absoluto = abs(saldo_final)
                        columna_debe = Decimal('0')
                        columna_haber = saldo_absoluto
                        total_haber += saldo_absoluto
                        total_haber_activos += saldo_absoluto  # SUMA AL HABER DE ACTIVOS
                        
                        if saldo_absoluto > 0:
                            activos.append({
                                'codigo': cuenta.codigo,
                                'nombre': cuenta.nombre,
                                'saldo': saldo_absoluto,
                                'es_deudor': False,
                                'debe': columna_debe,
                                'haber': columna_haber,
                                'es_contra_activo': True
                            })
                
                elif es_cuenta_bancaria and saldo_final < 0:
                    # Cuentas bancarias con sobregiro
                    saldo_absoluto = abs(saldo_final)
                    columna_debe = Decimal('0')
                    columna_haber = saldo_absoluto
                    total_haber += saldo_absoluto
                    total_haber_activos += saldo_absoluto  # SUMA AL HABER DE ACTIVOS
                    
                    activos.append({
                        'codigo': cuenta.codigo,
                        'nombre': f"{cuenta.nombre} (Sobregiro)",
                        'saldo': saldo_absoluto,
                        'es_deudor': False,
                        'debe': columna_debe,
                        'haber': columna_haber,
                        'es_sobregiro': True
                    })
                
                else:
                    # Activos normales - saldo en DEBE
                    if saldo_final > 0:
                        columna_debe = saldo_final
                        columna_haber = Decimal('0')
                        total_debe += saldo_final
                        total_debe_activos += saldo_final  # SUMA AL DEBE DE ACTIVOS
                        
                        activos.append({
                            'codigo': cuenta.codigo,
                            'nombre': cuenta.nombre,
                            'saldo': saldo_final,
                            'es_deudor': True,
                            'debe': columna_debe,
                            'haber': columna_haber
                        })

        # === Calcular PASIVOS (MODIFICADO para sumar DEBE y HABER por separado) ===
        for cuenta in cuentas_pasivos:
            transacciones = Transaccion.objects.filter(
                cuenta=cuenta,
                periodo=periodo_actual
            )
            
            if transacciones.exists():
                total_debe_trans = transacciones.aggregate(total=Sum('debe'))['total'] or Decimal('0')
                total_haber_trans = transacciones.aggregate(total=Sum('haber'))['total'] or Decimal('0')

                # Para pasivos, el saldo normal es acreedor
                if total_haber_trans > total_debe_trans:
                    saldo_final = total_haber_trans - total_debe_trans
                    columna_debe = Decimal('0')
                    columna_haber = saldo_final
                    total_haber += saldo_final
                    total_haber_pasivos += saldo_final  # SUMA AL HABER DE PASIVOS
                    es_acreedor = True
                    
                    if saldo_final > 0:
                        pasivos.append({
                            'codigo': cuenta.codigo,
                            'nombre': cuenta.nombre,
                            'saldo': saldo_final,
                            'es_acreedor': es_acreedor,
                            'debe': columna_debe,
                            'haber': columna_haber
                        })
                else:
                    # Saldo deudor en pasivos (anormal)
                    saldo_final = total_debe_trans - total_haber_trans
                    columna_debe = saldo_final
                    columna_haber = Decimal('0')
                    total_debe += saldo_final
                    total_debe_pasivos += saldo_final  # SUMA AL DEBE DE PASIVOS
                    es_acreedor = False

                    if saldo_final > 0:
                        pasivos.append({
                            'codigo': cuenta.codigo,
                            'nombre': cuenta.nombre,
                            'saldo': saldo_final,
                            'es_acreedor': es_acreedor,
                            'debe': columna_debe,
                            'haber': columna_haber
                        })

        # === CALCULAR PATRIMONIO (MODIFICADO para sumar DEBE y HABER por separado) ===
        # 1. Obtener Capital Social inicial (3101)
        capital_inicial = Decimal('0')
        try:
            cuenta_capital = Cuenta.objects.get(codigo='3101')
            trans_capital_agg = Transaccion.objects.filter(
                cuenta=cuenta_capital,
                periodo=periodo_actual
            ).aggregate(
                total_debe=Sum('debe'),
                total_haber=Sum('haber')
            )
            capital_inicial = (trans_capital_agg['total_haber'] or Decimal('0')) - (trans_capital_agg['total_debe'] or Decimal('0'))
        except Cuenta.DoesNotExist:
            capital_inicial = Decimal('0')

        # 2. Obtener Reservas iniciales (3102)
        reservas_inicial = Decimal('0')
        try:
            cuenta_reservas = Cuenta.objects.get(codigo='3102')
            trans_reservas_agg = Transaccion.objects.filter(
                cuenta=cuenta_reservas,
                periodo=periodo_actual
            ).aggregate(
                total_debe=Sum('debe'),
                total_haber=Sum('haber')
            )
            reservas_inicial = (trans_reservas_agg['total_haber'] or Decimal('0')) - (trans_reservas_agg['total_debe'] or Decimal('0'))
        except Cuenta.DoesNotExist:
            reservas_inicial = Decimal('0')

        # 3. Calcular RESULTADO del ejercicio
        total_ingresos = calcular_ventas_totales(periodo_actual, incluir_ajustes=True)
        total_gastos = calcular_gastos_totales(periodo_actual, incluir_ajustes=True)
        resultado_ejercicio = total_ingresos - total_gastos
        hay_perdida = resultado_ejercicio < 0

        # 4. CALCULAR PATRIMONIO SEGÚN RESULTADO
        if hay_perdida:
            # En caso de PÉRDIDA
            perdida_total = abs(resultado_ejercicio)
            capital_final = capital_inicial - perdida_total
            reservas_final = reservas_inicial
            
            # Agregar Capital Social
            if capital_final > 0:
                patrimonio.append({
                    'codigo': '3101', 'nombre': 'Capital Social',
                    'saldo': capital_final, 'es_acreedor': True,
                    'debe': Decimal('0'), 'haber': capital_final
                })
                total_haber += capital_final
                total_haber_patrimonio += capital_final  # SUMA AL HABER DE PATRIMONIO
            else: # Déficit
                patrimonio.append({
                    'codigo': '3101', 'nombre': 'Capital Social (Déficit)',
                    'saldo': abs(capital_final), 'es_acreedor': False,
                    'debe': abs(capital_final), 'haber': Decimal('0')
                })
                total_debe += abs(capital_final)
                total_debe_patrimonio += abs(capital_final)  # SUMA AL DEBE DE PATRIMONIO
            
            # Agregar Reservas
            if reservas_final > 0:
                patrimonio.append({
                    'codigo': '3102', 'nombre': 'Reservas de Capital',
                    'saldo': reservas_final, 'es_acreedor': True,
                    'debe': Decimal('0'), 'haber': reservas_final
                })
                total_haber += reservas_final
                total_haber_patrimonio += reservas_final  # SUMA AL HABER DE PATRIMONIO
                
        else:
            # En caso de UTILIDAD
            reinversion = resultado_ejercicio * Decimal('0.60')
            reservas_utilidad_periodo = resultado_ejercicio * Decimal('0.40')
            
            capital_final = capital_inicial + reinversion
            reservas_final = reservas_inicial + reservas_utilidad_periodo

            # Agregar Capital Social
            if capital_final > 0:
                patrimonio.append({
                    'codigo': '3101', 'nombre': 'Capital Social',
                    'saldo': capital_final, 'es_acreedor': True,
                    'debe': Decimal('0'), 'haber': capital_final
                })
                total_haber += capital_final
                total_haber_patrimonio += capital_final  # SUMA AL HABER DE PATRIMONIO

            # Agregar Reservas
            if reservas_final > 0:
                patrimonio.append({
                    'codigo': '3102', 'nombre': 'Reservas de Capital',
                    'saldo': reservas_final,
                    'es_acreedor': True,
                    'debe': Decimal('0'),
                    'haber': reservas_final
                })
                total_haber += reservas_final
                total_haber_patrimonio += reservas_final  # SUMA AL HABER DE PATRIMONIO

    # Obtener todos los períodos disponibles
    periodos = PeriodoContable.objects.all().order_by('-año')

    # Verificar que el balance cuadre
    balance_cuadra = (round(total_debe, 2) == round(total_haber, 2))

    context = {
        'activos': activos,
        'pasivos': pasivos,
        'patrimonio': patrimonio,
        'total_debe': total_debe,
        'total_haber': total_haber,
        # NUEVOS: Totales por sección (DEBE y HABER separados)
        'total_debe_activos': total_debe_activos,
        'total_haber_activos': total_haber_activos,
        'total_debe_pasivos': total_debe_pasivos,
        'total_haber_pasivos': total_haber_pasivos,
        'total_debe_patrimonio': total_debe_patrimonio,
        'total_haber_patrimonio': total_haber_patrimonio,
        'periodo_actual': periodo_actual,
        'periodos': periodos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'balance_cuadra': balance_cuadra,
    }

    return render(request, 'EstadosFinancieros/balanceGeneral.html', context)