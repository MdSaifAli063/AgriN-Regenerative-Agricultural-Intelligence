"""
JSON-LD Context serving endpoint.
Serves static `.jsonld` context files from the static/contexts/ directory so
external consumers can dereference context URIs like:
  GET /contexts/soil-intelligence.jsonld
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/contexts", tags=["JSON-LD Contexts"])

CONTEXTS_DIR = Path(__file__).parents[2] / "static" / "contexts"

_ALLOWED = {
    "soil-intelligence.jsonld",
    "disease-diagnosis.jsonld",
    "outbreak-aggregate.jsonld",
    "climate-analogue.jsonld",
}


@router.get("/{context_file}", summary="Serve JSON-LD Context")
async def serve_context(context_file: str):
    if context_file not in _ALLOWED:
        raise HTTPException(status_code=404, detail=f"Context '{context_file}' not found.")

    path = CONTEXTS_DIR / context_file
    if not path.exists():
        raise HTTPException(status_code=404, detail="Context file missing on disk.")

    return FileResponse(
        str(path),
        media_type="application/ld+json",
        headers={"Access-Control-Allow-Origin": "*"},
    )


@router.get("", summary="List Available JSON-LD Contexts")
async def list_contexts():
    return {
        "contexts": [
            {
                "id": name.removesuffix(".jsonld"),
                "href": f"/contexts/{name}",
                "type": "application/ld+json",
            }
            for name in sorted(_ALLOWED)
        ]
    }
