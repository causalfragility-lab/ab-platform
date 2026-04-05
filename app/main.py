from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import engine
from app.db.models import Base
from app.api import experiments, assignment, results

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="A/B Platform",
    description="Interpretable, reproducible, robustness-aware experimentation platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(experiments.router)
app.include_router(assignment.router)
app.include_router(results.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
