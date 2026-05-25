#!/bin/bash
# Script di esempio per eseguire il Playfair Cracker

# Configurazione
CIPHER_FILE="data/cipher.txt"
NGRAM_DIR="assets/ngrams_paisa_alphabet25"
OUTPUT_DIR="output/run_$(date +%Y%m%d_%H%M%S)"

# Parametri di default
MODE="fast"
WORKERS=4
RESTARTS=""
ITERS=""

# Parsing argomenti
while [[ $# -gt 0 ]]; do
  case $1 in
    --deep)
      MODE="deep"
      shift
      ;;
    --workers)
      WORKERS="$2"
      shift 2
      ;;
    --restarts)
      RESTARTS="--restarts $2"
      shift 2
      ;;
    --iters)
      ITERS="--iters $2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  --deep        Use deep mode (default: fast)"
      echo "  --workers N   Number of workers (default: 4)"
      echo "  --restarts N  Number of restarts"
      echo "  --iters N     Iterations per restart"
      echo "  --help        Show this help"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Esegui il cracker
echo "============================================"
echo "Playfair Cracker - Quick Run Script"
echo "============================================"
echo "Mode:       $MODE"
echo "Workers:    $WORKERS"
echo "Output dir: $OUTPUT_DIR"
echo "============================================"
echo ""

uv run python -m playfair_cracker.cli \
  --cipher-file "$CIPHER_FILE" \
  --ngram-dir "$NGRAM_DIR" \
  --mode "$MODE" \
  --workers "$WORKERS" \
  $RESTARTS \
  $ITERS \
  --output-dir "$OUTPUT_DIR"

echo ""
echo "============================================"
echo "Results saved to: $OUTPUT_DIR"
echo "Review: $OUTPUT_DIR/report.md"
echo "============================================"

