"""Lectura e importación del catálogo de cuentas desde Excel."""
import re
import unicodedata
from collections import defaultdict
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

from ChivoBits_app.models import Cuenta

TIPOS_VALIDOS = {"ACTIVO", "PASIVO", "PATRIMONIO", "INGRESO", "GASTO"}
SINONIMOS_TIPO = {
    "ACTIVOS": "ACTIVO", "PASIVOS": "PASIVO", "CAPITAL": "PATRIMONIO",
    "INGRESOS": "INGRESO", "GASTOS": "GASTO", "COSTO": "GASTO", "COSTOS": "GASTO",
}
# Para cuentas de grupo sin tipo en el archivo: se deduce por el nombre (el orden importa)
PALABRAS_TIPO = [
    ("INGRES", "INGRESO"), ("ACREEDOR", "INGRESO"),
    ("GAST", "GASTO"), ("COST", "GASTO"), ("DEUDOR", "GASTO"),
    ("PATRIMONIO", "PATRIMONIO"), ("CAPITAL", "PATRIMONIO"),
    ("PASIVO", "PASIVO"), ("ACTIVO", "ACTIVO"),
]
ENCABEZADOS_CODIGO = {"codigo", "cuenta contable", "codigo de cuenta", "codigo cuenta", "cuenta", "cod"}
ENCABEZADOS_NOMBRE = {"nombre", "descripcion", "nombre de la cuenta", "nombre cuenta", "concepto"}


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", texto).strip().lower()


def _tipo_desde_valor(valor):
    if valor is None:
        return None
    t = _normalizar(valor).upper()
    return t if t in TIPOS_VALIDOS else SINONIMOS_TIPO.get(t)


def _tipo_desde_nombre(nombre):
    n = _normalizar(nombre).upper()
    for palabra, tipo in PALABRAS_TIPO:
        if palabra in n:
            return tipo
    return None


def _codigo_desde_celda(valor):
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return re.sub(r"[\s.\-]", "", str(valor))   # acepta 1101.01 o 1101-01


def nivel_por_codigo(codigo):
    """Mismo criterio que Cuenta.save()."""
    return {1: 1, 2: 2, 4: 3}.get(len(codigo), 4)


def leer_catalogo(archivo):
    """Devuelve (filas, errores). Cada fila: {'fila', 'codigo', 'nombre', 'tipo'}."""
    wb = load_workbook(archivo, data_only=True, read_only=True)
    ws = wb.worksheets[0]
    filas, errores = [], []
    col_codigo = col_nombre = None
    cols_tipo = []

    for n, fila in enumerate(ws.iter_rows(values_only=True), start=1):
        if col_codigo is None:
            # Buscar la fila de encabezados en las primeras 20 filas
            encabezados = [_normalizar(v) if v is not None else "" for v in fila]
            cod = [i for i, h in enumerate(encabezados) if h in ENCABEZADOS_CODIGO]
            nom = [i for i, h in enumerate(encabezados) if h in ENCABEZADOS_NOMBRE]
            if cod and nom:
                col_codigo, col_nombre = cod[0], nom[0]
                cols_tipo = [i for i, h in enumerate(encabezados) if "tipo" in h or "clase" in h]
            elif n >= 20:
                break
            continue

        valor_codigo = fila[col_codigo] if col_codigo < len(fila) else None
        valor_nombre = fila[col_nombre] if col_nombre < len(fila) else None
        if valor_codigo in (None, "") and valor_nombre in (None, ""):
            continue

        codigo = _codigo_desde_celda(valor_codigo) if valor_codigo is not None else ""
        nombre = re.sub(r"\s+", " ", str(valor_nombre or "")).strip().upper()[:100]
        if not codigo.isdigit() or len(codigo) > 10:
            errores.append(f"Fila {n}: código inválido '{valor_codigo}'.")
            continue
        if not nombre:
            errores.append(f"Fila {n}: la cuenta {codigo} no tiene nombre.")
            continue

        tipo = None
        for i in cols_tipo:
            if i < len(fila):
                tipo = _tipo_desde_valor(fila[i])
                if tipo:
                    break
        filas.append({"fila": n, "codigo": codigo, "nombre": nombre, "tipo": tipo})

    wb.close()
    if col_codigo is None:
        raise ValueError("No se encontró la fila de encabezados. El archivo debe tener columnas "
                         "'Código' (o 'Cuenta Contable') y 'Nombre' (o 'Descripción').")
    if not filas:
        raise ValueError("El archivo no tiene cuentas para importar.")
    return filas, errores


def guardar_catalogo(filas, actualizar_nombres=False):
    """Crea las cuentas nuevas (padres antes que hijas). Llamar dentro de transaction.atomic()."""
    resultado = {"creadas": 0, "actualizadas": 0, "omitidas": 0, "errores": []}
    por_codigo = {c.codigo: c for c in Cuenta.objects.all()}

    # Quitar códigos repetidos dentro del archivo
    unicas, vistos = [], set()
    for f in filas:
        if f["codigo"] in vistos:
            resultado["errores"].append(f"Fila {f['fila']}: el código {f['codigo']} está repetido en el archivo.")
            continue
        vistos.add(f["codigo"])
        unicas.append(f)

    # Agrupar por largo del código: así cada padre se crea antes que sus hijas
    por_largo = defaultdict(list)
    for f in unicas:
        por_largo[len(f["codigo"])].append(f)

    a_actualizar = []
    for largo in sorted(por_largo):
        nuevas = []
        for f in sorted(por_largo[largo], key=lambda x: x["codigo"]):
            existente = por_codigo.get(f["codigo"])
            if existente:
                if actualizar_nombres and existente.nombre != f["nombre"]:
                    existente.nombre = f["nombre"]
                    a_actualizar.append(existente)
                else:
                    resultado["omitidas"] += 1
                continue

            padre = None
            for i in range(len(f["codigo"]) - 1, 0, -1):
                padre = por_codigo.get(f["codigo"][:i])
                if padre:
                    break

            if padre:
                tipo = padre.tipo
            elif largo > 1:
                resultado["errores"].append(f"Fila {f['fila']}: la cuenta {f['codigo']} no tiene cuenta padre.")
                continue
            else:
                tipo = f["tipo"] or _tipo_desde_nombre(f["nombre"])
                if not tipo:
                    resultado["errores"].append(
                        f"Fila {f['fila']}: no se pudo determinar el tipo del grupo {f['codigo']} - {f['nombre']} "
                        f"(agrega una columna 'Tipo' con ACTIVO, PASIVO, PATRIMONIO, INGRESO o GASTO).")
                    continue

            nuevas.append(Cuenta(
                codigo=f["codigo"], nombre=f["nombre"], tipo=tipo,
                nivel=nivel_por_codigo(f["codigo"]), cuenta_padre=padre, activa=True,
            ))

        # bulk_create no llama a save(), por eso el nivel se calcula arriba
        for c in Cuenta.objects.bulk_create(nuevas):
            por_codigo[c.codigo] = c
        resultado["creadas"] += len(nuevas)

    if a_actualizar:
        Cuenta.objects.bulk_update(a_actualizar, ["nombre"])
        resultado["actualizadas"] = len(a_actualizar)
    return resultado


def generar_plantilla():
    wb = Workbook()
    ws = wb.active
    ws.title = "Catalogo"
    ws.append(["Código", "Nombre", "Tipo"])
    for celda in ws[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="303A63")
    ejemplos = [
        ("1", "ACTIVO", "ACTIVO"),
        ("11", "ACTIVO CORRIENTE", ""),
        ("1101", "EFECTIVO Y EQUIVALENTES", ""),
        ("110101", "CAJA GENERAL", ""),
        ("2", "PASIVO", "PASIVO"),
    ]
    for fila in ejemplos:
        ws.append(fila)
    for celda in ws["A"]:
        celda.number_format = "@"
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 50
    ws.column_dimensions["C"].width = 14

    ins = wb.create_sheet("Instrucciones")
    for linea in [
        "1. Llena la hoja 'Catalogo': una cuenta por fila.",
        "2. Código: solo números (1, 11, 1101, 110101...). La cuenta padre se detecta por el código.",
        "3. Tipo: solo es obligatorio en las cuentas de grupo (1 dígito): ACTIVO, PASIVO, PATRIMONIO, INGRESO o GASTO.",
        "   Las demás cuentas heredan el tipo de su cuenta padre.",
        "4. Las cuentas que ya existen en el sistema no se duplican.",
    ]:
        ins.append([linea])
    ins.column_dimensions["A"].width = 110

    salida = BytesIO()
    wb.save(salida)
    return salida.getvalue()