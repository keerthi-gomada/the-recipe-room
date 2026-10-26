from collection_search import CollectionSearch, ingredient_catalog
from pantry import pantry_groups
import csv
import json
import re
import faiss
import numpy as np
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from generation import generate_dishes, parse_query, METHODS, EXTRAS, STYLES, MODEL_ID, DuplicateIngredientError
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

# Recover yields for older index metadata without rebuilding model embeddings.
serving_lookup = {}
if (BASE_DIR / "IndianFoodDatasetCSV.csv").exists():
    with (BASE_DIR / "IndianFoodDatasetCSV.csv").open(encoding="utf-8-sig", newline="") as dataset:
        for row in csv.DictReader(dataset):
            title = (row.get("TranslatedRecipeName") or row.get("RecipeName") or "").strip()
            try:
                count = int(row["Servings"])
            except (ValueError, KeyError):
                continue
            if count > 0:
                serving_lookup.setdefault(title, set()).add(count)

# Supplement search with the uploaded dataset's actual ingredient columns.
pantry_rows = []
if (BASE_DIR / 'pantry_dataset.json').exists():
    pantry_rows = json.loads((BASE_DIR / 'pantry_dataset.json').read_text(encoding='utf-8'))
    by_title = {row['title'].strip().casefold(): row for row in recipe_metadata}
    for row in pantry_rows:
        existing = by_title.get(row['title'].strip().casefold())
        if existing is not None:
            existing.setdefault('cleaned_ingredients', []).extend(row['cleaned_ingredients'])
collection_search = CollectionSearch(recipe_metadata)
collection_ingredients = ingredient_catalog([*recipe_metadata, *pantry_rows])

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

class ScanRequest(BaseModel):
    image: str = Field(min_length=1, max_length=12_000_000)

def canonical_pantry_names():
    names=set(collection_ingredients)
    for group in pantry_groups([*collection_ingredients,*METHODS,*EXTRAS]):
        names.update(group['ingredients'])
    return sorted(names)

@app.post('/api/scan')
def scan_ingredients(request: ScanRequest):
    """Identify visible pantry ingredients using a configured vision endpoint."""
    import os
    import base64
    import urllib.request
    from urllib.error import URLError, HTTPError
    endpoint=os.getenv('OPENAI_BASE_URL','https://api.openai.com/v1').rstrip('/')+'/chat/completions'
    api_key=os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise HTTPException(status_code=503,detail='Photo scanning is not configured on the recipe server yet.')
    if not request.image.startswith('data:image/') or ',' not in request.image:
        raise HTTPException(status_code=422,detail='Upload a valid image to scan.')
    mime,encoded=request.image.split(',',1)
    media_type=mime.removeprefix('data:').removesuffix(';base64')
    try:
        base64.b64decode(encoded,validate=True)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail='The selected image could not be read.') from exc
    allowed=canonical_pantry_names()
    payload={'model':os.getenv('VISION_MODEL','gpt-4o-mini'),'temperature':0,
      'response_format':{'type':'json_object'},
      'messages':[{'role':'system','content':'Identify only ingredients clearly visible in the image. Return JSON {"ingredients":[...]} with names selected only from the provided pantry catalog. Do not infer hidden items, packaging brands, or cookware.'},
        {'role':'user','content':[{'type':'text','text':'Match visible ingredients to this catalog. Return at most 30 distinct names: '+', '.join(allowed)},
         {'type':'image_url','image_url':{'url':request.image,'detail':'high'}}]}]}
    req=urllib.request.Request(endpoint,data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+api_key,'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=50) as response: result=json.loads(response.read())
        content=result['choices'][0]['message']['content']
        found=json.loads(content).get('ingredients',[])
    except (HTTPError,URLError,TimeoutError,KeyError,IndexError,ValueError) as exc:
        raise HTTPException(status_code=502,detail='Ingredient recognition failed. Try another photo.') from exc
    allowed_lookup={name.casefold():name for name in allowed}
    cleaned=list(dict.fromkeys(allowed_lookup[str(name).casefold()] for name in found if str(name).casefold() in allowed_lookup))
    return {'ingredients':cleaned}

@app.get("/api/ingredients")
def supported_ingredients():
    return {"ingredients": [key.replace('_', ' ') for key in METHODS],
            "additional_ingredients": [key.replace('_', ' ') for key in EXTRAS],
            "cuisines": list(STYLES), "model": MODEL_ID,
            "collection_ingredients": collection_ingredients,
            "pantry_groups": pantry_groups([*collection_ingredients, *METHODS, *EXTRAS]),
            "max_ingredients": 8, "max_cuisines": 3}

@app.post("/api/generate")
def generate(request: GenerationRequest):
    if (request.q is None) == (request.main_ingredient is None):
        raise HTTPException(status_code=422, detail="Provide either q or main_ingredient, containing ingredients + cuisine.")
    try:
        dishes = generate_dishes(engine, request.q if request.q is not None else request.main_ingredient, request.cuisine)
    except DuplicateIngredientError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        if not str(exc).startswith(('Unsupported ingredients', 'Add at least one main ingredient')):
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        result = search(q=request.q or request.main_ingredient, cuisine=request.cuisine,
                        top_k=24, include_generated=False)
        result['message'] = ('Showing matching collection recipes for these ingredients.' if result['recipes']
                             else 'No collection recipe matches all these ingredients. Try fewer ingredients.')
        return result
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
    except DuplicateIngredientError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
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

    semantic_scores = {int(idx): float(score) for idx, score in zip(indices[0], scores[0])}
    collection_ids = collection_search.rank(q, STYLES, indices[0], top_k)

    results = []
    generation_warning = None

    # 1. Prepend AI dish synthesized for the specific regional cuisine
    if include_generated:
        try:
            results.extend(generate_dishes(engine, q, cuisine))
        except ValueError as exc:
            generation_warning = str(exc)

    # 2. Append dataset retrieved dishes
    for idx in collection_ids:
        score = semantic_scores.get(int(idx))
        if idx < 0 or idx >= len(recipe_metadata):
            continue
        item = recipe_metadata[idx]
        flavour_match_pct = round(max(float(score), 0.0) * 100, 1) if score is not None else None

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
            "servings": item.get("servings") or (next(iter(serving_lookup[item.get("title", "")])) if len(serving_lookup.get(item.get("title", ""), set())) == 1 else None),
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

@app.get('/api/scan-recipes')
def scan_recipes(q: str = Query(..., min_length=1, max_length=500)):
    """Return collection recipes containing at least two recognized query ingredients."""
    if not recipe_index:
        raise HTTPException(status_code=503,detail='Recipe search is unavailable.')
    try:
        canonical_tokens,_=parse_query(q)
    except (ValueError,DuplicateIngredientError):
        canonical_tokens=engine.extract_canonical_ingredients(q)
    canonical_tokens=[token for token in canonical_tokens if token in METHODS or token in EXTRAS]
    if not canonical_tokens:
        return {'recipes':[],'matched_ingredients':[]}
    query_vec=engine.encode_ingredient_list(canonical_tokens).reshape(1,-1)
    faiss.normalize_L2(query_vec)
    _,indices=recipe_index.search(query_vec,min(100,recipe_index.ntotal))
    candidates=collection_search.rank(q,STYLES,indices[0],min(100,recipe_index.ntotal))
    results=[]
    for idx in candidates:
        if idx<0 or idx>=len(recipe_metadata):continue
        item=recipe_metadata[idx]
        ingredient_text=' '.join(item.get('ingredients',[]))
        present=set(engine.extract_canonical_ingredients(ingredient_text))
        overlap=[name for name in canonical_tokens if name in present]
        if len(overlap)<min(2,len(canonical_tokens)):continue
        results.append({'id':int(idx),'title':item.get('title','Untitled recipe'),'is_generated':False,
          'ingredients':item.get('ingredients',[]),'directions':item.get('directions',[]),'cuisine':item.get('cuisine','Indian'),
          'prep_time':item.get('prep_time',30),'servings':item.get('servings'),'diet':item.get('diet','Vegetarian'),
          'matched_ingredients':[name.replace('_',' ') for name in overlap]})
        if len(results)>=24:break
    return {'recipes':results,'matched_ingredients':[name.replace('_',' ') for name in canonical_tokens]}

app.mount("/", StaticFiles(directory=str(BASE_DIR.parent / "frontend"), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
