"""Verifica HTTP real em um Uvicorn temporário e salva evidência local."""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrieval", action="store_true", help="Também verifica modelo e índice reais.")
    args = parser.parse_args()
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    opener = build_opener(ProxyHandler({}))

    def request(path, payload=None, timeout=2):
        data = json.dumps(payload).encode() if payload is not None else None
        req = Request(base + path, data=data, headers={"Content-Type": "application/json"})
        with opener.open(req, timeout=timeout) as response:
            return response.status, response.read()

    with (reports / "uvicorn.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT, stdout=log, stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            for _ in range(80):
                if process.poll() is not None:
                    raise RuntimeError("Uvicorn terminou antes de iniciar; consulte reports/uvicorn.log.")
                try:
                    status, body = request("/health")
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Tempo esgotado ao iniciar a API.")
            health = json.loads(body)
            assert status == 200 and health["status"] == "ok"
            status, schema = request("/openapi.json")
            assert status == 200 and "/simulate" in json.loads(schema)["paths"]
            assert request("/docs")[0] == 200
            status, body = request("/simulate", {
                "base_amount": "100.00", "current_rate_percent": "10", "proposed_rate_percent": "15",
            })
            result = json.loads(body)
            assert status == 200 and result["tax_difference"] == "5.00"
            report = {
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "transport": "HTTP sobre loopback, Uvicorn em subprocesso temporário",
                "checks": {"health": "passed", "openapi": "passed", "docs": "passed", "simulate": "passed"},
                "simulation": result,
            }
            if args.retrieval:
                status, body = request("/sources")
                sources = json.loads(body)
                assert status == 200 and sources["index_status"] == "validated"
                assert len(sources["sources"]) == 3
                status, body = request("/search", {
                    "question": "O que é a CBS e de quem é sua competência?", "top_k": 5,
                }, timeout=30)
                search = json.loads(body)
                assert status == 200 and len(search["results"]) == 5
                assert all(hit["url"].startswith("https://") and hit["text"] for hit in search["results"])
                assert any("CBS" in hit["text"] for hit in search["results"])
                assert "answer" not in search and "não é" in search["notice"]
                report.update({"sources": sources, "search": search})
                report["checks"].update({"sources": "passed", "semantic_search_real_model": "passed"})
            destination = "retrieval-api-smoke.json" if args.retrieval else "api-smoke.json"
            (reports / destination).write_text(
                json.dumps(report, ensure_ascii=False, indent=2), "utf-8"
            )
            print("HTTP real: /health, /openapi.json, /docs e /simulate aprovados.")
            if args.retrieval:
                print("HTTP real: /sources e /search com embeddings ONNX aprovados.")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
