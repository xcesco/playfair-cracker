"""
Reporting and output generation.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import numpy as np

from .parallel import Result
from .preprocessing import format_matrix, matrix_to_list, ids_to_text
from .numba_core import (
    build_inverse_positions, decrypt_unique_pairs, rebuild_plain
)


def decrypt_with_key(
    cipher_data: tuple,
    key: np.ndarray,
) -> str:
    """
    Decrypt cipher text with a given key.

    Returns plaintext as string.
    """
    cipher_ids, cipher_pairs, cipher_pair_ids, unique_pair_ids, inverse_unique_index = cipher_data

    # Build inverse positions
    pos = np.empty(25, dtype=np.uint8)
    build_inverse_positions(key, pos)

    # Decrypt unique pairs
    decoded_unique = np.empty(len(unique_pair_ids), dtype=np.uint16)
    decrypt_unique_pairs(unique_pair_ids, key, pos, decoded_unique)

    # Rebuild plaintext
    plain = np.empty(len(cipher_ids), dtype=np.uint8)
    rebuild_plain(decoded_unique, inverse_unique_index, plain)

    return ids_to_text(plain)


def save_results(
    results: List[Result],
    output_dir: Path,
    cipher_data: tuple,
    core_data: Optional[tuple],
    mode: str,
    config_used: Dict,
):
    """
    Save results to output directory.

    Creates:
        - best_results.jsonl
        - best_plaintext.txt
        - best_key.txt
        - report.md
        - config_used.json
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Decrypt all results
    plaintexts = []
    for result in results:
        plaintext = decrypt_with_key(cipher_data, result.key)
        plaintexts.append(plaintext)

    # Decrypt core if available
    core_plaintexts = []
    if core_data is not None:
        for result in results:
            core_plaintext = decrypt_with_key(core_data, result.key)
            core_plaintexts.append(core_plaintext)

    # Save best_results.jsonl
    jsonl_path = output_dir / "best_results.jsonl"
    with open(jsonl_path, 'w') as f:
        for rank, (result, plaintext) in enumerate(zip(results, plaintexts), 1):
            record = {
                "rank": rank,
                "score": float(result.score),
                "key": result.key_string,
                "matrix": matrix_to_list(result.key),
                "plaintext": plaintext,
                "plaintext_preview": plaintext[:200] if len(plaintext) > 200 else plaintext,
                "mode": mode,
                "worker_id": result.worker_id,
                "restart_id": result.restart_id,
                "iters": result.iters,
                "seed": result.seed,
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    print(f"Saved results to {jsonl_path}")

    # Save best plaintext
    if plaintexts:
        best_plaintext_path = output_dir / "best_plaintext.txt"
        with open(best_plaintext_path, 'w') as f:
            f.write(plaintexts[0])
        print(f"Saved best plaintext to {best_plaintext_path}")

    # Save best key
    if results:
        best_key_path = output_dir / "best_key.txt"
        with open(best_key_path, 'w') as f:
            f.write(format_matrix(results[0].key))
        print(f"Saved best key to {best_key_path}")

    # Save config
    config_path = output_dir / "config_used.json"
    with open(config_path, 'w') as f:
        json.dump(config_used, f, indent=2)
    print(f"Saved config to {config_path}")

    # Generate report
    report_path = output_dir / "report.md"
    generate_report(
        report_path,
        results,
        plaintexts,
        core_plaintexts,
        mode,
        config_used,
    )
    print(f"Saved report to {report_path}")


def generate_report(
    report_path: Path,
    results: List[Result],
    plaintexts: List[str],
    core_plaintexts: List[str],
    mode: str,
    config_used: Dict,
):
    """Generate markdown report."""

    with open(report_path, 'w') as f:
        f.write("# Playfair Cracker Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Configuration\n\n")
        f.write(f"- **Mode:** {mode}\n")
        f.write(f"- **Workers:** {config_used.get('workers', 'N/A')}\n")
        f.write(f"- **Restarts:** {config_used.get('restarts', 'N/A')}\n")
        f.write(f"- **Iterations per restart:** {config_used.get('iters', 'N/A'):,}\n")
        f.write(f"- **Base seed:** {config_used.get('seed', 'N/A')}\n")
        f.write(f"- **Top-K:** {config_used.get('top_k', 'N/A')}\n\n")

        if 'cipher_file' in config_used:
            f.write("### Input Files\n\n")
            f.write(f"- **Cipher:** {config_used['cipher_file']}\n")
            if 'clean_cipher_file' in config_used:
                f.write(f"- **Clean cipher:** {config_used['clean_cipher_file']}\n")
            if 'core_file' in config_used:
                f.write(f"- **Core blocks:** {config_used['core_file']}\n")
            f.write(f"- **N-gram directory:** {config_used.get('ngram_dir', 'N/A')}\n\n")

        f.write("### Scoring Weights\n\n")
        f.write(f"- **w_full:** {config_used.get('w_full', 'N/A')}\n")
        f.write(f"- **w_core:** {config_used.get('w_core', 'N/A')}\n")
        f.write(f"- **w_tri:** {config_used.get('w_tri', 'N/A')}\n")
        f.write(f"- **w_inword:** {config_used.get('w_inword', 'N/A')}\n")
        f.write(f"- **w_letter:** {config_used.get('w_letter', 'N/A')}\n\n")

        f.write("## Top Results\n\n")

        n_show = min(10, len(results))
        f.write(f"### Top {n_show} Keys\n\n")

        for rank, result in enumerate(results[:n_show], 1):
            f.write(f"#### Rank {rank}\n\n")
            f.write(f"**Score:** {result.score:.4f}\n\n")
            f.write("**Key Matrix:**\n\n")
            f.write("```\n")
            f.write(format_matrix(result.key))
            f.write("\n```\n\n")

            f.write(f"**Key String:** `{result.key_string}`\n\n")

            plaintext = plaintexts[rank - 1]
            preview = plaintext[:300] if len(plaintext) > 300 else plaintext
            f.write("**Plaintext Preview:**\n\n")
            f.write(f"```\n{preview}\n```\n\n")

            if core_plaintexts and rank <= len(core_plaintexts):
                core_preview = core_plaintexts[rank - 1][:200] if len(core_plaintexts[rank - 1]) > 200 else core_plaintexts[rank - 1]
                f.write("**Core Blocks Decryption:**\n\n")
                f.write(f"```\n{core_preview}\n```\n\n")

            f.write("---\n\n")

        f.write("## Best Result Details\n\n")

        if results:
            f.write("### Full Plaintext\n\n")
            f.write("```\n")
            f.write(plaintexts[0])
            f.write("\n```\n\n")

            f.write("### Linguistic Plausibility\n\n")
            f.write("This plaintext should be evaluated for:\n\n")
            f.write("- Italian vocabulary and grammar\n")
            f.write("- Natural word boundaries\n")
            f.write("- Reasonable vowel/consonant distribution\n")
            f.write("- Common Italian endings and patterns\n\n")

        f.write("## Important Notes\n\n")
        f.write("⚠️ **Simulated Annealing is a probabilistic optimization method.**\n\n")
        f.write("- The results represent the most linguistically plausible decryptions found.\n")
        f.write("- There is no guarantee that the true plaintext has been recovered.\n")
        f.write("- Multiple runs with different parameters may yield different results.\n")
        f.write("- Human verification is essential for final validation.\n")
        f.write("- Consider running in `deep` mode for more thorough search.\n\n")

        f.write("## Recommendations\n\n")

        if mode == "fast":
            f.write("- Current mode: **fast** (exploratory)\n")
            f.write("- For production attack, consider running in **deep** mode\n")
            f.write("- Increase `--restarts` and `--iters` for better coverage\n\n")
        else:
            f.write("- Current mode: **deep** (thorough search)\n")
            f.write("- Results have been refined with additional iterations\n")
            f.write("- If results are unsatisfactory, try adjusting scoring weights\n\n")


def format_plaintext_with_spacing(plaintext: str, group_size: int = 5) -> str:
    """Format plaintext with spacing for readability."""
    groups = [plaintext[i:i+group_size] for i in range(0, len(plaintext), group_size)]
    return ' '.join(groups)


class NgramRecord:
    """Record per singolo n-gramma."""
    def __init__(self, ngram: str, start_pos: int, end_pos: int, logprob: float, count: Optional[int] = None):
        self.ngram = ngram
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.logprob = logprob
        self.count = count
        self.observed = count > 0 if count is not None else (logprob > -20.0)  # Euristica


class NgramAnalysis:
    """Analisi completa degli n-grammi."""
    def __init__(self):
        self.model_name = ""
        self.n = 0
        self.total_windows = 0
        self.observed_count = 0
        self.unobserved_count = 0
        self.observed_ratio = 0.0
        self.mean_logprob = 0.0
        self.min_logprob = 0.0
        self.max_logprob = 0.0
        self.top_best = []  # List[NgramRecord]
        self.top_worst = []  # List[NgramRecord]


def analyze_ngrams(
    plain_ids: np.ndarray,
    n: int,
    logprob: np.ndarray,
    counts: Optional[np.ndarray],
    model_name: str,
    top_k_best: int = 50,
    top_k_worst: int = 50
) -> NgramAnalysis:
    """
    Analizza n-grammi nel plaintext decifrato.

    Args:
        plain_ids: Array degli ID delle lettere
        n: Lunghezza n-gramma (3 o 4)
        logprob: Array log-probabilità
        counts: Array counts (opzionale)
        model_name: Nome del modello (es. "quad_continuous")
        top_k_best: Numero di migliori n-grammi da estrarre
        top_k_worst: Numero di peggiori n-grammi da estrarre

    Returns:
        NgramAnalysis con statistiche complete
    """
    from .config import ID_TO_LETTER, ALPHABET_SIZE

    analysis = NgramAnalysis()
    analysis.model_name = model_name
    analysis.n = n

    # Calcola numero finestre
    text_len = len(plain_ids)
    if text_len < n:
        return analysis

    total_windows = text_len - n + 1
    analysis.total_windows = total_windows

    # Raccogli tutti gli n-grammi con le loro statistiche
    all_ngrams = []
    total_logprob = 0.0
    observed = 0
    unobserved = 0

    for i in range(total_windows):
        # Estrai n-gramma
        ngram_ids = plain_ids[i:i+n].astype(np.int32)  # Cast to int32 to avoid overflow

        # Calcola indice
        if n == 3:
            idx = int(((ngram_ids[0] * ALPHABET_SIZE) + ngram_ids[1]) * ALPHABET_SIZE + ngram_ids[2])
        elif n == 4:
            idx = int((((ngram_ids[0] * ALPHABET_SIZE) + ngram_ids[1]) * ALPHABET_SIZE + ngram_ids[2]) * ALPHABET_SIZE + ngram_ids[3])
        else:
            continue

        # Ottieni logprob e count
        lp = float(logprob[idx])
        cnt = int(counts[idx]) if counts is not None else None

        # Converti a stringa
        ngram_str = ''.join([ID_TO_LETTER[int(nid)] for nid in ngram_ids])

        # Crea record
        record = NgramRecord(ngram_str, i, i+n, lp, cnt)
        all_ngrams.append(record)

        # Accumula statistiche
        total_logprob += lp
        if record.observed:
            observed += 1
        else:
            unobserved += 1

    # Calcola statistiche aggregate
    analysis.observed_count = observed
    analysis.unobserved_count = unobserved
    analysis.observed_ratio = observed / total_windows if total_windows > 0 else 0.0
    analysis.mean_logprob = total_logprob / total_windows if total_windows > 0 else 0.0

    # Trova min/max
    if all_ngrams:
        analysis.min_logprob = min(r.logprob for r in all_ngrams)
        analysis.max_logprob = max(r.logprob for r in all_ngrams)

        # Ordina per logprob
        sorted_by_logprob = sorted(all_ngrams, key=lambda r: r.logprob, reverse=True)

        # Top best
        analysis.top_best = sorted_by_logprob[:top_k_best]

        # Top worst
        analysis.top_worst = sorted_by_logprob[-top_k_worst:][::-1]

    return analysis


def save_ngram_analysis_json(analysis: NgramAnalysis, output_path: Path):
    """Salva analisi n-grammi in formato JSON."""
    data = {
        "model_name": analysis.model_name,
        "n": analysis.n,
        "total_windows": analysis.total_windows,
        "observed_count": analysis.observed_count,
        "unobserved_count": analysis.unobserved_count,
        "observed_ratio": analysis.observed_ratio,
        "mean_logprob": analysis.mean_logprob,
        "min_logprob": analysis.min_logprob,
        "max_logprob": analysis.max_logprob,
        "top_best": [
            {
                "ngram": r.ngram,
                "start_pos": r.start_pos,
                "end_pos": r.end_pos,
                "logprob": r.logprob,
                "count": r.count,
                "observed": r.observed
            }
            for r in analysis.top_best
        ],
        "top_worst": [
            {
                "ngram": r.ngram,
                "start_pos": r.start_pos,
                "end_pos": r.end_pos,
                "logprob": r.logprob,
                "count": r.count,
                "observed": r.observed
            }
            for r in analysis.top_worst
        ]
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_ngram_positions_csv(analysis: NgramAnalysis, output_path: Path):
    """Salva posizioni n-grammi in formato CSV."""
    with open(output_path, 'w', encoding='utf-8') as f:
        # Header
        f.write("model,n,start_pos,end_pos,ngram,logprob,count,observed,rank_by_logprob\n")

        # Top best
        for rank, record in enumerate(analysis.top_best, 1):
            count_str = str(record.count) if record.count is not None else ""
            f.write(f"{analysis.model_name},{analysis.n},{record.start_pos},{record.end_pos},"
                   f"{record.ngram},{record.logprob:.4f},{count_str},{record.observed},{rank}\n")


def hamming_distance(key1: np.ndarray, key2: np.ndarray) -> int:
    """Calcola Hamming distance tra due chiavi."""
    return int(np.sum(key1 != key2))


def format_ngram_table_markdown(records: List[NgramRecord], title: str, max_rows: int = 20) -> str:
    """Formatta tabella n-grammi in Markdown."""
    if not records:
        return f"### {title}\n\nNessun n-gramma disponibile.\n"

    lines = [f"### {title}", ""]
    lines.append("| pos | ngram | logprob | count | observed |")
    lines.append("|----:|-------|--------:|------:|:--------:|")

    for record in records[:max_rows]:
        count_str = str(record.count) if record.count is not None else "-"
        obs_str = "✓" if record.observed else "✗"
        lines.append(f"| {record.start_pos} | {record.ngram} | {record.logprob:.4f} | {count_str} | {obs_str} |")

    lines.append("")
    return '\n'.join(lines)
