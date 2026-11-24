"""Conceptos de los estados financieros y fórmulas de las razones financieras."""

# clave: (etiqueta, estado)
CONCEPTOS = {
    "efectivo": ("Efectivo y equivalentes", "Balance General"),
    "cuentas_por_cobrar": ("Cuentas por cobrar", "Balance General"),
    "inventarios": ("Inventarios", "Balance General"),
    "activo_corriente": ("Total activo corriente", "Balance General"),
    "activo_fijo_neto": ("Activo fijo neto (PPE)", "Balance General"),
    "activo_total": ("Total activo", "Balance General"),
    "cuentas_por_pagar": ("Cuentas por pagar comerciales", "Balance General"),
    "pasivo_corriente": ("Total pasivo corriente", "Balance General"),
    "pasivo_no_corriente": ("Total pasivo no corriente", "Balance General"),
    "patrimonio": ("Total patrimonio", "Balance General"),
    "ventas_netas": ("Ventas netas", "Estado de Resultados"),
    "costo_ventas": ("Costo de ventas", "Estado de Resultados"),
    "utilidad_operacion": ("Utilidad de operación", "Estado de Resultados"),
    "gastos_financieros": ("Gastos financieros (intereses)", "Estado de Resultados"),
    "utilidad_neta": ("Utilidad neta", "Estado de Resultados"),
}

# Se guardan siempre en positivo (algunos Excel los traen negativos)
SIEMPRE_POSITIVOS = {"costo_ventas", "gastos_financieros"}


def _div(a, b):
    if a is None or b in (None, 0):
        return None
    return a / b


class Datos:
    """Valores de un año, con promedio contra el año anterior."""

    def __init__(self, actual, anterior=None, usar_promedios=True):
        self.a = actual
        self.p = anterior if usar_promedios else None

    def __getitem__(self, clave):
        if clave == "pasivo_total":
            return self.a.get("pasivo_corriente", 0) + self.a.get("pasivo_no_corriente", 0)
        if clave == "utilidad_bruta":
            return self.a.get("ventas_netas", 0) - self.a.get("costo_ventas", 0)
        return self.a.get(clave, 0)

    def prom(self, clave):
        if self.p is None or clave not in self.p:
            return self[clave]
        return (self.a.get(clave, 0) + self.p[clave]) / 2


# clave: (grupo, nombre, unidad, fórmula, qué mide, función)
RATIOS = {
    # ---------- Liquidez ----------
    "razon_corriente": ("Liquidez", "Razón corriente", "veces",
        "Activo corriente / Pasivo corriente",
        "Dólares de activo corriente por cada dólar de deuda a corto plazo.",
        lambda d: _div(d["activo_corriente"], d["pasivo_corriente"])),
    "prueba_acida": ("Liquidez", "Prueba ácida", "veces",
        "(Activo corriente − Inventarios) / Pasivo corriente",
        "Capacidad de pagar deudas de corto plazo sin vender inventario.",
        lambda d: _div(d["activo_corriente"] - d["inventarios"], d["pasivo_corriente"])),
    "razon_efectivo": ("Liquidez", "Razón de efectivo", "veces",
        "Efectivo / Pasivo corriente",
        "Parte de la deuda de corto plazo que se paga con el efectivo disponible.",
        lambda d: _div(d["efectivo"], d["pasivo_corriente"])),
    "capital_trabajo": ("Liquidez", "Capital de trabajo", "$",
        "Activo corriente − Pasivo corriente",
        "Recursos de corto plazo que quedan después de cubrir las deudas de corto plazo.",
        lambda d: d["activo_corriente"] - d["pasivo_corriente"]),

    # ---------- Actividad ----------
    "rotacion_cxc": ("Actividad", "Rotación de cuentas por cobrar", "veces",
        "Ventas netas / Cuentas por cobrar promedio",
        "Veces al año que se cobran las cuentas por cobrar.",
        lambda d: _div(d["ventas_netas"], d.prom("cuentas_por_cobrar"))),
    "periodo_cobro": ("Actividad", "Período medio de cobro", "días",
        "(Cuentas por cobrar promedio × 365) / Ventas netas",
        "Días que tarda la empresa en cobrar.",
        lambda d: _div(d.prom("cuentas_por_cobrar") * 365, d["ventas_netas"])),
    "rotacion_cxp": ("Actividad", "Rotación de cuentas por pagar", "veces",
        "Costo de ventas / Cuentas por pagar promedio",
        "Veces al año que se paga a proveedores.",
        lambda d: _div(d["costo_ventas"], d.prom("cuentas_por_pagar"))),
    "periodo_pago": ("Actividad", "Período medio de pago", "días",
        "(Cuentas por pagar promedio × 365) / Costo de ventas",
        "Días que tarda la empresa en pagar a proveedores.",
        lambda d: _div(d.prom("cuentas_por_pagar") * 365, d["costo_ventas"])),
    "rotacion_inventario": ("Actividad", "Rotación de inventarios", "veces",
        "Costo de ventas / Inventario promedio",
        "Veces al año que se vende y repone el inventario.",
        lambda d: _div(d["costo_ventas"], d.prom("inventarios"))),
    "dias_inventario": ("Actividad", "Días de inventario", "días",
        "(Inventario promedio × 365) / Costo de ventas",
        "Días que el inventario permanece en bodega.",
        lambda d: _div(d.prom("inventarios") * 365, d["costo_ventas"]) if d.prom("inventarios") else None),
    "ciclo_efectivo": ("Actividad", "Ciclo de conversión del efectivo", "días",
        "Días de inventario + Período de cobro − Período de pago",
        "Días entre que se paga a proveedores y se cobra a clientes.",
        lambda d: None if 0 in (d["costo_ventas"], d["ventas_netas"]) else (
            d.prom("inventarios") * 365 / d["costo_ventas"]
            + d.prom("cuentas_por_cobrar") * 365 / d["ventas_netas"]
            - d.prom("cuentas_por_pagar") * 365 / d["costo_ventas"])),
    "rotacion_activo_total": ("Actividad", "Rotación de activos totales", "veces",
        "Ventas netas / Activo total promedio",
        "Dólares de ventas por cada dólar invertido en activos.",
        lambda d: _div(d["ventas_netas"], d.prom("activo_total"))),
    "rotacion_activo_fijo": ("Actividad", "Rotación de activos fijos", "veces",
        "Ventas netas / Activo fijo neto promedio",
        "Dólares de ventas por cada dólar invertido en activo fijo.",
        lambda d: _div(d["ventas_netas"], d.prom("activo_fijo_neto"))),

    # ---------- Endeudamiento ----------
    "razon_endeudamiento": ("Endeudamiento", "Razón de endeudamiento", "%",
        "Pasivo total / Activo total",
        "Porcentaje de los activos financiado con deuda.",
        lambda d: _div(d["pasivo_total"], d["activo_total"])),
    "deuda_patrimonio": ("Endeudamiento", "Deuda a patrimonio", "veces",
        "Pasivo total / Patrimonio",
        "Dólares de deuda por cada dólar de los dueños.",
        lambda d: _div(d["pasivo_total"], d["patrimonio"])),
    "cobertura_intereses": ("Endeudamiento", "Cobertura de intereses", "veces",
        "Utilidad de operación / Gastos financieros",
        "Veces que la utilidad de operación cubre los intereses.",
        lambda d: _div(d["utilidad_operacion"], d["gastos_financieros"])),

    # ---------- Rentabilidad ----------
    "margen_bruto": ("Rentabilidad", "Margen bruto", "%",
        "Utilidad bruta / Ventas netas",
        "Lo que queda de cada dólar vendido después del costo de ventas.",
        lambda d: _div(d["utilidad_bruta"], d["ventas_netas"])),
    "margen_operativo": ("Rentabilidad", "Margen operativo", "%",
        "Utilidad de operación / Ventas netas",
        "Lo que queda de cada dólar vendido después de los gastos de operación.",
        lambda d: _div(d["utilidad_operacion"], d["ventas_netas"])),
    "margen_neto": ("Rentabilidad", "Margen neto", "%",
        "Utilidad neta / Ventas netas",
        "Lo que queda de cada dólar vendido después de todos los gastos e impuestos.",
        lambda d: _div(d["utilidad_neta"], d["ventas_netas"])),
    "roa": ("Rentabilidad", "Rentabilidad sobre activos (ROA)", "%",
        "Utilidad neta / Activo total promedio",
        "Utilidad generada por cada dólar invertido en activos.",
        lambda d: _div(d["utilidad_neta"], d.prom("activo_total"))),
    "roe": ("Rentabilidad", "Rentabilidad sobre patrimonio (ROE)", "%",
        "Utilidad neta / Patrimonio promedio",
        "Utilidad generada por cada dólar aportado por los dueños.",
        lambda d: _div(d["utilidad_neta"], d.prom("patrimonio"))),
}

GRUPOS = ["Liquidez", "Actividad", "Endeudamiento", "Rentabilidad"]


def calcular_ratios(periodos, usar_promedios=True):
    """periodos: lista de (año, dict_valores) ordenada por año.
    Devuelve {clave_ratio: {año: valor}}."""
    resultado = {clave: {} for clave in RATIOS}
    anterior = None
    for anio, valores in periodos:
        datos = Datos(valores, anterior, usar_promedios)
        for clave, (_, _, unidad, _, _, funcion) in RATIOS.items():
            try:
                v = funcion(datos)
            except ZeroDivisionError:
                v = None
            if v is not None and unidad == "%":
                v *= 100
            resultado[clave][anio] = v
        anterior = valores
    return resultado


def verificar_balance(valores):
    """Mensaje si Activo ≠ Pasivo + Patrimonio (tolerancia de 1)."""
    activo = valores.get("activo_total", 0)
    pas_pat = (valores.get("pasivo_corriente", 0) + valores.get("pasivo_no_corriente", 0)
               + valores.get("patrimonio", 0))
    if abs(activo - pas_pat) > 1:
        return f"El balance no cuadra: Activo {activo:,.2f} ≠ Pasivo + Patrimonio {pas_pat:,.2f}"
    return None