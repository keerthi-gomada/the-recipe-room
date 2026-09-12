# Epicure Recipe Room

Installable web app with a FastAPI backend and Epicure ingredient embeddings.

## Run

Requires Python 3.10 or newer. From the project directory:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend/requirements.txt
.venv\Scripts\python -m uvicorn app:app --app-dir backend --host 0.0.0.0 --port 8000
```

Open http://localhost:8000. The first launch downloads Epicure assets from Hugging Face and requires internet access. The included recipe index enables collection search. Generation works independently of that index.

## Generate a dish

Enter ingredients and cuisines separated by `+`, then select **Generate dishes** or press Enter:

- `paneer + spinach + north indian`
- `rice + potatoes + south indian`
- `chicken + garlic + chettinad`
- `tofu + mushroom + chinese + thai` — creates two dishes, one for each cuisine.

Use up to 8 distinct ingredients and 3 cuisines. With no cuisine, generation defaults to Indian style. Duplicates and common plural spellings are normalized. Every accepted ingredient is included; unsupported terms and empty `+` segments produce HTTP 422 instead of being silently discarded. The expandable list in the app shows the supported mains, additions and 17 cuisines. Chickpeas must be cooked/canned, chicken must be boneless, and rice uses basmati.

The backend loads [Kaikaku/epicure-core](https://huggingface.co/Kaikaku/epicure-core), the blended chemistry/context embedding model. It averages all requested ingredient vectors, steers toward an existing cuisine macro-region pole, and ranks seasonings from a compatible regional pool. Indian regions use `cuisine:South_Asian`; Chinese, Thai, Italian, Continental and Mexican styles use their corresponding available macro-region poles. Regional cooking profiles provide the finer distinctions in tempering, sauces and finishing ingredients.

Ingredient-specific cooking plans provide measured quantities, heat settings, timing and doneness cues for two servings. Components are cooked separately before combining, so rice, roots, leafy greens and chicken receive appropriate methods. This is algorithmic generation, not a text-generating language model, and recipes have not been kitchen-tested. Generated dishes have no fabricated confidence percentage. The response includes the model ID, actual cuisine pole, requested ingredients and selected seasonings.

## Install

Use the **Install app** button when offered by your browser, or the browser’s installation menu. On iPhone/iPad, use Safari → Share → Add to Home Screen. The app opens in its own window. On a deployed host, HTTPS is required for installation and service workers; localhost is supported for development. Serve frontend and API together with the command above. A phone accessing a plain HTTP LAN address will not get install/offline functionality.

This is a progressive web app, not an App Store/Play Store binary. Recipe generation and search require the running backend. An offline page is available after the first online visit. The current frontend also uses hosted Tailwind, icons and fonts.

## API

- `GET /api/ingredients`: supported mains, additions, cuisines, model ID and input limits.
- `POST /api/generate` with JSON `{"q":"paneer + spinach + north indian"}`: generated dishes, one per requested cuisine. An optional `cuisine` field can also contain styles separated by `+`.
- Legacy `{"main_ingredient":"potato","cuisine":"north indian"}` remains supported; send either `q` or `main_ingredient`, not both.
- `GET /api/search?q=rice&include_generated=false`: collection search.

Run backend tests with `python -m unittest discover -s backend -p "test_*.py"`.
