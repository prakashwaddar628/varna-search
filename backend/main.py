import os
from fastapi import FastAPI, File, UploadFile, Form
from pydantic import BaseModel
from typing import List, Optional
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import io
import time

app = FastAPI(title="Varna-Search CLIP Backend")

# ---------------------------------------------------------------------------
# 1. Load CLIP Model (Done once on startup)
# ---------------------------------------------------------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Loading CLIP model on {device}...")

model_id = "openai/clip-vit-base-patch32"
model = CLIPModel.from_pretrained(model_id).to(device)
processor = CLIPProcessor.from_pretrained(model_id)

# ---------------------------------------------------------------------------
# 2. In-Memory Vector Store / Cache
# ---------------------------------------------------------------------------
# In a production app, use LanceDB, Chroma, or ObjectBox.
# For this Varna-Search phase, we hold indexed vectors in memory.
indexed_images = []  # List of dicts: {"path": str, "embedding": torch.Tensor, "filename": str}

# ---------------------------------------------------------------------------
# API Models
# ---------------------------------------------------------------------------
class IndexRequest(BaseModel):
    folder_path: str

class SearchResult(BaseModel):
    path: str
    filename: str
    score: float

# ---------------------------------------------------------------------------
# Helper: Computes embedding for a single PIL image
# ---------------------------------------------------------------------------
def get_image_embedding(image: Image.Image) -> torch.Tensor:
    inputs = processor(images=image, return_tensors="pt").to(device)
    with torch.no_features():
        embeddings = model.get_image_features(**inputs)
    # Normalize the embedding for cosine similarity math
    embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
    return embeddings

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/index_folder")
def index_folder(request: IndexRequest):
    global indexed_images
    folder = request.folder_path
    
    if not os.path.exists(folder):
        return {"error": f"Directory not found: {folder}"}
        
    print(f"Indexing folder: {folder}")
    indexed_images.clear() # Reset cache
    
    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    
    count = 0
    start_time = time.time()
    
    for root, _, files in os.walk(folder):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in valid_extensions:
                path = os.path.join(root, file)
                try:
                    # Open and process
                    img = Image.open(path).convert("RGB")
                    embedding = get_image_embedding(img)
                    
                    indexed_images.append({
                        "path": path,
                        "filename": file,
                        "embedding": embedding.cpu() # Store on CPU RAM to save VRAM
                    })
                    count += 1
                except Exception as e:
                    print(f"Failed to process {path}: {e}")
                    
    duration = time.time() - start_time
    print(f"Indexed {count} images in {duration:.2f}s")
    
    return {"status": "success", "count": count, "duration_seconds": duration}


@app.post("/search_image", response_model=List[SearchResult])
async def search_image(
    file: UploadFile = File(...),
    limit: int = Form(10)
):
    global indexed_images
    
    if not indexed_images:
        return [] # Nothing indexed
        
    # Read query image bytes
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    
    # 1. Compute query vector
    query_embedding = get_image_embedding(image).cpu()
    
    # 2. Compute cosine similarity against all cached vectors
    results = []
    
    for item in indexed_images:
        target_embedding = item["embedding"]
        # Cosine similarity is dot product of normalized vectors
        similarity = torch.nn.functional.cosine_similarity(query_embedding, target_embedding).item()
        
        results.append({
            "path": item["path"],
            "filename": item["filename"],
            "score": similarity
        })
        
    # 3. Sort by highest score first
    results.sort(key=lambda x: x["score"], reverse=True)
    
    # 4. Slice to the match limit
    return results[:limit]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
