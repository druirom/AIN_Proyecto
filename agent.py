from __future__ import annotations
from typing import Any, Dict, List
import os

from ddgs import DDGS
from fpdf import FPDF

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm


def buscar_peliculas(query: str) -> Dict[str, Any]:
    """Busca en DuckDuckGo las 3 primeras peliculas relacionadas con la query. Devuelve titulo, url y resumen de cada resultado."""
    with DDGS() as ddgs:
        resultados = ddgs.text(f"{query} pelicula", max_results=3)

    # nos quedamos solo con los campos que nos interesan
    limpios = []
    for r in resultados:
        limpios.append({
            "title": r.get("title"),
            "url": r.get("href"),
            "summary": r.get("body"),
        })
    return {"result": limpios}


def _limpiar(txt: str) -> str:
    """Quita caracteres que la fuente helvetica (latin-1) no soporta."""
    if not txt:
        return ""
    cambios = {
        "–": "-", "—": "-", "−": "-",
        "‘": "'", "’": "'",
        "“": '"', "”": '"',
        "…": "...",
        "\u00a0": " ",  # nbsp
        "\r": "",
        "\t": " ",
    }
    for a, b in cambios.items():
        txt = txt.replace(a, b)
    # cualquier caracter fuera de latin-1 lo quitamos
    return txt.encode("latin-1", "ignore").decode("latin-1")


def _partir_tokens_largos(texto: str, max_len: int = 40) -> str:
    """Parte palabras muy largas (urls, etc.) insertando espacios cada max_len caracteres.
    Asi fpdf siempre tiene un punto donde cortar la linea."""

    palabras = texto.split(" ")
    resultado = []
    for p in palabras:
        if len(p) > max_len:
            # cortar en trozos de max_len
            trozos = [p[i:i+max_len] for i in range(0, len(p), max_len)]
            resultado.append(" ".join(trozos))
        else:
            resultado.append(p)
    return " ".join(resultado)


def _escribir_parrafo(pdf: "FPDF", texto: str, alto: float = 6) -> None:
    """Escribe un parrafo con multi_cell asegurando el margen izquierdo y partiendo tokens largos."""
    if not texto:
        return
    texto = _partir_tokens_largos(_limpiar(texto))

    # garantizamos posicion inicial correcta (margen izquierdo, ancho completo)
    pdf.set_x(pdf.l_margin)
    try:
        pdf.multi_cell(0, alto, texto)
    except Exception:
        # si aun asi falla, escribimos linea a linea saltando la problematica
        pdf.set_x(pdf.l_margin)
        for linea in texto.split("\n"):
            try:
                pdf.multi_cell(0, alto, linea)
            except Exception:
                continue
            pdf.set_x(pdf.l_margin)


def guardar_pdf(title: str, sections: List[Dict[str, Any]], references: List[str]) -> Dict[str, Any]:
    """Genera el PDF del informe en output/informe.pdf a partir del titulo, las secciones (cada una con name y content) y la lista de referencias."""
    path = os.path.join("output", "informe.pdf")
    os.makedirs("output", exist_ok=True)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # titulo principal
    pdf.set_font("helvetica", "B", 18)
    _escribir_parrafo(pdf, title, alto=10)
    pdf.ln(5)

    # secciones
    for s in sections:
        pdf.set_font("helvetica", "B", 14)
        _escribir_parrafo(pdf, s.get("name", "Seccion"), alto=8)
        pdf.set_font("helvetica", size=11)
        _escribir_parrafo(pdf, s.get("content", ""), alto=6)
        pdf.ln(5)

    # referencias
    if references:
        pdf.set_font("helvetica", "B", 14)
        _escribir_parrafo(pdf, "Referencias", alto=8)
        pdf.set_font("helvetica", size=10)
        for ref in references:
            # las urls se parten solas en _partir_tokens_largos
            _escribir_parrafo(pdf, f"- {ref}", alto=6)

    pdf.output(path)
    return {"result": {"pdf_path": path}}

# ---------------------------
# Root agent
# ---------------------------

root_agent = Agent(
    # Pick a model you have configured (Gemini via GOOGLE_API_KEY, or via Vertex).
    # You can also route via LiteLLM if your environment is set up that way.
    #model="gemini-3-flash-preview",
    model=LiteLlm(model="openai/gpt-oss-120b", api_base="https://api.poligpt.upv.es/", api_key="sk-LFXs1kjaSxtEDgOMlPUOpA"),

    name="root_agent",
    description=(
        "Genera informes academicos sobre cine buscando informacion en DuckDuckGo y guardando el PDF."
    ),
    instruction=(
        "Eres un agente que genera informes academicos UNICAMENTE sobre cine (peliculas, directores, sagas, generos cinematograficos).\n"
        "Si el usuario pide un informe sobre cualquier otro tema que no sea cine, responde: 'Lo siento, solo puedo generar informes sobre cine.' y no llames a ninguna herramienta.\n"
        "\n"
        "Pasos cuando el tema es de cine: (1) llama a buscar_peliculas(query) con el tema del usuario para obtener las 3 primeras peliculas.\n"
        "(2) redacta el informe en espanol con al menos 4 secciones, obligatoriamente una llamada 'Introduccion' y otra 'Conclusiones'. Cada seccion con al menos 150 palabras y el total con al menos 450. Usa al menos 3 referencias (pueden ser las urls devueltas por buscar_peliculas).\n"
        "(3) llama a guardar_pdf(title, sections, references) pasando el titulo, la lista de secciones (cada una con name y content completo) y la lista de referencias. IMPORTANTE: los strings de content deben ir en una sola linea, sin saltos de linea reales. Usa espacios entre parrafos, nunca \\n literal ni saltos de linea dentro del string JSON.\n"
        "(4) responde SOLO con un JSON con esta estructura, sin texto extra ni markdown:\n"
        "{\"title\": \"...\", \"sections\": [{\"name\": \"Introduccion\", \"word_count\": 160}, ...], \"total_words\": 650, \"num_sections\": 4, \"num_references\": 3, \"pdf_path\": \"output/informe.pdf\"}"
    ),
    tools=[buscar_peliculas, guardar_pdf],
)