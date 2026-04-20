import json
import os
from typing import Dict, Any, List

DATA_DIR = "data"

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_json(filename: str) -> Dict[str, Any]:
    ensure_data_dir()
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(filename: str, data: Dict[str, Any]):
    ensure_data_dir()
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

