#!/bin/bash

# Uso: ./convert_md.sh [notebook.ipynb]
# Default: analisi_frequenze.ipynb

NOTEBOOK="${1:-analisi_frequenze.ipynb}"

if [ ! -f "$NOTEBOOK" ]; then
    echo "Errore: file '$NOTEBOOK' non trovato"
    exit 1
fi

echo "Conversione di: $NOTEBOOK"

# Sanificazione del notebook: rimuove i campi proprietari JetBrains
python - <<PY
import nbformat
from pathlib import Path
p = Path('$NOTEBOOK')
nb = nbformat.read(p, as_version=4)
for cell in nb.get("cells", []):
    for out in cell.get("outputs", []):
        if isinstance(out, dict):
            out.pop("jetTransient", None)
nbformat.write(nb, p)
PY

# Conversione a Markdown
jupyter-nbconvert "$NOTEBOOK" --to markdown \
  --TemplateExporter.exclude_input=True \
  --TemplateExporter.exclude_input_prompt=True

echo "Completato: ${NOTEBOOK%.ipynb}.md"
