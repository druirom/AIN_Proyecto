
# Agente generador de informes sobre cine.

from __future__ import annotations

try:
    from google.adk.agents.llm_agent import Agent
except Exception:
    from google.adk.agents import Agent

from google.adk.models.lite_llm import LiteLlm

from .tools import tmdb_tool


# ---------------------------
# Root agent
# ---------------------------

root_agent = Agent(
    # Pick a model you have configured (Gemini via GOOGLE_API_KEY, or via Vertex).
    # You can also route via LiteLLM if your environment is set up that way.
    #model="gemini-3-flash-preview",
    model=LiteLlm(
        model="openai/gpt-oss-120b",
        api_base="https://api.poligpt.upv.es/",
        api_key="sk-LFXs1kjaSxtEDgOMlPUOpA",
    ),

    name="root_agent",
    description=(
        "Genera informes academicos sobre cine usando datos reales de TMDb "
        "a traves de la tool tmdb_tool."
    ),
    instruction=(
        "Eres un agente que genera informes academicos sobre cine. SIEMPRE debes "
        "fundamentarte en la herramienta tmdb_tool.\n"
        "Pasos: (1) planifica el informe a partir del tema del usuario.\n"
        "(2) llama a tmdb_tool(query, mode='search') para buscar peliculas "
        "relevantes al tema.\n"
        "(3) si encuentras una pelicula interesante, llama a "
        "tmdb_tool(query='', mode='details', movie_id=<id>) para sacar "
        "director, generos, duracion, etc.\n"
        "(4) redacta el informe en espanol con tono academico, apoyandote en "
        "los datos que devuelve la tool (sin inventar titulos).\n"
        "(5) responde SOLO con un JSON (sin markdown, sin texto extra) con "
        "esta estructura:\n"
        "{\n"
        '  "title": "Titulo del informe",\n'
        '  "sections": [\n'
        '    {"name": "Introduccion", "word_count": 160, "content": "..."},\n'
        '    {"name": "Desarrollo", "word_count": 180, "content": "..."},\n'
        '    {"name": "Analisis", "word_count": 155, "content": "..."},\n'
        '    {"name": "Conclusiones", "word_count": 155, "content": "..."}\n'
        "  ],\n"
        '  "total_words": 650,\n'
        '  "num_sections": 4,\n'
        '  "num_references": 3,\n'
        '  "references": ["ref1", "ref2", "ref3"],\n'
        '  "pdf_path": "output/informe.pdf"\n'
        "}\n"
        "REGLAS OBLIGATORIAS (si no se cumplen el informe es invalido):\n"
        "- sections debe tener al menos 4 elementos.\n"
        "- Obligatorio incluir una seccion llamada 'Introduccion' y otra "
        "'Conclusiones'.\n"
        "- Cada seccion debe tener word_count >= 150 (redacta parrafos largos).\n"
        "- total_words >= 450.\n"
        "- num_references >= 3.\n"
        "- Todo el contenido en espanol."
    ),
    tools=[tmdb_tool],
)
