# common.py — tutto il codice condiviso del progetto in un unico modulo
from dataclasses import dataclass, field
from typing import Optional, Literal
import random, hashlib, time, statistics, json
import numpy as np
import pandas as pd

# ============================================================
# 1) CONTRATTO DI INTERFACCIA
# ============================================================
Verdict = Literal["safe", "unsafe"]

@dataclass
class ClassificationResult:
    verdict: Verdict
    score: float
    latency_ms: float
    matched_rule: Optional[str] = None
    raw: dict = field(default_factory=dict)

class Defense:
    name: str = "base"
    def classify(self, response_text: str) -> ClassificationResult:
        raise NotImplementedError

# ============================================================
# 2) UTILITY
# ============================================================
def set_seed(seed: int = 42):
    random.seed(seed); np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass

def file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def benchmark_latency(fn, texts, repeats: int = 5, warmup: int = 10):
    for x in texts[:warmup]:
        fn(x)
    lat = []
    for x in texts:
        for _ in range(repeats):
            start = time.perf_counter()
            fn(x)
            lat.append((time.perf_counter() - start) * 1000)
    lat.sort()
    return {"n": len(lat), "median_ms": statistics.median(lat),
            "p95_ms": lat[int(0.95 * len(lat))], "min_ms": lat[0], "max_ms": lat[-1]}

# ============================================================
# 3) CARICAMENTO DEL CSV DELL'ARTICOLO  <-- la parte che combacia col CSV
# Colonne reali: Question, Behavior, Category, Question_Source,
#                Response, LLMs, Source_LLM, Noise, Human
# ============================================================
CSV_COLUMN_MAP = {
    "Response": "response_text",
    "Category": "category",
    "Behavior": "behavior",
    "Source_LLM": "source",          # "base" vs "xbreaking"
    "LLMs": "model",                 # es. "qwen3b"
    "Question": "question",
    "Question_Source": "question_source",
    "Noise": "noise",
}

def load_dataset_csv(path: str) -> pd.DataFrame:
    """Legge il CSV dell'articolo e normalizza nomi colonne + etichetta."""
    df = pd.read_csv(path, encoding='latin1')
    df = df.rename(columns=CSV_COLUMN_MAP)
    # etichetta: la colonna Human e' l'annotazione umana di dannosita'
    # 1 -> unsafe, 0 -> safe   (VERIFICA questa semantica sul paper!)
    df["ground_truth"] = df["Human"].map({1: "unsafe", 0: "safe"})
    # le risposte nel CSV hanno spazi iniziali/finali: ripuliscile
    df["response_text"] = df["response_text"].astype(str).str.strip()
    df = df.dropna(subset=["response_text", "ground_truth"]).reset_index(drop=True)
    return df

# ============================================================
# 4) SCHEMA DEL TEST SET GENERATO
# ============================================================
TEST_SET_FIELDS = {
    "id": str,                # identificativo univoco          
    "response_text": str,     # la risposta del modello da classificare
    "ground_truth": str,      # "safe" | "unsafe"
    "source": str,            # modello che l'ha generata, o "csv"
    "category": str,          # categoria di rischio (es. "economic_harm") 
    "obfuscation_level": int, # 0=esplicito ... 3=molto offuscato 
    "origin": str,            # "generated" | "csv"
}
VALID_VERDICTS = {"safe", "unsafe"}

def validate_record(rec: dict) -> list:
    errors = []
    for fld, typ in TEST_SET_FIELDS.items():
        if fld not in rec:
            errors.append(f"manca il campo '{fld}'")
        elif not isinstance(rec[fld], typ):
            errors.append(f"'{fld}' dovrebbe essere {typ.__name__}")
    if rec.get("ground_truth") not in VALID_VERDICTS:
        errors.append(f"ground_truth non valido: {rec.get('ground_truth')}")
    if rec.get("obfuscation_level") not in (0, 1, 2, 3):
        errors.append(f"obfuscation_level fuori range: {rec.get('obfuscation_level')}")
    return errors

def load_test_set(path: str) -> list:
    records = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            errs = validate_record(rec)
            if errs:
                raise ValueError(f"riga {i}: {errs}")
            records.append(rec)
    return records
