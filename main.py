"""
AfCEN Venture Platform — Main Entry Point

Run with: uvicorn main:app --reload
Docs at:  http://localhost:8000/docs
UI  at:   http://localhost:8000/
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database import engine, Base
from app.routes import builders_router, intake_router, ventures_router, approvals_router

# Create all tables on startup if they don't exist
Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")

app = FastAPI(
    title="AfCEN Venture Platform",
    description="Agentic venture operating platform for African builders.",
    version="1.0.0",
)

# Register all routes
app.include_router(builders_router)
app.include_router(intake_router)
app.include_router(ventures_router)
app.include_router(approvals_router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def ui(request: Request):
    """Serve the chat UI"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
