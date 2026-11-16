"""Lectura de estados financieros completos y cálculo del análisis vertical y horizontal."""
import re
import unicodedata
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string


def a_numero(v):
    """Convierte '1,200.50', '$ 90,000', '(20,000)' o números a float. Vacío -> None."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    texto = str(v).strip().replace("$", "").replace(",", "").replace(" ", "")
    if texto in ("", "-", "—"):
        return None
    negativo = texto.startswith("(") and texto.endswith(")")
    texto = texto.strip("()")
    try:
        n = float(texto)
    except ValueError:
        raise ValueError(f"'{v}' no es un número válido.")
    return -n if negativo else n


def construir_lineas(filas, anios):
    """filas: lista de (nombre, [valor por año]). Devuelve lista de dicts para guardar."""
    lineas = []
    for nombre, valores in filas:
        nombre = str(nombre).strip() if nombre is not None else ""
        if not nombre:
            continue
        numeros = [a_numero(v) for v in valores]
        es_titulo = all(n is None for n in numeros)
        lineas.append({
            "nombre": nombre,
            "es_titulo": es_titulo,
            "valores": {} if es_titulo else {str(a): (n or 0.0) for a, n in zip(anios, numeros)},
        })
    if not any(not l["es_titulo"] for l in lineas):
        raise ValueError("No se encontraron filas con valores numéricos.")
    return lineas


def leer_estado_excel(archivo, hoja, columna_nombres, fila_encabezado, fila_inicio, fila_fin):
    """Lee un estado con los nombres en una columna y un año por columna a la derecha."""
    wb = load_workbook(archivo, data_only=True)
    if hoja and hoja not in wb.sheetnames:
        raise ValueError(f"La hoja '{hoja}' no existe. Hojas del archivo: {', '.join(wb.sheetnames)}")
    ws = wb[hoja] if hoja else wb.worksheets[0]
    col_nombre = column_index_from_string(columna_nombres.strip().upper())

    columnas_anio = {}
    for col in range(col_nombre + 1, ws.max_column + 1):
        v = ws.cell(fila_encabezado, col).value
        try:
            anio = int(float(str(v).strip()))
        except (TypeError, ValueError):
            continue
        if 1900 <= anio <= 2100:
            columnas_anio[col] = anio
    if not columnas_anio:
        raise ValueError(f"No se encontraron años en la fila {fila_encabezado}, "
                         f"a la derecha de la columna {columna_nombres.upper()}.")

    # Ordenar por año ascendente (muchos estados vienen 2020, 2019)
    orden = sorted(columnas_anio.items(), key=lambda x: x[1])
    anios = [a for _, a in orden]
    filas = []
    for fila in range(fila_inicio, fila_fin + 1):
        nombre = ws.cell(fila, col_nombre).value
        filas.append((nombre, [ws.cell(fila, col).value for col, _ in orden]))
    wb.close()
    return anios, construir_lineas(filas, anios)


def leer_texto_pegado(texto, anios):
    """Filas copiadas de Excel: nombre<TAB>valor_año1<TAB>valor_año2..."""
    filas = []
    for n, linea in enumerate(texto.splitlines(), start=1):
        if not linea.strip():
            continue
        partes = linea.split("\t")
        nombre, valores = partes[0], partes[1:]
        if len(valores) > len(anios):
            raise ValueError(f"Línea {n}: tiene {len(valores)} valores pero indicaste {len(anios)} años.")
        valores += [None] * (len(anios) - len(valores))
        try:
            [a_numero(v) for v in valores]
        except ValueError as e:
            raise ValueError(f"Línea {n}: {e}")
        filas.append((nombre, valores))
    return construir_lineas(filas, anios)


def _normalizar(texto):
    t = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t).strip(" :")


def detectar_base(lineas, estado):
    """Índice de la línea base: Total activo (BG) o Ventas netas (ER)."""
    claves = (["total activo", "activo total", "total de activo", "total activos", "activos totales"]
              if estado == "BG" else ["ventas netas", "ingresos netos", "ventas", "ingresos"])
    nombres = [(i, _normalizar(l["nombre"])) for i, l in enumerate(lineas) if not l["es_titulo"]]
    # 1) coincidencia exacta  2) contiene la clave sin ser subtotal (circulante / corriente)
    for clave in claves:
        for i, n in nombres:
            if n == clave:
                return i
    for clave in claves:
        for i, n in nombres:
            if clave in n and not any(x in n for x in ("circulante", "corriente", "costo")):
                return i
    numericas = [i for i, l in enumerate(lineas) if not l["es_titulo"]]
    if estado == "BG":
        return max(numericas, key=lambda i: max(abs(v) for v in lineas[i]["valores"].values()))
    return numericas[0]


def calcular_vertical_horizontal(lineas, anios, indice_base):
    """Devuelve una fila por línea con montos, % vertical y variaciones entre años consecutivos."""
    base = lineas[indice_base]["valores"]
    resultado = []
    for i, l in enumerate(lineas):
        if l["es_titulo"]:
            resultado.append({"nombre": l["nombre"], "es_titulo": True, "es_base": False})
            continue
        valores = [l["valores"].get(str(a), 0.0) for a in anios]
        vertical = []
        for a, v in zip(anios, valores):
            b = base.get(str(a), 0)
            vertical.append(v / b * 100 if b else None)
        variaciones = []
        for j in range(1, len(anios)):
            anterior, actual = valores[j - 1], valores[j]
            absoluta = actual - anterior
            relativa = absoluta / abs(anterior) * 100 if anterior else None
            variaciones.append({"absoluta": absoluta, "relativa": relativa})
        resultado.append({
            "nombre": l["nombre"], "es_titulo": False, "es_base": i == indice_base,
            "columnas": [{"valor": v, "vertical": p} for v, p in zip(valores, vertical)],
            "variaciones": variaciones,
        })
    return resultado