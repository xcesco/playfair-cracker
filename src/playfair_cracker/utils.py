"""
Utility functions.
"""

import os
import logging
import numpy as np
from pathlib import Path
from typing import Optional


def setup_logging(verbose: bool = False, quiet: bool = False):
    """Configure logging."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S',
    )


def read_file_safe(filepath: str) -> str:
    """Read file content safely."""
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def get_default_ngram_dir() -> str:
    """Get default n-gram directory."""
    return "assets/ngrams_paisa_alphabet25"


def get_cpu_count() -> int:
    """Get number of CPUs, defaulting to 1 if unavailable."""
    try:
        return os.cpu_count() or 1
    except:
        return 1


def key_from_keyword(keyword: str) -> np.ndarray:
    """
    Costruisce matrice Playfair da keyword.

    Regole:
    1. Normalizza keyword (uppercase, J→I, solo lettere)
    2. Rimuove duplicati preservando ordine
    3. Aggiunge lettere mancanti in ordine alfabetico

    Args:
        keyword: Parola chiave

    Returns:
        Array uint8[25] con matrice Playfair

    Example:
        >>> key_from_keyword("INTELLIGENCE")
        # Restituisce: INTELGCABDFHKMOPQRSUVWXYZ
    """
    from .config import ALPHABET, LETTER_TO_ID

    # Normalizza keyword
    keyword = keyword.upper().replace('J', 'I')
    keyword = ''.join(c for c in keyword if c in ALPHABET)

    if not keyword:
        raise ValueError("Keyword is empty after normalization")

    # Rimuovi duplicati preservando ordine
    seen = set()
    key_letters = []
    for char in keyword:
        if char not in seen:
            seen.add(char)
            key_letters.append(char)

    # Aggiungi lettere mancanti in ordine alfabetico
    for char in ALPHABET:
        if char not in seen:
            seen.add(char)
            key_letters.append(char)

    # Converti in array di IDs
    key = np.array([LETTER_TO_ID[c] for c in key_letters], dtype=np.uint8)

    if len(key) != 25:
        raise ValueError(f"Invalid key length: {len(key)}, expected 25")

    return key


def key_from_matrix(matrix: str) -> np.ndarray:
    """
    Costruisce chiave da stringa matrice completa.

    Args:
        matrix: Stringa con 25 lettere (può contenere spazi/newline)

    Returns:
        Array uint8[25] con matrice Playfair

    Raises:
        ValueError: Se matrice non valida

    Example:
        >>> key_from_matrix("ABCDEFGHIKLMNOPQRSTUVWXYZ")
        # Restituisce array con IDs corrispondenti
    """
    from .config import ALPHABET, LETTER_TO_ID

    # Normalizza: uppercase, J→I, rimuovi non-lettere
    matrix = matrix.upper().replace('J', 'I')
    matrix = ''.join(c for c in matrix if c in ALPHABET)

    # Verifica lunghezza
    if len(matrix) != 25:
        raise ValueError(f"Invalid matrix length: {len(matrix)}, expected 25 letters")

    # Verifica lettere uniche
    if len(set(matrix)) != 25:
        duplicates = [c for c in set(matrix) if matrix.count(c) > 1]
        raise ValueError(f"Matrix contains duplicate letters: {duplicates}")

    # Verifica che contenga tutte le lettere dell'alfabeto
    matrix_set = set(matrix)
    alphabet_set = set(ALPHABET)

    if matrix_set != alphabet_set:
        missing = alphabet_set - matrix_set
        extra = matrix_set - alphabet_set
        msg = []
        if missing:
            msg.append(f"Missing letters: {sorted(missing)}")
        if extra:
            msg.append(f"Extra letters: {sorted(extra)}")
        raise ValueError(". ".join(msg))

    # Converti in array di IDs
    key = np.array([LETTER_TO_ID[c] for c in matrix], dtype=np.uint8)

    return key


def key_to_text(key: np.ndarray) -> str:
    """
    Converte chiave in stringa.

    Args:
        key: Array uint8[25]

    Returns:
        Stringa 25 caratteri
    """
    from .config import ID_TO_LETTER
    return ''.join([ID_TO_LETTER[int(i)] for i in key])


def validate_key(key: np.ndarray) -> None:
    """
    Valida che una chiave sia corretta.

    Args:
        key: Array da validare

    Raises:
        ValueError: Se chiave non valida
    """
    if not isinstance(key, np.ndarray):
        raise ValueError("Key must be numpy array")

    if key.dtype != np.uint8:
        raise ValueError(f"Key must be uint8, got {key.dtype}")

    if len(key) != 25:
        raise ValueError(f"Key must have length 25, got {len(key)}")

    # Verifica che contenga tutti i numeri 0-24 esattamente una volta
    if not np.array_equal(np.sort(key), np.arange(25, dtype=np.uint8)):
        raise ValueError("Key must contain all values 0-24 exactly once")
