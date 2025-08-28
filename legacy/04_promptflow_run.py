import subprocess
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
import argparse

# === CONFIGURACIÓN ===
FLOW_DIR = "/home/matias/Documents/media_monitor/flow"
# DATA_FILE = "/home/matias/Documents/media_monitor/data/digest_jsonls/20250611T04.jsonl"
RUNS_DIR = Path.home() / ".promptflow/.runs"
OUTPUT_DIR = Path("./data/pf_out")
JSONL_BASE_DIR = Path("./data/digest_jsonls")

def run_promptflow(flow_dir, data_file):
    cmd = [
        "python", "-m", "promptflow._cli.pf", "run", "create",
        "--flow", str(flow_dir),
        "--data", str(data_file)
    ]
    print("\n🔁 Ejecutando PromptFlow...\n")
    print(" ".join(cmd))
    print("\n───────────── PromptFlow output ─────────────")
    try:
        subprocess.run(cmd, check=True)  # Muestra output en tiempo real
    except KeyboardInterrupt:
        print("\n⛔ Ejecución interrumpida por el usuario.")
        exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ PromptFlow falló con código {e.returncode}")
        exit(1)
    print("───────────── Fin PromptFlow output ─────────────\n")

def get_latest_output_file(runs_dir):
    candidates = list(runs_dir.glob("flow_variant_0_*/flow_outputs/output.jsonl"))
    if not candidates:
        raise FileNotFoundError("❌ No se encontró ningún output.jsonl.")
    latest = max(candidates, key=os.path.getmtime)
    return latest

def load_output_jsonl(path):
    print(f"📥 Cargando resultados desde: {path}")
    return pd.read_json(path, lines=True)

def save_output(df, base_name, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%H%M%S")
    out_path = output_dir / f"pfout_{base_name}_{timestamp}.jsonl"
    df.to_json(out_path, orient="records", lines=True, force_ascii=False)
    print(f"✅ Guardado en {out_path}")
    return out_path

# # === MAIN ===
# if __name__ == "__main__":
#     run_promptflow(FLOW_DIR, DATA_FILE)
#     output_file = get_latest_output_file(RUNS_DIR)
#     df = load_output_jsonl(output_file)
#     print("✅ Primeras filas del output:")
#     print(df.head(3).to_string(index=False))
#     save_output(df, DATA_FILE, OUTPUT_DIR)

import sys

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--digest-id", required=True, help="Digest ID in format YYYYMMDDTHH")
    args = parser.parse_args()


    data_file = JSONL_BASE_DIR / f"{args.digest_id}.jsonl"
    if not data_file.exists():
        print(f"⚠️ No se encontró el archivo {data_file}. Saltando PromptFlow.")
        sys.exit(0)  # ← No es un error, simplemente no hay datos que procesar


    run_promptflow(FLOW_DIR, data_file)
    output_file = get_latest_output_file(RUNS_DIR)
    df = load_output_jsonl(output_file)
    print("✅ Primeras filas del output:")
    print(df.head(3).to_string(index=False))
    save_output(df, args.digest_id, OUTPUT_DIR)