"""
Text preprocessing for Playfair cipher.
"""

import numpy as np
from typing import Tuple
from .config import ALPHABET, LETTER_TO_ID, ID_TO_LETTER, ALPHABET_SIZE


def normalize_text(text: str) -> str:
    """
    Normalize text for Playfair cipher.

    - Convert to uppercase
    - J -> I
    - Keep only valid alphabet characters
    """
    text = text.upper()
    text = text.replace('J', 'I')

    # Keep only valid characters
    result = []
    for char in text:
        if char in LETTER_TO_ID:
            result.append(char)

    return ''.join(result)


def text_to_ids(text: str) -> np.ndarray:
    """Convert text to array of letter IDs."""
    return np.array([LETTER_TO_ID[c] for c in text], dtype=np.uint8)


def ids_to_text(ids: np.ndarray) -> str:
    """Convert array of letter IDs to text."""
    return ''.join([ID_TO_LETTER[int(i)] for i in ids])


def split_pairs(ids: np.ndarray, strict: bool = False) -> np.ndarray:
    """
    Split text IDs into pairs.

    Returns:
        Array of shape (n_pairs, 2) with dtype uint8
    """
    n = len(ids)

    if n % 2 != 0:
        if strict:
            raise ValueError(f"Text length {n} is odd, cannot split into pairs in strict mode")
        else:
            print(f"Warning: Text length {n} is odd, ignoring last character")
            ids = ids[:-1]
            n = len(ids)

    return ids.reshape(-1, 2)


def preprocess_cipher(text: str, strict: bool = False) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Preprocess cipher text.

    Returns:
        cipher_ids: Full cipher as letter IDs
        cipher_pairs: Pairs of letters (n_pairs, 2)
        cipher_pair_ids: Pair IDs (c1 * 25 + c2)
        unique_pair_ids: Unique pair IDs
        inverse_unique_index: Indices to reconstruct from unique pairs
    """
    # Normalize
    normalized = normalize_text(text)

    # Convert to IDs
    cipher_ids = text_to_ids(normalized)

    # Split into pairs
    cipher_pairs = split_pairs(cipher_ids, strict=strict)

    # Compute pair IDs (cast to uint16 to avoid overflow since max pair_id = 24*25+24 = 624)
    cipher_pair_ids = cipher_pairs[:, 0].astype(np.uint16) * ALPHABET_SIZE + cipher_pairs[:, 1].astype(np.uint16)

    # Get unique pairs for optimization
    unique_pair_ids, inverse_unique_index = np.unique(cipher_pair_ids, return_inverse=True)

    return cipher_ids, cipher_pairs, cipher_pair_ids, unique_pair_ids, inverse_unique_index


def valid_key(key: np.ndarray) -> bool:
    """
    Check if a key is valid.

    - Must have length 25
    - Must contain all letters 0..24 exactly once
    """
    if len(key) != ALPHABET_SIZE:
        return False

    if not np.array_equal(np.sort(key), np.arange(ALPHABET_SIZE, dtype=np.uint8)):
        return False

    return True


def generate_random_key(seed: int = None) -> np.ndarray:
    """Generate a random permutation key."""
    if seed is not None:
        np.random.seed(seed)

    key = np.arange(ALPHABET_SIZE, dtype=np.uint8)
    np.random.shuffle(key)
    return key


def key_to_string(key: np.ndarray) -> str:
    """Convert key array to string representation."""
    return ids_to_text(key)


def format_matrix(key: np.ndarray) -> str:
    """
    Format key as 5x5 matrix.

    Returns string like:
    A B C D E
    F G H I K
    L M N O P
    Q R S T U
    V W X Y Z
    """
    lines = []
    for row in range(5):
        row_letters = [ID_TO_LETTER[int(key[row * 5 + col])] for col in range(5)]
        lines.append(' '.join(row_letters))
    return '\n'.join(lines)


def matrix_to_list(key: np.ndarray) -> list:
    """Convert key to list of 5 strings (one per row)."""
    rows = []
    for row in range(5):
        row_letters = ''.join([ID_TO_LETTER[int(key[row * 5 + col])] for col in range(5)])
        rows.append(row_letters)
    return rows

