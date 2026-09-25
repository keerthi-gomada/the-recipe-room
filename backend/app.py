import json
import re
import faiss
import numpy as np
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from generation import generate_dishes, parse_query, METHODS, EXTRAS, STYLES, MODEL_ID
from fastapi.middleware.cors import CORSMiddleware
from epicure_engine import EpicureEngine

app = FastAPI(title="Epicure-Core Recipe Intelligence & Generation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = EpicureEngine(repo_id="Kaikaku/epicure-core")
recipe_index = None
recipe_metadata = []

BASE_DIR = Path(__file__).resolve().parent
if (BASE_DIR / "recipe_faiss.index").exists() and (BASE_DIR / "recipes_metadata.json").exists():
    recipe_index = faiss.read_index(str(BASE_DIR / "recipe_faiss.index"))
    with open(BASE_DIR / "recipes_metadata.json", "r", encoding="utf-8") as f:
        recipe_metadata = json.load(f)
    print(f"[✓] Loaded {recipe_index.ntotal} recipes from index.")
else:
    print("[!] Warning: Run indexer.py first to build FAISS index.")

def detect_cuisine_from_query(query_str):
    normalized = query_str.lower().replace('_', ' ')
    for name in sorted(STYLES, key=len, reverse=True):
        if re.search(r'\b' + re.escape(name) + r'\b', normalized):
            style = STYLES[name]
            return style.pole, {"label": style.label}
    for pole_key in engine.poles:
        if not pole_key.startswith('cuisine:'):
            continue
        name = pole_key.removeprefix('cuisine:').replace('_', ' ').lower()
        if re.search(r'\b' + re.escape(name) + r'\b', normalized):
            return pole_key, {"label": name.title()}
    return None, None

class GenerationRequest(BaseModel):
    q: str | None = Field(default=None, min_length=1, max_length=500)
    main_ingredient: str | None = Field(default=None, min_length=1, max_length=500)
    cuisine: str | None = Field(default=None, min_length=1, max_length=120)

@app.get("/api/ingredients")
def supported_ingredients():
    return {"ingredients": [key.replace('_', ' ') for key in METHODS],
            "additional_ingredients": [key.replace('_', ' ') for key in EXTRAS],
            "cuisines": list(STYLES), "model": MODEL_ID,
            "max_ingredients": 8, "max_cuisines": 3}

@app.post("/api/generate")
def generate(request: GenerationRequest):
    if (request.q is None) == (request.main_ingredient is None):
        raise HTTPException(status_code=422, detail="Provide either q or main_ingredient, containing ingredients + cuisine.")
    try:
        dishes = generate_dishes(engine, request.q if request.q is not None else request.main_ingredient, request.cuisine)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"recipes": dishes, "count": len(dishes), "model": MODEL_ID,
            "detected_cuisine": ', '.join(dish['cuisine'] for dish in dishes),
            "matched_canonical_ingredients": [key.replace('_', ' ') for key in dishes[0]['requested_ingredients']]}

@app.get("/api/search")
def search(
    q: str = Query(..., description="Query ingredients and regional cuisine"),
    cuisine: str = Query(None),
    top_k: int = Query(24, ge=1, le=100),
    include_generated: bool = Query(True)
):
    if not recipe_index:
        raise HTTPException(status_code=503, detail="Recipe search is unavailable. Run indexer.py to build the index; main-ingredient generation is still available.")

    pole_key, detected_profile = detect_cuisine_from_query(q)
    if not pole_key and cuisine:
        pole_key, detected_profile = detect_cuisine_from_query(cuisine)

    try:
        canonical_tokens, _ = parse_query(q, cuisine)
    except ValueError:
        # Collection search also accepts free text beyond the generation catalog.
        canonical_tokens = engine.extract_canonical_ingredients(q)
    query_vec = engine.encode_ingredient_list(canonical_tokens)

    pole_vec = None
    if pole_key:
        pole_vec = engine.get_pole_vector(pole_key)
        if pole_vec is not None and np.linalg.norm(query_vec) > 0:
            query_vec = engine.slerp(query_vec, pole_vec, theta_deg=35.0)
        elif pole_vec is not None:
            query_vec = pole_vec

    query_vec = query_vec.reshape(1, -1)
    faiss.normalize_L2(query_vec)

    scores, indices = recipe_index.search(query_vec, top_k)

    results = []
    generation_warning = None

    # 1. Prepend AI dish synthesized for the specific regional cuisine
    if include_generated:
        try:
            results.extend(generate_dishes(engine, q, cuisine))
        except ValueError as exc:
            generation_warning = str(exc)

    # 2. Append dataset retrieved dishes
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(recipe_metadata):
            continue
        item = recipe_metadata[idx]
        flavour_match_pct = round(max(float(score), 0.0) * 100, 1)

        results.append({
            "id": int(idx),
            "title": item.get("title", "Untitled Recipe"),
            "is_generated": False,
            "flavour_match_score": flavour_match_pct,
            "flavour_notes": [f.replace("_", " ") for f in item.get("canonical_flavours", [])[:5]],
            "ingredients": item.get("ingredients", []),
            "directions": item.get("directions", []),
            "cuisine": item.get("cuisine", "Indian"),
            "prep_time": item.get("prep_time", 30),
            "diet": item.get("diet", "Vegetarian")
        })

    return {
        "query": q,
        "generation_warning": generation_warning,
        "detected_cuisine": detected_profile["label"] if detected_profile else "General Indian",
        "matched_canonical_ingredients": [t.replace("_", " ") for t in canonical_tokens],
        "count": len(results),
        "recipes": results
    }

app.mount("/", StaticFiles(directory=str(BASE_DIR.parent / "frontend"), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
