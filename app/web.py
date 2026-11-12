"""Serve somente o frontend compilado, depois das rotas da API."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.ingestion import ROOT


def mount_frontend(application: FastAPI, directory: Path = ROOT / "frontend/dist") -> bool:
    if not (directory / "index.html").is_file():
        return False
    application.mount("/", StaticFiles(directory=directory, html=True), name="frontend")
    return True
