from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ws.router import router as ws_router

app = FastAPI(title="IncluSpeech")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
