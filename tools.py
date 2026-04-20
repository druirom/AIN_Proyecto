"""
Herramienta para consultar la API de TMDb.

"""

from __future__ import annotations
from typing import Any, Dict
import os

import requests


TMDB_URL = "https://api.themoviedb.org/3"


def tmdb_tool(query: str, mode: str = "search", movie_id: int = 0) -> Dict[str, Any]:
    """
    Consulta la API de TMDb.
    - mode="search": busca peliculas por texto.
    - mode="details": devuelve detalles de una pelicula por su id.
    """
    api_key = os.environ.get("TMDB_API_KEY")
    if not api_key:
        return {"status": "error", "message": "Falta TMDB_API_KEY"}

    try:
        if mode == "search":
            # buscamos peliculas que coincidan con la query
            url = f"{TMDB_URL}/search/movie"
            params = {"api_key": api_key, "query": query, "language": "es-ES"}
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()

            # nos quedamos con los 5 primeros resultados
            results = []
            for m in data.get("results", [])[:5]:
                results.append({
                    "id": m.get("id"),
                    "title": m.get("title"),
                    "release_date": m.get("release_date"),
                    "overview": m.get("overview"),
                    "vote_average": m.get("vote_average"),
                })
            return {"status": "success", "results": results}

        elif mode == "details":
            # detalles ampliados de una pelicula concreta
            url = f"{TMDB_URL}/movie/{movie_id}"
            params = {
                "api_key": api_key,
                "language": "es-ES",
                "append_to_response": "credits",
            }
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()

            # sacamos el director del crew
            director = None
            for c in data.get("credits", {}).get("crew", []):
                if c.get("job") == "Director":
                    director = c.get("name")
                    break

            return {
                "status": "success",
                "movie": {
                    "title": data.get("title"),
                    "release_date": data.get("release_date"),
                    "runtime": data.get("runtime"),
                    "genres": [g["name"] for g in data.get("genres", [])],
                    "overview": data.get("overview"),
                    "director": director,
                    "vote_average": data.get("vote_average"),
                },
            }

        else:
            return {"status": "error", "message": f"modo '{mode}' no valido"}

    except Exception as e:
        # si algo falla devolvemos el error al agente
        return {"status": "error", "message": str(e)}
