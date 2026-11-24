"""Análisis DuPont y estados financieros proforma (método de porcentaje de ventas).

Usa los mismos datos de EstadoPeriodo que las razones financieras
(los que se cargan a mano o con la plantilla de Excel de ratios).
"""
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill


def _div(a, b):
    if a is None or b in (None, 0):
        return None
    return a / b


def _prod(*valores):
    if any(v is None for v in valores):
        return None
    r = 1
    for v in valores:
        r *= v
    return r


# =====================================================================
# DUPONT
# =====================================================================
def calcular_dupont(periodos, usar_promedios=True):
    """periodos: [(año, valores)] ordenados. Devuelve una lista de dicts, uno por año."""
    filas, anterior = [], None
    for anio, v in periodos:
        def g(k, v=v):
            return v.get(k) or 0

        def prom(k, v=v, anterior=anterior):
            if usar_promedios and anterior is not None and k in anterior:
                return (g(k) + (anterior.get(k) or 0)) / 2
            return g(k)

        ventas, un = g("ventas_netas"), g("utilidad_neta")
        uo, gf = g("utilidad_operacion"), g("gastos_financieros")
        uai = uo - gf
        activo, patrimonio = prom("activo_total"), prom("patrimonio")

        margen = _div(un, ventas)
        rotacion = _div(ventas, activo)
        multiplicador = _div(activo, patrimonio)
        carga_fiscal = _div(un, uai)
        carga_intereses = _div(uai, uo)
        margen_operativo = _div(uo, ventas)

        filas.append({
            "anio": anio,
            "ventas": ventas, "utilidad_neta": un, "utilidad_operacion": uo, "uai": uai,
            "activo": activo, "patrimonio": patrimonio,
            "margen_neto": margen,
            "rotacion": rotacion,
            "multiplicador": multiplicador,
            "roa": _prod(margen, rotacion),
            "roe": _prod(margen, rotacion, multiplicador),
            "roe_directo": _div(un, patrimonio),
            "carga_fiscal": carga_fiscal,
            "carga_intereses": carga_intereses,
            "margen_operativo": margen_operativo,
            "roe_5": _prod(carga_fiscal, carga_intereses, margen_operativo, rotacion, multiplicador),
        })
        anterior = v
    return filas


def efectos_dupont(filas):
    """Cuánto aportó cada factor al cambio del ROE entre años consecutivos
    (sustituciones sucesivas: margen, luego rotación, luego multiplicador)."""
    efectos = []
    for a, b in zip(filas, filas[1:]):
        if None in (a["roe"], b["roe"]):
            continue
        m0, r0, k0 = a["margen_neto"], a["rotacion"], a["multiplicador"]
        m1, r1, k1 = b["margen_neto"], b["rotacion"], b["multiplicador"]
        efectos.append({
            "periodo": f"{a['anio']} – {b['anio']}",
            "roe_inicial": a["roe"], "roe_final": b["roe"],
            "margen": (m1 - m0) * r0 * k0,
            "rotacion": m1 * (r1 - r0) * k0,
            "multiplicador": m1 * r1 * (k1 - k0),
            "total": b["roe"] - a["roe"],
        })
    return efectos


# =====================================================================
# PROFORMA (porcentaje de ventas)
# =====================================================================
# Conceptos que se proyectan como % de las ventas: (clave, etiqueta)
PCT_ER = [
    ("costo_ventas", "Costo de ventas"),
    ("gastos_operacion", "Gastos de operación"),
]
PCT_BG = [
    ("efectivo", "Efectivo y equivalentes"),
    ("cuentas_por_cobrar", "Cuentas por cobrar"),
    ("inventarios", "Inventarios"),
    ("otros_activos_corrientes", "Otros activos corrientes"),
    ("activo_fijo_neto", "Activo fijo neto"),
    ("cuentas_por_pagar", "Cuentas por pagar comerciales"),
    ("otros_pasivos_corrientes", "Otros pasivos corrientes (retenciones, impuestos, etc.)"),
]
PCT_TODOS = PCT_ER + PCT_BG
MAX_ANIOS = 5


def _derivados(v):
    """Agrega a los valores de un año los rubros que se calculan por diferencia."""
    g = lambda k: v.get(k) or 0
    d = {k: g(k) for k in ("ventas_netas", "costo_ventas", "utilidad_operacion", "gastos_financieros",
                           "utilidad_neta", "efectivo", "cuentas_por_cobrar", "inventarios",
                           "activo_corriente", "activo_fijo_neto", "activo_total", "cuentas_por_pagar",
                           "pasivo_corriente", "pasivo_no_corriente", "patrimonio")}
    d["gastos_operacion"] = d["ventas_netas"] - d["costo_ventas"] - d["utilidad_operacion"]
    d["otros_activos_corrientes"] = (d["activo_corriente"] - d["efectivo"]
                                     - d["cuentas_por_cobrar"] - d["inventarios"])
    d["otros_activos_no_corrientes"] = d["activo_total"] - d["activo_corriente"] - d["activo_fijo_neto"]
    d["otros_pasivos_corrientes"] = d["pasivo_corriente"] - d["cuentas_por_pagar"]
    d["uai"] = d["utilidad_operacion"] - d["gastos_financieros"]
    return d


def supuestos_historicos(periodos, anio_base=None):
    """Supuestos iniciales calculados con los datos reales del año base."""
    datos = dict(periodos)
    anios = sorted(datos)
    anio_base = anio_base if anio_base in datos else anios[-1]
    d = _derivados(datos[anio_base])
    ventas = d["ventas_netas"]

    crecimiento = 10.0
    anterior = [a for a in anios if a < anio_base]
    if anterior:
        ventas_ant = (datos[anterior[-1]].get("ventas_netas") or 0)
        if ventas_ant:
            crecimiento = round((ventas / ventas_ant - 1) * 100, 2)

    tasa = 0.0
    if d["uai"] > 0:
        tasa = round(max(0, min(100, (1 - d["utilidad_neta"] / d["uai"]) * 100)), 2)

    return {
        "anio_base": anio_base,
        "crecimiento": [crecimiento] * 3,
        "pct": {k: round(d[k] / ventas * 100, 2) if ventas else 0 for k, _ in PCT_TODOS},
        "activo_fijo_variable": True,
        "gastos_financieros": round(d["gastos_financieros"], 2),
        "tasa_impuesto": tasa,
        "dividendos": 0.0,
    }


def proyectar(base_valores, s):
    """Devuelve una lista de dicts: el año base (real) y los años proyectados."""
    prev = _derivados(base_valores)
    prev["fer_acumulado"] = 0.0
    columnas = [dict(prev, anio=s["anio_base"], real=True, dividendos=None, utilidad_retenida=None,
                     isr=prev["uai"] - prev["utilidad_neta"], fer_anio=None)]
    pct = {k: (s["pct"].get(k) or 0) / 100 for k, _ in PCT_TODOS}

    for i, g in enumerate(s["crecimiento"]):
        p = {"anio": s["anio_base"] + i + 1, "real": False}
        ventas = prev["ventas_netas"] * (1 + g / 100)
        p["ventas_netas"] = ventas
        p["costo_ventas"] = ventas * pct["costo_ventas"]
        p["utilidad_bruta"] = ventas - p["costo_ventas"]
        p["gastos_operacion"] = ventas * pct["gastos_operacion"]
        p["utilidad_operacion"] = p["utilidad_bruta"] - p["gastos_operacion"]
        p["gastos_financieros"] = s["gastos_financieros"]
        p["uai"] = p["utilidad_operacion"] - p["gastos_financieros"]
        p["isr"] = max(0, p["uai"] * s["tasa_impuesto"] / 100)
        p["utilidad_neta"] = p["uai"] - p["isr"]
        p["dividendos"] = max(0, p["utilidad_neta"]) * s["dividendos"] / 100
        p["utilidad_retenida"] = p["utilidad_neta"] - p["dividendos"]

        for k in ("efectivo", "cuentas_por_cobrar", "inventarios", "otros_activos_corrientes",
                  "cuentas_por_pagar", "otros_pasivos_corrientes"):
            p[k] = ventas * pct[k]
        p["activo_fijo_neto"] = ventas * pct["activo_fijo_neto"] if s["activo_fijo_variable"] \
            else prev["activo_fijo_neto"]
        p["otros_activos_no_corrientes"] = prev["otros_activos_no_corrientes"]
        p["activo_corriente"] = (p["efectivo"] + p["cuentas_por_cobrar"] + p["inventarios"]
                                 + p["otros_activos_corrientes"])
        p["activo_total"] = p["activo_corriente"] + p["activo_fijo_neto"] + p["otros_activos_no_corrientes"]

        p["pasivo_corriente"] = p["cuentas_por_pagar"] + p["otros_pasivos_corrientes"]
        p["pasivo_no_corriente"] = prev["pasivo_no_corriente"]
        p["patrimonio"] = prev["patrimonio"] + p["utilidad_retenida"]
        # Fondos externos requeridos: lo que falta (o sobra) para que el balance cuadre
        p["fer_acumulado"] = p["activo_total"] - (p["pasivo_corriente"] + p["pasivo_no_corriente"]
                                                  + p["patrimonio"])
        p["fer_anio"] = p["fer_acumulado"] - prev["fer_acumulado"]
        columnas.append(p)
        prev = p

    for c in columnas:
        c.setdefault("utilidad_bruta", c["ventas_netas"] - c["costo_ventas"])
        c["pasivo_total"] = c["pasivo_corriente"] + c["pasivo_no_corriente"]
        c["total_pasivo_patrimonio"] = c["pasivo_total"] + c["patrimonio"]
        c["total_con_fer"] = c["total_pasivo_patrimonio"] + c["fer_acumulado"]
    return columnas


# Filas que se muestran: (clave, etiqueta, estilo)  estilo: d=detalle, s=subtotal, T=total, f=fondos
FILAS_ER = [
    ("ventas_netas", "Ventas netas", "s"),
    ("costo_ventas", "Costo de ventas", "d"),
    ("utilidad_bruta", "Utilidad bruta", "s"),
    ("gastos_operacion", "Gastos de operación", "d"),
    ("utilidad_operacion", "Utilidad de operación", "s"),
    ("gastos_financieros", "Gastos financieros", "d"),
    ("uai", "Utilidad antes de impuestos", "s"),
    ("isr", "Impuestos (y reserva legal)", "d"),
    ("utilidad_neta", "Utilidad neta", "T"),
    ("dividendos", "Dividendos", "d"),
    ("utilidad_retenida", "Utilidad retenida", "s"),
]
FILAS_BG = [
    ("efectivo", "Efectivo y equivalentes", "d"),
    ("cuentas_por_cobrar", "Cuentas por cobrar", "d"),
    ("inventarios", "Inventarios", "d"),
    ("otros_activos_corrientes", "Otros activos corrientes", "d"),
    ("activo_corriente", "Total activo corriente", "s"),
    ("activo_fijo_neto", "Activo fijo neto", "d"),
    ("otros_activos_no_corrientes", "Otros activos no corrientes", "d"),
    ("activo_total", "Total activo", "T"),
    ("cuentas_por_pagar", "Cuentas por pagar comerciales", "d"),
    ("otros_pasivos_corrientes", "Otros pasivos corrientes", "d"),
    ("pasivo_corriente", "Total pasivo corriente", "s"),
    ("pasivo_no_corriente", "Pasivo no corriente", "d"),
    ("pasivo_total", "Total pasivo", "s"),
    ("patrimonio", "Patrimonio", "d"),
    ("total_pasivo_patrimonio", "Total pasivo y patrimonio (sin financiamiento nuevo)", "s"),
    ("fer_acumulado", "Fondos externos requeridos (acumulado)", "f"),
    ("total_con_fer", "Total pasivo, patrimonio y fondos externos", "T"),
]


def armar_tabla(columnas, filas):
    return [{"etiqueta": etq, "estilo": est, "valores": [c.get(k) for c in columnas]}
            for k, etq, est in filas]


# =====================================================================
# EXCEL DE SUPUESTOS DEL PROFORMA
# =====================================================================
def _filas_plantilla(s):
    filas = [("anio_base", "Año base (debe existir en el análisis)", s["anio_base"], "")]
    for i in range(MAX_ANIOS):
        valor = s["crecimiento"][i] if i < len(s["crecimiento"]) else None
        filas.append((f"crecimiento_{i + 1}", f"Crecimiento de ventas año +{i + 1} (%)", valor,
                      "Deja vacío para proyectar menos años"))
    for k, etq in PCT_TODOS:
        filas.append((f"pct_{k}", f"{etq} (% de ventas)", s["pct"].get(k, 0), ""))
    filas += [
        ("activo_fijo_variable", "¿El activo fijo crece con las ventas? (SI/NO)",
         "SI" if s["activo_fijo_variable"] else "NO", "NO = se mantiene igual al año base"),
        ("gastos_financieros", "Gastos financieros proyectados ($ por año)", s["gastos_financieros"], ""),
        ("tasa_impuesto", "Tasa de impuestos sobre la utilidad (%)", s["tasa_impuesto"], ""),
        ("dividendos", "Dividendos (% de la utilidad neta)", s["dividendos"], ""),
    ]
    return filas


def generar_plantilla_proforma(s):
    wb = Workbook()
    ws = wb.active
    ws.title = "Supuestos"
    ws.append(["Clave (no modificar)", "Supuesto", "Valor", "Nota"])
    for celda in ws[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="1F4E78")
        celda.alignment = Alignment(horizontal="center")
    for fila in _filas_plantilla(s):
        ws.append(list(fila))
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 58
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 40

    ins = wb.create_sheet("Instrucciones")
    for linea in [
        "1. No modifiques la columna A (clave).",
        "2. Los porcentajes se escriben como número: 10 = 10 %. También puedes usar celdas con formato de porcentaje.",
        "3. Los % de ventas que trae la plantilla salen del año base; cámbialos si esperas otra estructura.",
        "4. Puedes proyectar de 1 a 5 años: llena solo los crecimientos que necesites.",
    ]:
        ins.append([linea])
    ins.column_dimensions["A"].width = 100

    salida = BytesIO()
    wb.save(salida)
    return salida.getvalue()


def _numero(celda, nombre):
    v = celda.value
    if v in (None, ""):
        return None
    if isinstance(v, str):
        v = v.replace("%", "").replace(",", "").strip()
    try:
        v = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"'{nombre}' debe ser un número (se encontró {celda.value!r}).")
    if "%" in (celda.number_format or ""):
        v *= 100
    return v


def leer_plantilla_proforma(archivo):
    wb = load_workbook(archivo, data_only=True)
    ws = wb["Supuestos"] if "Supuestos" in wb.sheetnames else wb.worksheets[0]
    celdas = {}
    for fila in ws.iter_rows(min_row=2):
        clave = fila[0].value
        if clave and len(fila) >= 3:
            celdas[str(clave).strip()] = fila[2]
    wb.close()

    def num(clave, requerido=True):
        if clave not in celdas:
            if requerido:
                raise ValueError(f"Falta la fila '{clave}' en el archivo.")
            return None
        v = _numero(celdas[clave], clave)
        if v is None and requerido:
            raise ValueError(f"Falta el valor de '{clave}'.")
        return v

    anio_base = num("anio_base")
    crecimiento = []
    for i in range(1, MAX_ANIOS + 1):
        v = num(f"crecimiento_{i}", requerido=False)
        if v is None:
            break
        crecimiento.append(v)
    if not crecimiento:
        raise ValueError("Escribe al menos el crecimiento de ventas del año +1.")

    af = celdas.get("activo_fijo_variable")
    af = str(af.value).strip().upper() if af is not None and af.value is not None else "SI"
    return {
        "anio_base": int(anio_base),
        "crecimiento": crecimiento,
        "pct": {k: num(f"pct_{k}") for k, _ in PCT_TODOS},
        "activo_fijo_variable": af not in ("NO", "N", "FALSE", "0"),
        "gastos_financieros": num("gastos_financieros"),
        "tasa_impuesto": num("tasa_impuesto"),
        "dividendos": num("dividendos"),
    }