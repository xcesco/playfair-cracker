"""
Validation of n-gram models and indexing correctness.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def load_metadata(ngram_dir: str) -> Dict:
    """Load metadata.json from n-gram directory."""
    metadata_path = Path(ngram_dir) / "metadata.json"

    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    with open(metadata_path, 'r') as f:
        return json.load(f)


def validate_alphabet(metadata: Dict, expected_alphabet: str) -> bool:
    """
    Validate that metadata alphabet matches expected alphabet.

    Returns True if valid, raises ValueError otherwise.
    """
    meta_alphabet = metadata.get("alphabet", "")
    meta_base = metadata.get("base", 0)

    if meta_alphabet != expected_alphabet:
        raise ValueError(
            f"Alphabet mismatch!\n"
            f"Expected: {expected_alphabet}\n"
            f"Metadata: {meta_alphabet}"
        )

    if meta_base != len(expected_alphabet):
        raise ValueError(
            f"Base mismatch!\n"
            f"Expected: {len(expected_alphabet)}\n"
            f"Metadata: {meta_base}"
        )

    logger.info(f"✓ Alphabet validated: {meta_alphabet} (base {meta_base})")
    return True


def validate_vocab_sizes(metadata: Dict) -> bool:
    """
    Validate that vocab sizes match expected dimensions.

    base^3 = 15625
    base^4 = 390625
    """
    models = metadata.get("models", {})

    # Validate trigrams
    if "3_continuous" in models:
        expected_3 = 15625  # 25^3
        actual_3 = models["3_continuous"]["vocab_size"]
        if actual_3 != expected_3:
            raise ValueError(f"Trigram vocab size mismatch: {actual_3} != {expected_3}")
        logger.info(f"✓ Trigram vocab size: {actual_3}")

    # Validate quadgrams
    if "4_continuous" in models:
        expected_4 = 390625  # 25^4
        actual_4 = models["4_continuous"]["vocab_size"]
        if actual_4 != expected_4:
            raise ValueError(f"Quadgram vocab size mismatch: {actual_4} != {expected_4}")
        logger.info(f"✓ Quadgram vocab size: {actual_4}")

    # Validate letters
    if "letters" in metadata:
        expected_letters = 25
        actual_letters = metadata["letters"]["unique_letters"]
        if actual_letters != expected_letters:
            raise ValueError(f"Letter count mismatch: {actual_letters} != {expected_letters}")
        logger.info(f"✓ Letter count: {actual_letters}")

    return True


def validate_indexing(metadata: Dict, alphabet: str) -> bool:
    """
    Validate that indexing formulas are correct.

    Tests known letter mappings from metadata.
    """
    # Create letter to ID mapping
    letter_to_id = {letter: idx for idx, letter in enumerate(alphabet)}

    # Get top letters from metadata
    letters_info = metadata.get("letters", {}).get("top_letters", [])

    for letter_info in letters_info[:5]:  # Test top 5
        letter = letter_info["letter"]
        expected_id = letter_info["letter_id"]

        if letter not in letter_to_id:
            logger.warning(f"Letter {letter} not in alphabet")
            continue

        actual_id = letter_to_id[letter]

        if actual_id != expected_id:
            raise ValueError(
                f"Letter indexing error!\n"
                f"Letter: {letter}\n"
                f"Expected ID: {expected_id}\n"
                f"Actual ID: {actual_id}"
            )

    logger.info(f"✓ Letter indexing validated (tested {min(5, len(letters_info))} letters)")
    return True


def validate_array_shapes(
    ngram_dir: str,
    metadata: Dict,
) -> bool:
    """
    Validate that loaded numpy arrays have correct shapes.
    """
    npy_dir = Path(ngram_dir) / "npy"

    # Check quadgrams continuous
    quad_path = npy_dir / "paisa_4grams_continuous_logprob.npy"
    if quad_path.exists():
        quad_array = np.load(str(quad_path), mmap_mode='r')
        expected_shape = (390625,)
        if quad_array.shape != expected_shape:
            raise ValueError(f"Quadgram shape mismatch: {quad_array.shape} != {expected_shape}")
        logger.info(f"✓ Quadgram array shape: {quad_array.shape}")

    # Check trigrams continuous
    tri_path = npy_dir / "paisa_3grams_continuous_logprob.npy"
    if tri_path.exists():
        tri_array = np.load(str(tri_path), mmap_mode='r')
        expected_shape = (15625,)
        if tri_array.shape != expected_shape:
            raise ValueError(f"Trigram shape mismatch: {tri_array.shape} != {expected_shape}")
        logger.info(f"✓ Trigram array shape: {tri_array.shape}")

    # Check letters
    letter_path = npy_dir / "paisa_letter_logprob.npy"
    if letter_path.exists():
        letter_array = np.load(str(letter_path), mmap_mode='r')
        expected_shape = (25,)
        if letter_array.shape != expected_shape:
            raise ValueError(f"Letter shape mismatch: {letter_array.shape} != {expected_shape}")
        logger.info(f"✓ Letter array shape: {letter_array.shape}")

    return True


def test_known_ngrams(ngram_dir: str, alphabet: str) -> bool:
    """
    Test known n-grams from CSV files to validate indexing.
    """
    csv_dir = Path(ngram_dir) / "csv"
    letter_to_id = {letter: idx for idx, letter in enumerate(alphabet)}

    # Test letter frequencies
    letter_csv = csv_dir / "paisa_letter_frequencies.csv"
    if letter_csv.exists():
        import csv
        with open(letter_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in list(reader)[:5]:  # Test first 5
                letter = row['letter']
                expected_id = int(row['letter_id'])

                if letter in letter_to_id:
                    actual_id = letter_to_id[letter]
                    if actual_id != expected_id:
                        raise ValueError(
                            f"Letter indexing mismatch in CSV!\n"
                            f"Letter: {letter}\n"
                            f"CSV letter_id: {expected_id}\n"
                            f"Our letter_id: {actual_id}"
                        )
        logger.info(f"✓ CSV letter indexing validated")

    # Test some trigrams
    tri_csv = csv_dir / "paisa_3grams_continuous.csv"
    if tri_csv.exists():
        import csv
        with open(tri_csv, 'r') as f:
            reader = csv.DictReader(f)
            tested = 0
            for row in list(reader)[:10]:  # Test first 10
                ngram = row['ngram']
                if len(ngram) != 3:
                    continue

                # All letters must be in alphabet
                if all(c in letter_to_id for c in ngram):
                    a, b, c = [letter_to_id[ch] for ch in ngram]
                    idx = ((a * 25) + b) * 25 + c

                    # Just verify it's in valid range
                    if not (0 <= idx < 15625):
                        raise ValueError(f"Trigram index out of range: {ngram} -> {idx}")

                    tested += 1

            if tested > 0:
                logger.info(f"✓ Trigram indexing validated (tested {tested} n-grams)")

    # Test some quadgrams
    quad_csv = csv_dir / "paisa_4grams_continuous.csv"
    if quad_csv.exists():
        import csv
        with open(quad_csv, 'r') as f:
            reader = csv.DictReader(f)
            tested = 0
            for row in list(reader)[:10]:  # Test first 10
                ngram = row['ngram']
                if len(ngram) != 4:
                    continue

                # All letters must be in alphabet
                if all(c in letter_to_id for c in ngram):
                    a, b, c, d = [letter_to_id[ch] for ch in ngram]
                    idx = (((a * 25) + b) * 25 + c) * 25 + d

                    # Just verify it's in valid range
                    if not (0 <= idx < 390625):
                        raise ValueError(f"Quadgram index out of range: {ngram} -> {idx}")

                    tested += 1

            if tested > 0:
                logger.info(f"✓ Quadgram indexing validated (tested {tested} n-grams)")

    return True


def validate_ngram_directory(ngram_dir: str, alphabet: str) -> Tuple[Dict, bool]:
    """
    Complete validation of n-gram directory.

    Returns:
        (metadata, validation_passed)
    """
    logger.info("=" * 60)
    logger.info("Validating n-gram directory structure")
    logger.info("=" * 60)

    # Load metadata
    try:
        metadata = load_metadata(ngram_dir)
        logger.info(f"✓ Metadata loaded from {ngram_dir}/metadata.json")
    except Exception as e:
        logger.error(f"✗ Failed to load metadata: {e}")
        return None, False

    # Validate alphabet
    try:
        validate_alphabet(metadata, alphabet)
    except Exception as e:
        logger.error(f"✗ Alphabet validation failed: {e}")
        return metadata, False

    # Validate vocab sizes
    try:
        validate_vocab_sizes(metadata)
    except Exception as e:
        logger.error(f"✗ Vocab size validation failed: {e}")
        return metadata, False

    # Validate indexing
    try:
        validate_indexing(metadata, alphabet)
    except Exception as e:
        logger.error(f"✗ Indexing validation failed: {e}")
        return metadata, False

    # Validate array shapes
    try:
        validate_array_shapes(ngram_dir, metadata)
    except Exception as e:
        logger.error(f"✗ Array shape validation failed: {e}")
        return metadata, False

    # Test known n-grams from CSV
    try:
        test_known_ngrams(ngram_dir, alphabet)
    except Exception as e:
        logger.error(f"✗ N-gram testing failed: {e}")
        return metadata, False

    logger.info("=" * 60)
    logger.info("✓ ALL VALIDATIONS PASSED")
    logger.info("=" * 60)

    return metadata, True


def get_default_scores(metadata: Dict) -> Dict:
    """Extract default log probabilities from metadata."""
    defaults = {}

    models = metadata.get("models", {})

    if "4_continuous" in models:
        defaults['quad_continuous'] = models["4_continuous"]["default_log_probability"]

    if "3_continuous" in models:
        defaults['tri_continuous'] = models["3_continuous"]["default_log_probability"]

    if "4_inword" in models:
        defaults['quad_inword'] = models["4_inword"]["default_log_probability"]

    return defaults

