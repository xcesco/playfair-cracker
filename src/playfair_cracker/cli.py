"""
Command-line interface for Playfair cracker.
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import Optional

from .utils import setup_logging, read_file_safe, get_default_ngram_dir, get_cpu_count
from .config import get_mode_config, DEEP_REFINEMENT, ALPHABET
from .preprocessing import preprocess_cipher
from .annealing import load_ngram_model, prepare_scoring_data
from .parallel import run_parallel_annealing, run_refinement
from .reporting import save_results
from .validation import validate_ngram_directory

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Playfair cipher cracker using Simulated Annealing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Fast mode (exploratory):
    %(prog)s --cipher-file data/cipher.txt --mode fast
  
  Deep mode (thorough):
    %(prog)s --cipher-file data/cipher.txt --mode deep --workers 8
  
  With core blocks:
    %(prog)s --cipher-file data/cipher.txt --core-file data/core_blocks.txt --mode deep
        """
    )

    # Required arguments
    parser.add_argument(
        '--cipher-file',
        type=str,
        required=True,
        help='Path to cipher text file (required)'
    )

    # Optional input files
    parser.add_argument(
        '--clean-cipher-file',
        type=str,
        help='Path to cleaned cipher text file (optional)'
    )

    parser.add_argument(
        '--core-file',
        type=str,
        help='Path to core blocks file (optional)'
    )

    parser.add_argument(
        '--core-block',
        type=str,
        action='append',
        dest='core_blocks',
        help='Core block text (can be specified multiple times)'
    )

    # N-gram directory
    parser.add_argument(
        '--ngram-dir',
        type=str,
        default=get_default_ngram_dir(),
        help=f'Path to n-gram directory (default: {get_default_ngram_dir()})'
    )

    # Execution mode
    parser.add_argument(
        '--mode',
        type=str,
        choices=['fast', 'deep'],
        default='fast',
        help='Execution mode: fast (exploratory) or deep (thorough)'
    )

    # Parallelization
    parser.add_argument(
        '--workers',
        type=int,
        default=max(1, get_cpu_count() - 1),
        help=f'Number of parallel workers (default: CPU count - 1 = {max(1, get_cpu_count() - 1)})'
    )

    # Override mode defaults
    parser.add_argument(
        '--restarts',
        type=int,
        help='Number of restarts (overrides mode default)'
    )

    parser.add_argument(
        '--iters',
        type=int,
        help='Iterations per restart (overrides mode default)'
    )

    # Decode-only mode
    parser.add_argument(
        '--decode-only',
        action='store_true',
        help='Decode with known key without running simulated annealing'
    )

    parser.add_argument(
        '--known-keyword',
        type=str,
        help='Known Playfair keyword (requires --decode-only)'
    )

    parser.add_argument(
        '--known-matrix',
        type=str,
        help='Known Playfair matrix as 25-letter string (requires --decode-only)'
    )

    # Initial key for local search
    parser.add_argument(
        '--initial-keyword',
        type=str,
        help='Initial Playfair keyword for local search'
    )

    parser.add_argument(
        '--initial-matrix',
        type=str,
        help='Initial Playfair matrix as 25-letter string for local search'
    )

    parser.add_argument(
        '--initial-key-file',
        type=str,
        help='File containing initial matrices (one per line)'
    )

    parser.add_argument(
        '--local-search',
        action='store_true',
        help='Local search mode: explore neighborhood of initial key'
    )

    parser.add_argument(
        '--initial-mutation-radius',
        type=int,
        help='Max mutations for initial key perturbation (default: mode-dependent)'
    )

    parser.add_argument(
        '--seed',
        type=int,
        default=12345,
        help='Base random seed (default: 12345)'
    )

    parser.add_argument(
        '--top-k',
        type=int,
        help='Number of top results to keep (overrides mode default)'
    )

    # Output
    parser.add_argument(
        '--output-dir',
        type=str,
        default='output',
        help='Output directory (default: output)'
    )

    parser.add_argument(
        '--checkpoint-every',
        type=int,
        default=0,
        help='Save checkpoint every N restarts (0 = disabled, default: 0)'
    )

    # Flags
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Strict mode: error on odd-length cipher'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Minimal output'
    )

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    #  Validate decode-only arguments
    if args.decode_only:
        if not args.known_keyword and not args.known_matrix:
            logger.error("--decode-only requires either --known-keyword or --known-matrix")
            return 1
        if args.known_keyword and args.known_matrix:
            logger.error("--known-keyword and --known-matrix are mutually exclusive")
            return 1
    elif args.known_keyword or args.known_matrix:
        logger.warning("--known-keyword/--known-matrix specified without --decode-only. Ignoring.")

    # Setup logging
    setup_logging(verbose=args.verbose, quiet=args.quiet)

    logger.info("=" * 60)
    logger.info("Playfair Cipher Cracker - Simulated Annealing")
    logger.info("=" * 60)

    # Load configuration
    config = get_mode_config(args.mode)

    # Override with command-line arguments
    if args.restarts is not None:
        config.restarts = args.restarts
    if args.iters is not None:
        config.iters = args.iters
    if args.top_k is not None:
        config.top_k = args.top_k

    logger.info(f"Mode: {args.mode}")
    logger.info(f"Workers: {args.workers}")
    logger.info(f"Restarts: {config.restarts}")
    logger.info(f"Iterations per restart: {config.iters:,}")
    logger.info(f"Top-K: {config.top_k}")
    logger.info(f"Base seed: {args.seed}")

    # Load cipher text
    logger.info(f"Loading cipher from: {args.cipher_file}")
    cipher_text = read_file_safe(args.cipher_file)

    # Use clean cipher if provided
    if args.clean_cipher_file:
        logger.info(f"Loading clean cipher from: {args.clean_cipher_file}")
        cipher_text = read_file_safe(args.clean_cipher_file)

    # Preprocess cipher
    logger.info("Preprocessing cipher...")
    cipher_data = preprocess_cipher(cipher_text, strict=args.strict)
    logger.info(f"Cipher length: {len(cipher_data[0])} characters, {len(cipher_data[1])} pairs")
    logger.info(f"Unique pairs: {len(cipher_data[3])}")

    # Load core blocks if provided
    core_data = None
    if args.core_file or args.core_blocks:
        core_text = ""

        if args.core_file:
            logger.info(f"Loading core blocks from: {args.core_file}")
            core_text = read_file_safe(args.core_file)

        if args.core_blocks:
            logger.info(f"Adding {len(args.core_blocks)} core blocks from command line")
            core_text += "\n".join(args.core_blocks)

        logger.info("Preprocessing core blocks...")
        core_data = preprocess_cipher(core_text, strict=args.strict)
        logger.info(f"Core length: {len(core_data[0])} characters, {len(core_data[1])} pairs")

    # Validate n-gram directory
    logger.info(f"Validating n-gram directory: {args.ngram_dir}")
    metadata, validation_ok = validate_ngram_directory(args.ngram_dir, ALPHABET)
    
    if not validation_ok:
        logger.error("N-gram directory validation failed!")
        logger.error("Please check that the n-gram files are correct for alphabet base 25")
        return 1
    
    # Load n-gram models
    logger.info(f"Loading n-gram models from: {args.ngram_dir}")
    ngram_model = load_ngram_model(args.ngram_dir)

    logger.info(f"Quadgrams: loaded")
    if ngram_model.has_trigrams():
        logger.info(f"Trigrams: loaded")
    if ngram_model.has_inword():
        logger.info(f"Inword quadgrams: loaded")
    if ngram_model.has_letters():
        logger.info(f"Letter frequencies: loaded")

    # Prepare scoring data
    logger.info("Preparing scoring data...")
    scoring_data = prepare_scoring_data(cipher_data, core_data)

    # Prepare n-gram arrays
    ngram_arrays = {
        'quad_continuous': ngram_model.quad_continuous,
        'tri_continuous': ngram_model.tri_continuous,
        'quad_inword': ngram_model.quad_inword,
        'letter_logprob': ngram_model.letter_logprob,
    }
    
    # DECODE-ONLY MODE
    if args.decode_only:
        from .utils import key_from_keyword, key_from_matrix, key_to_text, validate_key
        from .decode import decode_with_known_key, save_decode_results
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("DECODE-ONLY MODE")
        logger.info("Using known key/matrix, annealing disabled")
        logger.info("=" * 60)
        
        # Build key from keyword or matrix
        try:
            if args.known_keyword:
                logger.info(f"Building key from keyword: {args.known_keyword}")
                key = key_from_keyword(args.known_keyword)
                logger.info(f"Key generated: {key_to_text(key)}")
            else:  # known_matrix
                logger.info(f"Building key from matrix: {args.known_matrix}")
                key = key_from_matrix(args.known_matrix)
                logger.info(f"Key loaded: {key_to_text(key)}")
            
            # Validate key
            validate_key(key)
            logger.info("✓ Key validation passed")
            
        except ValueError as e:
            logger.error(f"Invalid key: {e}")
            return 1
        
        # Decode with known key
        logger.info("Decrypting with known key...")
        result = decode_with_known_key(
            cipher_data=cipher_data,
            key=key,
            ngram_model=ngram_model,
            core_data=core_data,
        )
        
        logger.info(f"✓ Decryption complete")
        logger.info(f"Plaintext length: {len(result.plaintext)} characters")
        logger.info(f"Quadgram score: {result.scores['quad_continuous']:.4f}")
        
        # Collect warnings
        warnings = []
        if len(cipher_data[0]) % 2 != 0:
            warnings.append("Cipher length was odd, last character ignored")
        
        # Save results
        logger.info("")
        logger.info("=" * 60)
        logger.info("Saving decode-only results...")
        logger.info("=" * 60)
        
        output_path = Path(args.output_dir)
        save_decode_results(
            result=result,
            output_dir=output_path,
            cipher_file=args.cipher_file,
            cipher_length=len(cipher_data[0]),
            keyword=args.known_keyword,
            matrix_str=args.known_matrix or key_to_text(key),
            warnings=warnings,
        )
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("DECODE-ONLY COMPLETE")
        logger.info("=" * 60)
        logger.info(f"✓ Results saved to: {output_path}")
        logger.info(f"✓ Review decode_report.md for detailed analysis")
        logger.info(f"✓ Plaintext preview (first 100 chars):")
        logger.info(f"   {result.plaintext[:100]}")
        
        return 0

    # Run parallel annealing
    logger.info("")
    logger.info("=" * 60)
    logger.info("Starting annealing search...")
    logger.info("=" * 60)

    results = run_parallel_annealing(
        n_restarts=config.restarts,
        n_workers=args.workers,
        base_seed=args.seed,
        config=config,
        scoring_data=scoring_data,
        ngram_arrays=ngram_arrays,
        top_k=config.top_k,
        verbose=args.verbose,
        quiet=args.quiet,
    )

    logger.info(f"Search complete. Found {len(results)} unique solutions.")

    if results:
        logger.info(f"Best score: {results[0].score:.4f}")

    # Run refinement for deep mode
    if args.mode == 'deep' and results:
        logger.info("")
        logger.info("=" * 60)
        logger.info("Running refinement on top results...")
        logger.info("=" * 60)

        # Take top 20 for refinement
        top_for_refinement = results[:min(20, len(results))]

        refined_results = run_refinement(
            initial_results=top_for_refinement,
            refinement_config=DEEP_REFINEMENT,
            base_seed=args.seed,
            n_workers=args.workers,
            scoring_data=scoring_data,
            ngram_arrays=ngram_arrays,
            verbose=args.verbose,
            quiet=args.quiet,
        )

        logger.info(f"Refinement complete.")

        if refined_results:
            logger.info(f"Best refined score: {refined_results[0].score:.4f}")

            # Use refined results
            results = refined_results[:config.top_k]

    # Save results
    logger.info("")
    logger.info("=" * 60)
    logger.info("Saving results...")
    logger.info("=" * 60)

    output_path = Path(args.output_dir)

    # Prepare config dict for saving
    config_used = {
        'mode': args.mode,
        'workers': args.workers,
        'restarts': config.restarts,
        'iters': config.iters,
        'seed': args.seed,
        'top_k': config.top_k,
        'w_full': config.w_full,
        'w_core': config.w_core,
        'w_tri': config.w_tri,
        'w_inword': config.w_inword,
        'w_letter': config.w_letter,
        'T0': config.T0,
        'cooling': config.cooling,
        'cipher_file': args.cipher_file,
        'ngram_dir': args.ngram_dir,
    }

    if args.clean_cipher_file:
        config_used['clean_cipher_file'] = args.clean_cipher_file
    if args.core_file:
        config_used['core_file'] = args.core_file

    save_results(
        results=results,
        output_dir=output_path,
        cipher_data=cipher_data,
        core_data=core_data,
        mode=args.mode,
        config_used=config_used,
    )

    logger.info("")
    logger.info("=" * 60)
    logger.info("DONE")
    logger.info("=" * 60)

    if results:
        logger.info(f"✓ Best score: {results[0].score:.4f}")
        logger.info(f"✓ Results saved to: {output_path}")
        logger.info(f"✓ Review report.md for detailed analysis")
    else:
        logger.warning("No results found. Try adjusting parameters.")

    return 0


if __name__ == '__main__':
    sys.exit(main())

