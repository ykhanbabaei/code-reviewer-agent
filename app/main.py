import sys

import uvicorn
from fastapi import FastAPI
import logging
from dotenv import load_dotenv
from github import GithubException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from fastapi import Request

load_dotenv()

from app.config import settings

logging.basicConfig(
    level=settings.monitoring.log_level,
    handlers=[
        logging.FileHandler(settings.monitoring.log_file),
        logging.StreamHandler(sys.stdout)
    ]
)


app = FastAPI()

# Security note: Allowing all origins is not recommended for production environments. Adjust as necessary.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins - NOT for production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.review_routes import router
app.include_router(router)

@app.get("/")
async def health_check():
    return {"status": "ok"}

@app.exception_handler(GithubException)
async def github_exception_handler(
    request: Request,
    exc: GithubException,
):
    return JSONResponse(
        status_code=exc.status or 500,
        content={
            "detail": exc.data.get("message", str(exc))
        },
    )

# TODO 1. Fixing Security vulnerability of allowing all origins in CORS middleware.
#      2. Add authentication and authorization to the API endpoints.
#      3. Rate Limiter to prevent abuse. 

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)