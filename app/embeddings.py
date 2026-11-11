"""Inferência E5 local com ONNX quantizado, pooling por máscara e normalização L2."""

import argparse
import hashlib
import json
import threading
from pathlib import Path

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL_CONFIG = ROOT / "config/embedding_model.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def model_spec() -> dict:
    return json.loads(MODEL_CONFIG.read_text("utf-8"))


def model_fingerprint(spec: dict) -> str:
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()


def model_directory(spec: dict) -> Path:
    return ROOT / "data/models" / spec["revision"]


def download_model() -> None:
    spec = model_spec()
    folder = model_directory(spec)
    folder.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for name, details in spec["files"].items():
            destination = folder / name
            if destination.exists() and sha256_file(destination) == details["sha256"]:
                print(f"Cache verificado: {name}", flush=True)
                continue
            url = f"https://huggingface.co/{spec['model_id']}/resolve/{spec['revision']}/{details['remote_path']}"
            temporary = destination.with_suffix(destination.suffix + ".part")
            print(f"Baixando {name}: {details['bytes']} bytes", flush=True)
            with client.stream("GET", url) as response:
                response.raise_for_status()
                with temporary.open("wb") as output:
                    for block in response.iter_bytes(1024 * 1024):
                        output.write(block)
            if temporary.stat().st_size != details["bytes"] or sha256_file(temporary) != details["sha256"]:
                raise ValueError(f"Integridade inválida: {name}; modelo anterior preservado.")
            temporary.replace(destination)
            print(f"SHA-256 verificado: {name}", flush=True)


def mean_pool(hidden: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
    mask = attention_mask[..., None].astype(np.float32)
    pooled = (hidden * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1)
    norms = np.linalg.norm(pooled, axis=1, keepdims=True)
    if np.any(norms == 0) or not np.isfinite(pooled).all():
        raise ValueError("O modelo produziu embeddings inválidos.")
    return (pooled / norms).astype(np.float32)


class E5Embedder:
    def __init__(self):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.spec = model_spec()
        folder = model_directory(self.spec)
        for name, details in self.spec["files"].items():
            path = folder / name
            if not path.exists() or sha256_file(path) != details["sha256"]:
                raise ValueError("Modelo ausente ou inválido. Execute python -m app.embeddings download.")
        self.tokenizer = Tokenizer.from_file(str(folder / "tokenizer.json"))
        self.tokenizer.no_truncation()
        self.tokenizer.enable_padding(pad_id=1, pad_token="<pad>")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        options.enable_cpu_mem_arena = False
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        self.session = ort.InferenceSession(
            str(folder / "model.onnx"), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.input_names = {item.name for item in self.session.get_inputs()}
        self.lock = threading.Lock()

    def encode(self, texts: list[str], kind: str) -> np.ndarray:
        if kind not in {"query", "passage"} or not texts:
            raise ValueError("Use query ou passage e ao menos um texto.")
        vectors = []
        with self.lock:
            for text in texts:
                encoding = self.tokenizer.encode(self.spec["prefixes"][kind] + text)
                if len(encoding.ids) > self.spec["max_tokens"]:
                    raise ValueError("Texto excede 512 tokens; reduza o tamanho do trecho ou da pergunta.")
                feeds = {
                    "input_ids": np.asarray([encoding.ids], dtype=np.int64),
                    "attention_mask": np.asarray([encoding.attention_mask], dtype=np.int64),
                    "token_type_ids": np.asarray([encoding.type_ids], dtype=np.int64),
                }
                outputs = self.session.run(None, {k: v for k, v in feeds.items() if k in self.input_names})
                vectors.append(mean_pool(outputs[0], feeds["attention_mask"])[0])
        result = np.asarray(vectors, dtype=np.float32)
        if result.shape[1] != self.spec["dimensions"]:
            raise ValueError("Dimensão de embeddings incompatível com o modelo registrado.")
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["download"])
    parser.parse_args()
    download_model()


if __name__ == "__main__":
    main()
