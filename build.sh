#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/src"
echo "Building agentic_chomsky_formalization/main.pdf ..."
pdflatex -interaction=nonstopmode main.tex
bibtex main || true
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
if [[ -f main.pdf ]]; then
  cp -f main.pdf ../main.pdf
  echo "Output: $(dirname "$0")/main.pdf"
fi
echo "Building peer_review_article.pdf ..."
pdflatex -interaction=nonstopmode peer_review_article.tex
if [[ -f peer_review_article.pdf ]]; then
  cp -f peer_review_article.pdf ../peer_review_article.pdf
  echo "Output: $(dirname "$0")/peer_review_article.pdf"
fi
echo "Done."
