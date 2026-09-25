import json
import numpy as np
import pandas as pd
import faiss
from epicure_engine import EpicureEngine

CSV_PATH = "IndianFoodDatasetCSV.csv"
INDEX_FILE = "recipe_faiss.index"
META_FILE = "recipes_metadata.json"

print(f"[*] Reading {CSV_PATH}...")
df = pd.read_csv(CSV_PATH)

# Prefer English translated fields, fallback to original if missing
df['title'] = df['TranslatedRecipeName'].fillna(df['RecipeName'])
df['raw_ingredients'] = df['TranslatedIngredients'].fillna(df['Ingredients'])
df['raw_instructions'] = df['TranslatedInstructions'].fillna(df['Instructions'])
df['cuisine_tag'] = df['Cuisine'].fillna('Indian')
df['prep_time'] = df['TotalTimeInMins'].fillna(df['PrepTimeInMins'].fillna(30))

df = df.dropna(subset=['title', 'raw_ingredients', 'raw_instructions'])

engine = EpicureEngine(repo_id="Kaikaku/epicure-core")

print(f"[*] Extracting canonical ingredients & computing embeddings for {len(df)} recipes...")

recipe_vectors = []
valid_metadata = []

for count, (idx, row) in enumerate(df.iterrows(), 1):
    ing_text = str(row['raw_ingredients'])
    
    # 1. Parse ingredients into list by comma split
    ing_list = [i.strip() for i in ing_text.split(',') if i.strip()]
    
    # 2. Extract canonical ingredients recognized by Epicure-Core
    canonical_ings = engine.extract_canonical_ingredients(ing_text)
    
    # 3. Compute 300-D flavor embedding vector
    vec = engine.encode_ingredient_list(canonical_ings)
    
    if np.linalg.norm(vec) > 0:
        recipe_vectors.append(vec)
        
        # Split instructions into readable steps
        steps = [s.strip() for s in str(row['raw_instructions']).replace('\n', '. ').split('. ') if len(s.strip()) > 5]
        
        valid_metadata.append({
            "title": str(row['title']).strip(),
            "ingredients": ing_list,
            "directions": steps if steps else [str(row['raw_instructions'])],
            "cuisine": str(row['cuisine_tag']).strip(),
            "prep_time": int(row['prep_time']) if pd.notnull(row['prep_time']) else 30,
            "diet": str(row.get('Diet', 'Vegetarian')),
            "canonical_flavours": canonical_ings
        })

    if count % 1000 == 0 or count == len(df):
        print(f" -> Processed {count:,}/{len(df):,} recipes ({(count/len(df))*100:.1f}%)")

print("[*] Normalizing vectors and building FAISS index...")
recipe_vectors = np.array(recipe_vectors, dtype=np.float32)
faiss.normalize_L2(recipe_vectors)

dimension = recipe_vectors.shape[1]
index = faiss.IndexFlatIP(dimension)
index.add(recipe_vectors)

print(f"[*] Saving FAISS index with {index.ntotal} items to {INDEX_FILE}...")
faiss.write_index(index, INDEX_FILE)

print(f"[*] Saving metadata to {META_FILE}...")
with open(META_FILE, "w", encoding="utf-8") as f:
    json.dump(valid_metadata, f)

print(f"[✓] Complete! Successfully indexed {len(valid_metadata)} Indian recipes.")