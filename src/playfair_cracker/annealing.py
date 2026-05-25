"""
N-gram loading and annealing orchestration.
"""

import os
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class NgramModel:
    """Container for n-gram scoring models."""

    def __init__(
        self,
        quad_continuous: np.ndarray,
        tri_continuous: Optional[np.ndarray] = None,
        quad_inword: Optional[np.ndarray] = None,
        letter_logprob: Optional[np.ndarray] = None,
    ):
        self.quad_continuous = quad_continuous
        self.tri_continuous = tri_continuous
        self.quad_inword = quad_inword
        self.letter_logprob = letter_logprob

    def has_trigrams(self) -> bool:
        return self.tri_continuous is not None

    def has_inword(self) -> bool:
        return self.quad_inword is not None

    def has_letters(self) -> bool:
        return self.letter_logprob is not None


def load_ngram_model(ngram_dir: str) -> NgramModel:
    """
    Load n-gram scoring models from directory.

    Required:
        - npy/paisa_4grams_continuous_logprob.npy (shape: 390625)

    Optional:
        - npy/paisa_3grams_continuous_logprob.npy (shape: 15625)
        - npy/paisa_4grams_inword_logprob.npy (shape: 390625)
        - npy/paisa_letter_logprob.npy (shape: 25)
    """
    ngram_path = Path(ngram_dir)
    npy_dir = ngram_path / "npy"

    if not npy_dir.exists():
        raise ValueError(f"N-gram directory not found: {npy_dir}")

    # Load required quadgrams
    quad_continuous_path = npy_dir / "paisa_4grams_continuous_logprob.npy"
    if not quad_continuous_path.exists():
        raise ValueError(f"Required file not found: {quad_continuous_path}")

    logger.info(f"Loading quadgrams from {quad_continuous_path}")
    quad_continuous = np.load(str(quad_continuous_path), mmap_mode="r")

    if quad_continuous.shape != (390625,):
        raise ValueError(f"Invalid quadgram shape: {quad_continuous.shape}, expected (390625,)")

    # Convert to float32 for efficiency
    quad_continuous = quad_continuous.astype(np.float32)

    # Load optional trigrams
    tri_continuous = None
    tri_continuous_path = npy_dir / "paisa_3grams_continuous_logprob.npy"
    if tri_continuous_path.exists():
        logger.info(f"Loading trigrams from {tri_continuous_path}")
        tri_continuous = np.load(str(tri_continuous_path), mmap_mode="r")
        if tri_continuous.shape != (15625,):
            logger.warning(f"Invalid trigram shape: {tri_continuous.shape}, expected (15625,). Ignoring.")
            tri_continuous = None
        else:
            tri_continuous = tri_continuous.astype(np.float32)

    # Load optional inword quadgrams
    quad_inword = None
    quad_inword_path = npy_dir / "paisa_4grams_inword_logprob.npy"
    if quad_inword_path.exists():
        logger.info(f"Loading inword quadgrams from {quad_inword_path}")
        quad_inword = np.load(str(quad_inword_path), mmap_mode="r")
        if quad_inword.shape != (390625,):
            logger.warning(f"Invalid inword quadgram shape: {quad_inword.shape}, expected (390625,). Ignoring.")
            quad_inword = None
        else:
            quad_inword = quad_inword.astype(np.float32)

    # Load optional letter frequencies
    letter_logprob = None
    letter_logprob_path = npy_dir / "paisa_letter_logprob.npy"
    if letter_logprob_path.exists():
        logger.info(f"Loading letter frequencies from {letter_logprob_path}")
        letter_logprob = np.load(str(letter_logprob_path), mmap_mode="r")
        if letter_logprob.shape != (25,):
            logger.warning(f"Invalid letter shape: {letter_logprob.shape}, expected (25,). Ignoring.")
            letter_logprob = None
        else:
            letter_logprob = letter_logprob.astype(np.float32)

    return NgramModel(
        quad_continuous=quad_continuous,
        tri_continuous=tri_continuous,
        quad_inword=quad_inword,
        letter_logprob=letter_logprob,
    )


def prepare_scoring_data(
    cipher_data: Tuple,
    core_data: Optional[Tuple] = None,
) -> Dict:
    """
    Prepare data structures for scoring.

    Args:
        cipher_data: (cipher_ids, cipher_pairs, cipher_pair_ids, unique_pair_ids, inverse_unique_index)
        core_data: Optional same tuple for core blocks

    Returns:
        Dictionary with prepared data
    """
    cipher_ids, cipher_pairs, cipher_pair_ids, unique_pair_ids, inverse_unique_index = cipher_data

    data = {
        'full_unique_pair_ids': unique_pair_ids.astype(np.uint16),
        'full_inverse_unique_index': inverse_unique_index.astype(np.int64),
        'full_n_chars': len(cipher_ids),
    }

    if core_data is not None:
        core_ids, core_pairs, core_pair_ids, core_unique_pair_ids, core_inverse_unique_index = core_data
        data['core_unique_pair_ids'] = core_unique_pair_ids.astype(np.uint16)
        data['core_inverse_unique_index'] = core_inverse_unique_index.astype(np.int64)
        data['core_n_chars'] = len(core_ids)
    else:
        # Empty core data
        data['core_unique_pair_ids'] = np.array([], dtype=np.uint16)
        data['core_inverse_unique_index'] = np.array([], dtype=np.int64)
        data['core_n_chars'] = 0

    return data

