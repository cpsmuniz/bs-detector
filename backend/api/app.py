from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from application.analyze_docs import analyze_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
async def analyze():
    return analyze_documents()
