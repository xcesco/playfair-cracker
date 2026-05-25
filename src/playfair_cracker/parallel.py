"""
Parallel execution of annealing restarts.
"""

import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Tuple
import logging
from tqdm import tqdm

from .numba_core import annealing_run
from .preprocessing import generate_random_key, key_to_string, ids_to_text
from .config import ModeConfig

logger = logging.getLogger(__name__)


class Result:
    """Container for a single annealing result."""

    def __init__(
        self,
        key: np.ndarray,
        score: float,
        worker_id: int,
        restart_id: int,
        iters: int,
        seed: int,
    ):
        self.key = key
        self.score = score
        self.worker_id = worker_id
        self.restart_id = restart_id
        self.iters = iters
        self.seed = seed
        self.key_string = key_to_string(key)
        self.key_tuple = tuple(key.tolist())


def run_single_restart(
    restart_id: int,
    worker_id: int,
    base_seed: int,
    config: ModeConfig,
    scoring_data: Dict,
    ngram_arrays: Dict,
) -> Result:
    """
    Run a single annealing restart.

    This function will be executed in a separate process.
    """
    # Generate unique seed for this restart
    seed = base_seed + worker_id * 1_000_000 + restart_id

    # Generate random initial key
    initial_key = generate_random_key(seed=seed)

    # Extract scoring data
    full_unique_pair_ids = scoring_data['full_unique_pair_ids']
    full_inverse_unique_index = scoring_data['full_inverse_unique_index']
    full_n_chars = scoring_data['full_n_chars']

    core_unique_pair_ids = scoring_data['core_unique_pair_ids']
    core_inverse_unique_index = scoring_data['core_inverse_unique_index']
    core_n_chars = scoring_data['core_n_chars']

    # Extract n-gram arrays
    quad_scores = ngram_arrays['quad_continuous']
    tri_scores = ngram_arrays.get('tri_continuous')
    inword_scores = ngram_arrays.get('quad_inword')
    letter_scores = ngram_arrays.get('letter_logprob')

    # Run annealing
    best_key, best_score = annealing_run(
        initial_key,
        seed,
        config.iters,
        config.T0,
        config.cooling,
        full_unique_pair_ids,
        full_inverse_unique_index,
        full_n_chars,
        core_unique_pair_ids,
        core_inverse_unique_index,
        core_n_chars,
        quad_scores,
        tri_scores,
        inword_scores,
        letter_scores,
        config.w_full,
        config.w_core,
        config.w_tri,
        config.w_inword,
        config.w_letter,
    )

    return Result(
        key=best_key,
        score=best_score,
        worker_id=worker_id,
        restart_id=restart_id,
        iters=config.iters,
        seed=seed,
    )


def run_parallel_annealing(
    n_restarts: int,
    n_workers: int,
    base_seed: int,
    config: ModeConfig,
    scoring_data: Dict,
    ngram_arrays: Dict,
    top_k: int = 50,
    verbose: bool = True,
    quiet: bool = False,
) -> List[Result]:
    """
    Run multiple annealing restarts in parallel.

    Returns:
        List of top-k results sorted by score (descending)
    """
    results = []

    logger.info(f"Starting {n_restarts} restarts across {n_workers} workers")

    # Distribute restarts across workers
    restarts_per_worker = [n_restarts // n_workers] * n_workers
    for i in range(n_restarts % n_workers):
        restarts_per_worker[i] += 1

    # Create tasks
    tasks = []
    global_restart_id = 0
    for worker_id in range(n_workers):
        for local_restart_id in range(restarts_per_worker[worker_id]):
            tasks.append((global_restart_id, worker_id, base_seed, config, scoring_data, ngram_arrays))
            global_restart_id += 1

    # Execute in parallel
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = {
            executor.submit(run_single_restart, *task): task[0]
            for task in tasks
        }

        # Collect results with progress bar
        if not quiet:
            pbar = tqdm(total=len(futures), desc="Annealing restarts", disable=not verbose)

        for future in as_completed(futures):
            restart_id = futures[future]
            try:
                result = future.result()
                results.append(result)

                if not quiet and verbose:
                    pbar.set_postfix({'best_score': f'{max(r.score for r in results):.3f}'})
                    pbar.update(1)

            except Exception as e:
                logger.error(f"Restart {restart_id} failed: {e}")
                if not quiet:
                    pbar.update(1)

        if not quiet:
            pbar.close()

    # Sort by score (descending)
    results.sort(key=lambda r: r.score, reverse=True)

    # Deduplicate by key
    seen_keys = set()
    unique_results = []

    for result in results:
        if result.key_tuple not in seen_keys:
            seen_keys.add(result.key_tuple)
            unique_results.append(result)

            if len(unique_results) >= top_k:
                break

    logger.info(f"Found {len(unique_results)} unique keys in top-{top_k}")

    return unique_results


def run_refinement(
    initial_results: List[Result],
    refinement_config: ModeConfig,
    base_seed: int,
    n_workers: int,
    scoring_data: Dict,
    ngram_arrays: Dict,
    verbose: bool = True,
    quiet: bool = False,
) -> List[Result]:
    """
    Refine top results with additional iterations.
    """
    logger.info(f"Refining {len(initial_results)} results")

    refined_results = []

    tasks = []
    for idx, result in enumerate(initial_results):
        # Use the result's key as initial key
        tasks.append((idx, result.key, base_seed + 10_000_000, refinement_config, scoring_data, ngram_arrays))

    # Run refinement
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = {
            executor.submit(
                run_refinement_single,
                task[0],  # idx
                task[1],  # initial_key
                task[2],  # seed
                task[3],  # config
                task[4],  # scoring_data
                task[5],  # ngram_arrays
            ): task[0]
            for task in tasks
        }

        if not quiet:
            pbar = tqdm(total=len(futures), desc="Refinement", disable=not verbose)

        for future in as_completed(futures):
            idx = futures[future]
            try:
                result = future.result()
                refined_results.append(result)

                if not quiet:
                    pbar.update(1)

            except Exception as e:
                logger.error(f"Refinement {idx} failed: {e}")
                if not quiet:
                    pbar.update(1)

        if not quiet:
            pbar.close()

    # Sort by score
    refined_results.sort(key=lambda r: r.score, reverse=True)

    return refined_results


def run_refinement_single(
    idx: int,
    initial_key: np.ndarray,
    seed: int,
    config: ModeConfig,
    scoring_data: Dict,
    ngram_arrays: Dict,
) -> Result:
    """Run a single refinement."""
    # Extract data
    full_unique_pair_ids = scoring_data['full_unique_pair_ids']
    full_inverse_unique_index = scoring_data['full_inverse_unique_index']
    full_n_chars = scoring_data['full_n_chars']

    core_unique_pair_ids = scoring_data['core_unique_pair_ids']
    core_inverse_unique_index = scoring_data['core_inverse_unique_index']
    core_n_chars = scoring_data['core_n_chars']

    quad_scores = ngram_arrays['quad_continuous']
    tri_scores = ngram_arrays.get('tri_continuous')
    inword_scores = ngram_arrays.get('quad_inword')
    letter_scores = ngram_arrays.get('letter_logprob')

    # Run annealing from initial key
    best_key, best_score = annealing_run(
        initial_key,
        seed + idx,
        config.iters,
        config.T0,
        config.cooling,
        full_unique_pair_ids,
        full_inverse_unique_index,
        full_n_chars,
        core_unique_pair_ids,
        core_inverse_unique_index,
        core_n_chars,
        quad_scores,
        tri_scores,
        inword_scores,
        letter_scores,
        config.w_full,
        config.w_core,
        config.w_tri,
        config.w_inword,
        config.w_letter,
    )

    return Result(
        key=best_key,
        score=best_score,
        worker_id=-1,  # refinement
        restart_id=idx,
        iters=config.iters,
        seed=seed + idx,
    )

