"""
Initial key/matrix handling for local search and restart strategies.
"""

import numpy as np
from typing import List, Optional, Tuple
import random

from .config import ALPHABET_SIZE
from .utils import key_from_keyword, key_from_matrix


def random_perturbations(key: np.ndarray, radius: int, rng_seed: int) -> np.ndarray:
    """
    Applica mutazioni casuali a una chiave.

    Args:
        key: Chiave iniziale
        radius: Numero massimo di mutazioni da applicare
        rng_seed: Seed per generatore random

    Returns:
        Chiave perturbata
    """
    perturbed = key.copy()
    rng = np.random.RandomState(rng_seed)

    # Numero effettivo di mutazioni: tra 1 e radius
    n_mutations = rng.randint(1, radius + 1) if radius > 0 else 0

    for _ in range(n_mutations):
        mutation_type = rng.rand()

        if mutation_type < 0.85:
            # Swap due lettere
            i, j = rng.choice(ALPHABET_SIZE, 2, replace=False)
            perturbed[i], perturbed[j] = perturbed[j], perturbed[i]

        elif mutation_type < 0.92:
            # Swap due righe
            r1, r2 = rng.choice(5, 2, replace=False)
            for c in range(5):
                i1 = r1 * 5 + c
                i2 = r2 * 5 + c
                perturbed[i1], perturbed[i2] = perturbed[i2], perturbed[i1]

        else:
            # Swap due colonne
            c1, c2 = rng.choice(5, 2, replace=False)
            for r in range(5):
                i1 = r * 5 + c1
                i2 = r * 5 + c2
                perturbed[i1], perturbed[i2] = perturbed[i2], perturbed[i1]

    return perturbed


def prepare_initial_keys(
    initial_keyword: Optional[str],
    initial_matrix: Optional[str],
    initial_key_file: Optional[str],
    n_restarts: int,
    base_seed: int,
    local_search: bool,
    mutation_radius: int,
    random_ratio: float = 0.3
) -> List[Tuple[np.ndarray, str, int]]:
    """
    Prepara chiavi iniziali per tutti i restart.

    Args:
        initial_keyword: Keyword opzionale
        initial_matrix: Matrice opzionale
        initial_key_file: File con matrici opzionali
        n_restarts: Numero di restart
        base_seed: Seed base per RNG
        local_search: Se True, usa solo initial keys perturbate
        mutation_radius: Raggio di perturbazione
        random_ratio: Frazione di restart completamente casuali (ignorato se local_search=True)

    Returns:
        Lista di tuple (chiave, source, mutation_radius_used)
    """
    base_keys = []
    sources = []

    # Carica chiavi base
    if initial_keyword:
        key = key_from_keyword(initial_keyword)
        base_keys.append(key)
        sources.append(f"keyword:{initial_keyword}")

    if initial_matrix:
        key = key_from_matrix(initial_matrix)
        base_keys.append(key)
        sources.append(f"matrix:{initial_matrix[:30]}...")

    if initial_key_file:
        # Carica matrici da file (una per riga)
        with open(initial_key_file, 'r') as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        key = key_from_matrix(line)
                        base_keys.append(key)
                        sources.append(f"file:line{line_no}")
                    except Exception as e:
                        print(f"Warning: Could not parse line {line_no} in {initial_key_file}: {e}")

    # Se non ci sono chiavi base, tutti i restart saranno casuali
    if not base_keys:
        result = []
        for i in range(n_restarts):
            # Chiave casuale
            key = np.arange(ALPHABET_SIZE, dtype=np.uint8)
            rng = np.random.RandomState(base_seed + i * 1000)
            rng.shuffle(key)
            result.append((key, "random", 0))
        return result

    # Prepara restart
    result = []
    n_base_keys = len(base_keys)

    # Determina quanti restart casuali
    if local_search:
        n_random = 0  # Local search: 100% da initial keys
    else:
        n_random = int(n_restarts * random_ratio)

    n_from_base = n_restarts - n_random

    # Restart da chiavi base
    for i in range(n_from_base):
        # Scegli chiave base round-robin
        base_idx = i % n_base_keys
        base_key = base_keys[base_idx]
        source = sources[base_idx]

        # Applica perturbazioni
        seed = base_seed + i * 1000

        if mutation_radius > 0:
            perturbed_key = random_perturbations(base_key, mutation_radius, seed)
            result.append((perturbed_key, source, mutation_radius))
        else:
            # Nessuna perturbazione
            result.append((base_key.copy(), source, 0))

    # Restart completamente casuali
    for i in range(n_random):
        key = np.arange(ALPHABET_SIZE, dtype=np.uint8)
        rng = np.random.RandomState(base_seed + (n_from_base + i) * 1000)
        rng.shuffle(key)
        result.append((key, "random", 0))

    return result


def get_local_search_params() -> dict:
    """Parametri ottimizzati per local search."""
    return {
        'T0': 8.0,  # Temperatura iniziale più bassa
        'cooling': 0.999998,  # Raffreddamento più rapido
        'phase_weights': {
            'swap_letters': 0.90,
            'swap_rows': 0.03,
            'swap_cols': 0.03,
            'rotate_row': 0.01,
            'rotate_col': 0.01,
            'flip_row': 0.01,
            'flip_col': 0.01,
            'transpose': 0.00,
            'large_jump': 0.00,
        }
    }

