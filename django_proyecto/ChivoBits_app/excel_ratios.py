from io import BytesIO
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from ChivoBits_app.ratios_calculos import CONCEPTOS, SIEMPRE_POSITIVOS


def generar_plantilla(periodos=None):
    """periodos: lista de (año, dict_valores). Si está vacía, pone dos años de ejemplo."""
    periodos = periodos or [(2019, {}), (2020, {})]
    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"

    ws.append(["Clave (no modificar)", "Concepto"] + [anio for anio, _ in periodos])
    for celda in ws[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="1F4E78")
        celda.alignment = Alignment(horizontal="center")

    estado_actual = None
    for clave, (etiqueta, estado) in CONCEPTOS.items():
        if estado != estado_actual:
            ws.append(["", estado.upper()])
            ws.cell(ws.max_row, 2).font = Font(bold=True)
            estado_actual = estado
        ws.append([clave, etiqueta] + [valores.get(clave) for _, valores in periodos])
        for col in range(3, 3 + len(periodos)):
            ws.cell(ws.max_row, col).number_format = "#,##0.00"

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 38
    for col in range(3, 3 + len(periodos)):
        ws.column_dimensions[ws.cell(1, col).column_letter].width = 16

    ws2 = wb.create_sheet("Instrucciones")
    for linea in [
        "1. No modifiques la columna A (clave).",
        "2. En la fila 1, desde la columna C, escribe los años (puedes agregar más columnas).",
        "3. Puedes escribir montos o fórmulas (se lee el valor calculado).",
        "4. Costo de ventas y gastos financieros pueden ir en positivo o negativo.",
        "5. Las celdas vacías se toman como 0.",
    ]:
        ws2.append([linea])
    ws2.column_dimensions["A"].width = 90

    salida = BytesIO()
    wb.save(salida)
    return salida.getvalue()


def leer_plantilla(archivo):
    """Devuelve lista de (año, dict_valores) ordenada por año."""
    wb = load_workbook(archivo, data_only=True)
    ws = wb["Datos"] if "Datos" in wb.sheetnames else wb.worksheets[0]

    anios = {}
    for col in range(3, ws.max_column + 1):
        v = ws.cell(1, col).value
        if v in (None, ""):
            continue
        try:
            anios[col] = int(float(v))
        except (TypeError, ValueError):
            raise ValueError(f"El encabezado '{v}' de la fila 1 no es un año válido.")
    if not anios:
        raise ValueError("No se encontraron años en la fila 1 (desde la columna C).")

    datos = {anio: {} for anio in anios.values()}
    encontrados = set()
    for fila in range(2, ws.max_row + 1):
        clave = ws.cell(fila, 1).value
        if not clave or clave not in CONCEPTOS:
            continue
        encontrados.add(clave)
        for col, anio in anios.items():
            v = ws.cell(fila, col).value
            if v in (None, ""):
                v = 0
            try:
                v = float(v)
            except (TypeError, ValueError):
                raise ValueError(f"Valor no numérico en '{CONCEPTOS[clave][0]}', año {anio}: {v!r}")
            datos[anio][clave] = abs(v) if clave in SIEMPRE_POSITIVOS else v
    wb.close()

    faltan = set(CONCEPTOS) - encontrados
    if faltan:
        raise ValueError("Faltan conceptos en el archivo: " + ", ".join(CONCEPTOS[c][0] for c in faltan))
    return sorted(datos.items())