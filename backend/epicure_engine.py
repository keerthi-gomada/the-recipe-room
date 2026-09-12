import json
import re
import numpy as np
from huggingface_hub import hf_hub_download
from safetensors.numpy import load_file

class EpicureEngine:
    def __init__(self, repo_id: str = "Kaikaku/epicure-core"):
        print(f"[*] Downloading and caching assets from HF repo: {repo_id}")

        # 1. Load canonical vocabulary (1,790 items)
        vocab_file = hf_hub_download(repo_id=repo_id, filename="vocab.json")
        with open(vocab_file, "r", encoding="utf-8") as f:
            self.vocab = json.load(f)  # { "ingredient_name": id }

        # 2. Load itos (index-to-string)
        itos_file = hf_hub_download(repo_id=repo_id, filename="itos.json")
        with open(itos_file, "r", encoding="utf-8") as f:
            self.itos = json.load(f)

        # 3. Load 1790x300 Embedding Matrix
        weights_file = hf_hub_download(repo_id=repo_id, filename="embeddings.safetensors")
        tensors = load_file(weights_file)
        # Extract tensor (handles either 'embeddings' or the first available key)
        raw_embeddings = tensors.get("embeddings") if "embeddings" in tensors else list(tensors.values())[0]
        
        # Normalize embeddings to unit vectors for fast cosine similarity
        norms = np.linalg.norm(raw_embeddings, axis=1, keepdims=True)
        self.embeddings = raw_embeddings / np.maximum(norms, 1e-9)
        self.dim = self.embeddings.shape[1]

        # 4. Load Supervised Poles (Cuisine and flavor directions)
        poles_file = hf_hub_download(repo_id=repo_id, filename="supervised_poles.json")
        with open(poles_file, "r", encoding="utf-8") as f:
            self.poles = json.load(f)

        # 5. Build regex matcher for zero-shot text matching against canonical names
        # Sorting by length descending ensures multi-word ingredients (e.g. 'olive_oil') match first
        self.canonical_keys = sorted(list(self.vocab.keys()), key=len, reverse=True)
        escaped_terms = [re.escape(k.replace('_', ' ')) for k in self.canonical_keys]
        self._pattern = re.compile(r'\b(' + '|'.join(escaped_terms) + r')\b', re.IGNORECASE)

        print(f"[✓] Epicure-Core ready: {len(self.vocab)} ingredients, {len(self.poles)} directional poles.")

    def extract_canonical_ingredients(self, text: str) -> list[str]:
        """Extracts canonical ingredients directly from arbitrary recipe text or user queries."""
        matches = self._pattern.findall(text.lower())
        # Deduplicate and format to vocabulary key style (underscores)
        return list(dict.fromkeys(m.strip().replace(' ', '_') for m in matches if m.strip()))

    def get_ingredient_vector(self, ingredient: str) -> np.ndarray | None:
        key = ingredient.lower().strip().replace(' ', '_')
        if key in self.vocab:
            return self.embeddings[self.vocab[key]]
        return None

    def encode_ingredient_list(self, ingredients: list[str]) -> np.ndarray:
        """Computes the aggregate centroid vector from a list of ingredient keys."""
        vecs = [self.get_ingredient_vector(ing) for ing in ingredients if self.get_ingredient_vector(ing) is not None]
        if not vecs:
            return np.zeros(self.dim, dtype=np.float32)
        
        centroid = np.mean(vecs, axis=0)
        norm = np.linalg.norm(centroid)
        return (centroid / (norm + 1e-9)).astype(np.float32)

    def slerp(self, vec_a: np.ndarray, vec_b: np.ndarray, theta_deg: float = 25.0) -> np.ndarray:
        """Spherical Linear Interpolation to steer embedding towards a cuisine pole vector."""
        theta = np.radians(max(0.0, theta_deg))
        dot = np.clip(np.dot(vec_a, vec_b), -1.0, 1.0)
        omega = np.arccos(dot)
        if np.abs(omega) < 1e-6:
            return vec_a
        # Steer toward the pole without overshooting it for nearby vectors.
        theta = min(theta, omega)
        if np.abs(np.pi - omega) < 1e-6:
            # Opposite vectors do not define a unique great circle.
            return vec_a
        sin_omega = np.sin(omega)
        steered = (np.sin((1.0 - theta / omega) * omega) / sin_omega) * vec_a + (np.sin(theta) / sin_omega) * vec_b
        return (steered / (np.linalg.norm(steered) + 1e-9)).astype(np.float32)

    def get_pole_vector(self, pole_name: str) -> np.ndarray | None:
        if pole_name in self.poles:
            vec = np.array(self.poles[pole_name], dtype=np.float32)
            return vec / (np.linalg.norm(vec) + 1e-9)
        return None
