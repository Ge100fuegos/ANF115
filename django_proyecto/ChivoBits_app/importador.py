from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string


def leer_columna_excel(archivo, hoja, columna, fila_inicio, fila_fin):
    wb = load_workbook(archivo, data_only=True, read_only=True)
    if hoja and hoja not in wb.sheetnames:
        raise ValueError(f"La hoja '{hoja}' no existe. Hojas del archivo: {', '.join(wb.sheetnames)}")
    ws = wb[hoja] if hoja else wb.worksheets[0]
    col = column_index_from_string(columna.strip().upper())

    valores = []
    for (v,) in ws.iter_rows(min_row=fila_inicio, max_row=fila_fin,
                             min_col=col, max_col=col, values_only=True):
        if v is None or v == "":
            continue
        try:
            valores.append(float(v))
        except (TypeError, ValueError):
            raise ValueError(f"Valor no numérico en la columna {columna}: {v!r}")
    wb.close()

    if len(valores) < 2:
        raise ValueError("Se necesitan al menos 2 valores en el rango indicado.")
    return valores


def agrupar_anual(valores, meses=12):
    if len(valores) % meses:
        raise ValueError(f"Para agrupar por año los datos deben ser múltiplo de {meses} (hay {len(valores)}).")
    return [sum(valores[i:i + meses]) for i in range(0, len(valores), meses)]