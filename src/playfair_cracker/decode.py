"""
Decode-only mode: decrypt with known key.
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging

from .preprocessing import ids_to_text, format_matrix, matrix_to_list
from .numba_core import (
    build_inverse_positions,
    decrypt_unique_pairs,
    rebuild_plain,
    score_quadgrams,
    score_trigrams,
    score_letters,
)

logger = logging.getLogger(__name__)


class DecodeResult:
    """Result of decode-only operation."""

    def __init__(
        self,
        plaintext: str,
        key: np.ndarray,
        scores: Dict[str, float],
        keyword: Optional[str] = None,
        warnings: list = None,
    ):
        self.plaintext = plaintext
        self.key = key
        self.scores = scores
        self.keyword = keyword
        self.warnings = warnings or []


def decode_with_known_key(
    cipher_data: Tuple,
    key: np.ndarray,
    ngram_model,
    core_data: Optional[Tuple] = None,
) -> DecodeResult:
    """
    Decifra con chiave nota.

    Args:
        cipher_data: Tuple da preprocess_cipher
        key: Chiave Playfair uint8[25]
        ngram_model: Modelli n-grammi caricati
        core_data: Opzionale, dati core blocks

    Returns:
        DecodeResult con plaintext e scores
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

    # Convert to text
    plaintext = ids_to_text(plain)

    # Calculate scores
    scores = {}

    # Quadgrams (obbligatorio)
    quad_score = score_quadgrams(plain, ngram_model.quad_continuous)
    scores['quad_continuous'] = float(quad_score)

    # Trigrams (opzionale)
    if ngram_model.tri_continuous is not None:
        tri_score = score_trigrams(plain, ngram_model.tri_continuous)
        scores['tri_continuous'] = float(tri_score)

    # Inword quadgrams (opzionale)
    if ngram_model.quad_inword is not None:
        inword_score = score_quadgrams(plain, ngram_model.quad_inword)
        scores['quad_inword'] = float(inword_score)

    # Letter frequencies (opzionale)
    if ngram_model.letter_logprob is not None:
        letter_score = score_letters(plain, ngram_model.letter_logprob)
        scores['letter'] = float(letter_score)

    # Decode core if provided
    if core_data is not None:
        core_ids, _, _, core_unique, core_inverse = core_data

        core_decoded_unique = np.empty(len(core_unique), dtype=np.uint16)
        decrypt_unique_pairs(core_unique, key, pos, core_decoded_unique)

        core_plain = np.empty(len(core_ids), dtype=np.uint8)
        rebuild_plain(core_decoded_unique, core_inverse, core_plain)

        core_plaintext = ids_to_text(core_plain)
        core_score = score_quadgrams(core_plain, ngram_model.quad_continuous)

        scores['core_plaintext'] = core_plaintext
        scores['core_quad_score'] = float(core_score)

    return DecodeResult(
        plaintext=plaintext,
        key=key,
        scores=scores,
    )


def save_decode_results(
    result: DecodeResult,
    output_dir: Path,
    cipher_file: str,
    cipher_length: int,
    keyword: Optional[str] = None,
    matrix_str: Optional[str] = None,
    warnings: list = None,
):
    """
    Salva risultati decode-only.

    Files generati:
    - decoded_plaintext.txt
    - known_key.txt
    - decode_report.md
    - decode_result.json
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    warnings = warnings or []

    # 1. Save plaintext
    plaintext_path = output_dir / "decoded_plaintext.txt"
    with open(plaintext_path, 'w') as f:
        f.write(result.plaintext)
    logger.info(f"Saved plaintext to: {plaintext_path}")

    # 2. Save key
    key_path = output_dir / "known_key.txt"
    with open(key_path, 'w') as f:
        if keyword:
            f.write(f"KEYWORD: {keyword}\n")
        f.write(f"ROW_MAJOR: {ids_to_text(result.key)}\n")
        f.write("\nMATRIX:\n")
        f.write(format_matrix(result.key))
    logger.info(f"Saved key to: {key_path}")

    # 3. Generate report
    report_path = output_dir / "decode_report.md"
    generate_decode_report(
        report_path,
        result,
        cipher_file,
        cipher_length,
        keyword,
        matrix_str,
        warnings,
    )
    logger.info(f"Saved report to: {report_path}")

    # 4. Save JSON
    json_path = output_dir / "decode_result.json"
    json_data = {
        "mode": "decode-only",
        "timestamp": datetime.now().isoformat(),
        "cipher_file": cipher_file,
        "cipher_length": cipher_length,
        "plaintext_length": len(result.plaintext),
        "scores": result.scores,
        "plaintext_preview": result.plaintext[:500] if len(result.plaintext) > 500 else result.plaintext,
        "plaintext_tail": result.plaintext[-500:] if len(result.plaintext) > 500 else "",
        "warnings": warnings,
    }

    if keyword:
        json_data["known_keyword"] = keyword

    if matrix_str:
        json_data["known_matrix_row_major"] = matrix_str
    else:
        json_data["known_matrix_row_major"] = ids_to_text(result.key)

    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    logger.info(f"Saved JSON to: {json_path}")


def generate_decode_report(
    report_path: Path,
    result: DecodeResult,
    cipher_file: str,
    cipher_length: int,
    keyword: Optional[str],
    matrix_str: Optional[str],
    warnings: list,
):
    """Genera report Markdown per decode-only."""

    with open(report_path, 'w') as f:
        f.write("# Playfair Decode-Only Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Configuration\n\n")
        f.write("- **Mode:** decode-only (no simulated annealing)\n")
        f.write(f"- **Cipher file:** {cipher_file}\n")
        f.write(f"- **Cipher length:** {cipher_length} characters\n")

        if keyword:
            f.write(f"- **Known keyword:** `{keyword}`\n")

        f.write("\n## Known Key\n\n")
        f.write("**Matrix (5×5):**\n\n")
        f.write("```\n")
        f.write(format_matrix(result.key))
        f.write("\n```\n\n")
        f.write(f"**Row-major:** `{ids_to_text(result.key)}`\n\n")

        f.write("## Scores\n\n")
        f.write("| Metric | Score |\n")
        f.write("|--------|-------|\n")

        if 'quad_continuous' in result.scores:
            f.write(f"| Quadgrams (continuous) | {result.scores['quad_continuous']:.4f} |\n")
        if 'tri_continuous' in result.scores:
            f.write(f"| Trigrams (continuous) | {result.scores['tri_continuous']:.4f} |\n")
        if 'quad_inword' in result.scores:
            f.write(f"| Quadgrams (inword) | {result.scores['quad_inword']:.4f} |\n")
        if 'letter' in result.scores:
            f.write(f"| Letter frequencies | {result.scores['letter']:.4f} |\n")

        f.write("\n## Decoded Plaintext\n\n")
        f.write(f"**Length:** {len(result.plaintext)} characters\n\n")

        f.write("### First 500 characters\n\n")
        f.write("```\n")
        preview = result.plaintext[:500] if len(result.plaintext) > 500 else result.plaintext
        f.write(preview)
        if len(result.plaintext) > 500:
            f.write("\n...")
        f.write("\n```\n\n")

        if len(result.plaintext) > 500:
            f.write("### Last 500 characters\n\n")
            f.write("```\n")
            f.write(result.plaintext[-500:])
            f.write("\n```\n\n")

        # Core blocks if present
        if 'core_plaintext' in result.scores:
            f.write("## Core Blocks\n\n")
            f.write(f"**Core plaintext:** {result.scores['core_plaintext']}\n\n")
            f.write(f"**Core quad score:** {result.scores['core_quad_score']:.4f}\n\n")

        # Warnings
        if warnings:
            f.write("## Warnings\n\n")
            for warning in warnings:
                f.write(f"- ⚠️ {warning}\n")
            f.write("\n")

        f.write("## Notes\n\n")
        f.write("- This is decode-only mode: no optimization was performed\n")
        f.write("- The key was provided externally (keyword or matrix)\n")
        f.write("- Scores show linguistic plausibility of the decryption\n")
        f.write("- Higher scores (less negative) indicate better Italian text\n")

