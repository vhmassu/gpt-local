"""Cotizaciones MBA Saltillo en PDF (MXN, IVA desglosado) + ficha del cliente en la memoria.

Datos de la empresa y tarifas en ~/Cotizaciones/ (se crean la primera vez):
  empresa.json   nombre, teléfono, correo, dirección, condiciones, tasa de IVA
  precios.json   tarifas por equipo: {"GS-1930": {"descripcion": "...", "dia": 0, "semana": 0, "mes": 0}}

Uso:
  python cotizar.py datos.json          (o JSON por la entrada estándar:  echo '{...}' | python cotizar.py -)
Formato de datos:
  {"cliente": {"nombre": "Juan Pérez", "empresa": "Grupo X", "telefono": "", "correo": ""},
   "partidas": [{"clave": "GS-1930", "cantidad": 1, "periodo": "semana", "duracion": 2},
                {"descripcion": "Montacargas 2.5 t gas LP", "cantidad": 1, "periodo": "mes",
                 "duracion": 1, "precio_unitario": 18000}],
   "flete": 1500, "notas": "Entrega en Ramos Arizpe", "vigencia_dias": 15}
precio_unitario es por periodo (día/semana/mes). Si falta, se toma de precios.json.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

DIR = Path.home() / "Cotizaciones"
PERIODOS = {"dia": "día", "día": "día", "dias": "día", "días": "día",
            "semana": "semana", "semanas": "semana", "mes": "mes", "meses": "mes",
            "pieza": "pieza", "servicio": "servicio", "unidad": "pieza"}

EMPRESA_BASE = {
    "nombre": "MBA Saltillo",
    "subtitulo": "Montacargas y Brazos Articulados",
    "telefono": "",
    "correo": "",
    "direccion": "Saltillo, Coahuila",
    "tasa_iva": 0.16,
    "condiciones": [
        "Precios en pesos mexicanos (MXN). IVA desglosado.",
        "Vigencia de la cotización: {vigencia} días naturales.",
        "Tarifas por periodo indicado; tiempo adicional se cobra a la tarifa vigente.",
        "Flete de entrega y recolección según se indica en la cotización.",
    ],
}
PRECIOS_BASE = {
    "_instrucciones": "Llena las tarifas en MXN sin IVA. 0 o null = sin precio (pedirlo al cotizar).",
    "GS-1930": {"descripcion": "Plataforma de tijera eléctrica Genie GS-1930", "dia": None, "semana": None, "mes": None},
    "GS-2632": {"descripcion": "Plataforma de tijera eléctrica Genie GS-2632", "dia": None, "semana": None, "mes": None},
    "GS-3246": {"descripcion": "Plataforma de tijera eléctrica Genie GS-3246", "dia": None, "semana": None, "mes": None},
    "Z-45": {"descripcion": "Brazo articulado Genie Z-45/25", "dia": None, "semana": None, "mes": None},
    "S-45": {"descripcion": "Brazo telescópico Genie S-45", "dia": None, "semana": None, "mes": None},
    "MONTACARGAS-2.5T": {"descripcion": "Montacargas 2.5 t (gas LP)", "dia": None, "semana": None, "mes": None},
}


class CotizacionError(ValueError):
    pass


def preparar_carpeta() -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    for nombre, base in (("empresa.json", EMPRESA_BASE), ("precios.json", PRECIOS_BASE)):
        f = DIR / nombre
        if not f.exists():
            f.write_text(json.dumps(base, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _leer(nombre: str) -> dict:
    preparar_carpeta()
    return json.loads((DIR / nombre).read_text(encoding="utf-8"))


def _folio() -> str:
    f = DIR / "folio.txt"
    n = int(f.read_text().strip() or 0) + 1 if f.exists() else 1
    f.write_text(str(n))
    return f"COT-{date.today().year}-{n:04d}"


def _slug(t: str) -> str:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "-", t).strip("-")[:40] or "cliente"


def mxn(v: float) -> str:
    return f"${v:,.2f}"


def calcular(datos: dict) -> dict:
    """Valida y calcula. Devuelve partidas con importe, subtotal, iva y total."""
    empresa = _leer("empresa.json")
    precios = _leer("precios.json")
    cliente = datos.get("cliente") or {}
    if not (cliente.get("nombre") or cliente.get("empresa")):
        raise CotizacionError("Falta el nombre o la empresa del cliente.")
    partidas = []
    for i, p in enumerate(datos.get("partidas") or [], 1):
        clave = (p.get("clave") or "").strip()
        ref = precios.get(clave, {}) if clave else {}
        periodo = PERIODOS.get(str(p.get("periodo", "pieza")).lower().strip(), None)
        if periodo is None:
            raise CotizacionError(f"Partida {i}: periodo '{p.get('periodo')}' no válido (día, semana, mes, pieza, servicio).")
        precio = p.get("precio_unitario")
        if precio in (None, "", 0):
            precio = ref.get({"día": "dia"}.get(periodo, periodo))
        if precio in (None, "", 0):
            raise CotizacionError(
                f"Partida {i} ({clave or p.get('descripcion', '?')}): falta la tarifa por {periodo}. "
                f"Dámela o llénala en {DIR / 'precios.json'}.")
        cantidad = float(p.get("cantidad", 1))
        duracion = float(p.get("duracion", 1))
        desc = p.get("descripcion") or ref.get("descripcion") or clave
        importe = round(cantidad * duracion * float(precio), 2)
        partidas.append({"descripcion": desc, "cantidad": cantidad, "periodo": periodo,
                         "duracion": duracion, "precio": float(precio), "importe": importe})
    if not partidas:
        raise CotizacionError("La cotización no tiene partidas.")
    flete = float(datos.get("flete") or 0)
    if flete:
        partidas.append({"descripcion": "Flete (entrega y recolección)", "cantidad": 1,
                         "periodo": "servicio", "duracion": 1, "precio": flete, "importe": flete})
    subtotal = round(sum(p["importe"] for p in partidas), 2)
    tasa = float(datos.get("tasa_iva", empresa.get("tasa_iva", 0.16)))
    iva = round(subtotal * tasa, 2)
    return {"empresa": empresa, "cliente": cliente, "partidas": partidas, "subtotal": subtotal,
            "tasa_iva": tasa, "iva": iva, "total": round(subtotal + iva, 2),
            "vigencia": int(datos.get("vigencia_dias", 15)), "notas": datos.get("notas", "")}


def _lat(t) -> str:
    """fpdf con fuentes base solo admite latin-1."""
    t = str(t).replace("—", "-").replace("–", "-").replace("“", '"').replace("”", '"').replace("’", "'")
    return t.encode("latin-1", "replace").decode("latin-1")


def _num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def generar_pdf(c: dict, folio: str, salida: Path) -> None:
    from fpdf import FPDF  # pip install fpdf2

    e, cl = c["empresa"], c["cliente"]
    pdf = FPDF(format="Letter")
    pdf.set_auto_page_break(True, 18)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 9, _lat(e.get("nombre", "")), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for linea in (e.get("subtitulo"), e.get("direccion"),
                  " · ".join(x for x in (e.get("telefono"), e.get("correo")) if x)):
        if linea:
            pdf.cell(0, 5, _lat(linea), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 7, _lat(f"Cotización {folio}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    hoy = date.today()
    pdf.cell(0, 5, _lat(f"Fecha: {hoy:%d/%m/%Y}   ·   Vigente hasta: {hoy + timedelta(days=c['vigencia']):%d/%m/%Y}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "Cliente", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for linea in (cl.get("empresa"), cl.get("nombre"),
                  " · ".join(x for x in (cl.get("telefono"), cl.get("correo")) if x)):
        if linea:
            pdf.cell(0, 5, _lat(linea), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    anchos = (84, 16, 30, 30, 36)
    pdf.set_fill_color(235, 235, 235)
    pdf.set_font("Helvetica", "B", 9)
    for w, t in zip(anchos, ("Descripción", "Cant.", "Periodo", "Precio unit.", "Importe")):
        pdf.cell(w, 7, _lat(t), border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for p in c["partidas"]:
        per = p["periodo"] if p["periodo"] in ("pieza", "servicio") else \
            f"{_num(p['duracion'])} {p['periodo']}{'' if p['duracion'] == 1 else ('es' if p['periodo'] == 'mes' else 's')}"
        celdas = (p["descripcion"], _num(p["cantidad"]), per, mxn(p["precio"]), mxn(p["importe"]))
        for w, t, a in zip(anchos, celdas, ("L", "C", "C", "R", "R")):
            pdf.cell(w, 7, _lat(t)[:52], border=1, align=a)
        pdf.ln()
    pdf.ln(1)
    for etiqueta, valor, negrita in (("Subtotal", c["subtotal"], False),
                                     (f"IVA {c['tasa_iva'] * 100:g}%", c["iva"], False),
                                     ("Total MXN", c["total"], True)):
        pdf.set_font("Helvetica", "B" if negrita else "", 10)
        pdf.cell(sum(anchos[:4]), 7, _lat(etiqueta), align="R")
        pdf.cell(anchos[4], 7, mxn(valor), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
    if c["notas"]:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 5, "Notas", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, _lat(c["notas"]), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "Condiciones", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for cond in e.get("condiciones", []):
        pdf.multi_cell(0, 5, _lat("- " + cond.replace("{vigencia}", str(c["vigencia"]))), new_x="LMARGIN", new_y="NEXT")
    salida.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(salida))


def generar(datos: dict, guardar_en_memoria: bool = True) -> dict:
    """Calcula, crea el PDF y registra al cliente en la memoria. Devuelve resumen."""
    c = calcular(datos)
    folio = _folio()
    nombre_cliente = c["cliente"].get("empresa") or c["cliente"].get("nombre")
    salida = DIR / f"{folio}-{_slug(nombre_cliente)}.pdf"
    generar_pdf(c, folio, salida)
    resumen = {"folio": folio, "pdf": str(salida), "subtotal": c["subtotal"], "iva": c["iva"],
               "total": c["total"], "partidas": [p["descripcion"] for p in c["partidas"]]}
    if guardar_en_memoria:
        try:
            import memoria_unificada as mem
            cl = c["cliente"]
            mem.guardar_cliente(
                nombre=cl.get("nombre") or cl.get("empresa"), empresa=cl.get("empresa", ""),
                telefono=cl.get("telefono", ""), correo=cl.get("correo", ""),
                equipo=", ".join(p["descripcion"] for p in c["partidas"] if p["periodo"] != "servicio"),
                precio=f"{folio}: total {mxn(c['total'])} MXN con IVA", agente="cotizador",
                notas=c["notas"])
            resumen["memoria"] = "cliente registrado"
        except Exception as e:  # la cotización no depende de la memoria
            resumen["memoria"] = f"no se registró: {e}"
    return resumen


def texto_resumen(r: dict) -> str:
    return (f"Cotización {r['folio']} lista: {r['pdf']}\n"
            f"Subtotal {mxn(r['subtotal'])} + IVA {mxn(r['iva'])} = Total {mxn(r['total'])} MXN")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if len(sys.argv) < 2:
        preparar_carpeta()
        print(__doc__)
        sys.exit(0)
    fuente = sys.stdin.read() if sys.argv[1] == "-" else Path(sys.argv[1]).read_text(encoding="utf-8")
    try:
        print(texto_resumen(generar(json.loads(fuente))))
    except CotizacionError as e:
        print(f"No se pudo cotizar: {e}")
        sys.exit(1)
