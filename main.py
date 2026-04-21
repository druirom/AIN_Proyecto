"""
Agente generador de informes. Ejecuta el agente, parsea el JSON que devuelve, genera el PDF y guarda
el JSON final en la carpeta output/.

"""

import asyncio
import json
import os
import re
import sys

from fpdf import FPDF

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import root_agent


OUTPUT_DIR = "output"
PDF_PATH = os.path.join(OUTPUT_DIR, "informe.pdf")
JSON_PATH = os.path.join(OUTPUT_DIR, "informe.json")

APP_NAME = "document_generator_agent"
USER_ID = "user"
SESSION_ID = "session1"


def parse_json(text: str):
    """Extrae el JSON de la respuesta del agente."""
    # el modelo a veces devuelve el JSON envuelto en hola```json ... ```
    # asi que lo limpiamos antes de parsear
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = text.rstrip("`").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # ultimo intento: buscar el bloque {...}
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start:end + 1])
        return None


def generar_pdf(data: dict, path: str):
    """Genera el PDF del informe a partir del dict con titulo, secciones y refs."""
    
    class PDF(FPDF):
        def header(self):
            
            self.set_font("helvetica", "B", 10)
            self.cell(0, 10, f"Informe: {data.get('title', 'Sin título')}", align="R")
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font("helvetica", "I", 8)

            self.cell(0, 10, f"Página {self.page_no()}", align="C")

    pdf = PDF()
    pdf.add_page()
    
    # --- TÍTULO PRINCIPAL ---
    pdf.set_font("helvetica", "B", 20)
    pdf.multi_cell(0, 15, text=data.get("title", "Informe").upper(), align="C")
    pdf.ln(10)

    # --- SECCIONES ---
    for section in data.get("sections", []):
        # Nombre de la sección (Subtítulo)
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, text=section.get("name", "Sección"), ln=True)
        
        # Línea decorativa debajo del subtítulo
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 50, pdf.get_y())
        pdf.ln(5)

        # Contenido de la sección
        pdf.set_font("helvetica", size=11)
        contenido = section.get("content", "")
        pdf.multi_cell(0, 7, text=contenido)
        pdf.ln(10) # Espacio entre secciones


    if "references" in data or "num_references" in data:
        pdf.add_page() # Empezar referencias en página nueva
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, text="Referencias", ln=True)
        pdf.ln(5)
        pdf.set_font("helvetica", size=10)
        
        # Si el agente te da una lista de referencias
        refs = data.get("references", [])
        if isinstance(refs, list):
            for ref in refs:
                pdf.multi_cell(0, 6, text=f"- {ref}")
        else:
            pdf.cell(0, 10, text=f"Total de referencias citadas: {data.get('num_references', 0)}")

    # Guardar el archivo
    # Aseguramos que la carpeta existe justo antes de guardar
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pdf.output(path)


async def run_agent(prompt: str) -> str:
    """Lanza el agente con el prompt del usuario y devuelve su respuesta final."""
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    msg = types.Content(role="user", parts=[types.Part(text=prompt)])

    final_text = ""
    async for event in runner.run_async(
        user_id=USER_ID, session_id=SESSION_ID, new_message=msg
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(
                p.text for p in event.content.parts if p.text
            )

    return final_text


def main():
    # prompt por defecto si no se pasa argumento
    if len(sys.argv) > 1:
        prompt = sys.argv[1]
    else:
        prompt = "Genera un informe academico sobre el cine de ciencia ficcion."

    print(f"[INFO] Prompt: {prompt}")
    respuesta = asyncio.run(run_agent(prompt))

    data = parse_json(respuesta)
    if data is None:
        print("[ERROR] No se pudo parsear el JSON del agente")
        print(respuesta)
        return 1

    # recalculamos los campos por si el LLM los cuenta mal
    total = 0
    for s in data.get("sections", []):
        if "content" in s and not s.get("word_count"):
            s["word_count"] = len(s["content"].split())
        total += s.get("word_count", 0)
    data["total_words"] = total
    data["num_sections"] = len(data.get("sections", []))
    data["pdf_path"] = PDF_PATH

    # creamos la carpeta output si no existe
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # generamos el PDF
    generar_pdf(data, PDF_PATH)
    print(f"[OK] PDF guardado en {PDF_PATH}")

    # JSON final para la evaluacion (solo los campos de la rubrica)
    salida = {
        "title": data.get("title", ""),
        "sections": [
            {"name": s["name"], "word_count": s["word_count"]}
            for s in data.get("sections", [])
        ],
        "total_words": data["total_words"],
        "num_sections": data["num_sections"],
        "num_references": data.get("num_references", 0),
        "pdf_path": data["pdf_path"],
    }

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    print(f"[OK] JSON guardado en {JSON_PATH}")

    # imprimimos tambien el JSON por pantalla
    print(json.dumps(salida, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
