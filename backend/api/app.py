from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware

from application.runner import run_pipeline

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
async def analyze(body: dict | None = Body(None)):
    use_web_retrieval = body.get("use_web_retrieval", False) if body else False
    report = run_pipeline(docs_dir=None, use_web_retrieval=use_web_retrieval)
    return {"report": report}
