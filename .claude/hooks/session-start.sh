#!/bin/bash
set -euo pipefail

# Only run in remote Claude Code on the web environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo "==> Installing markitdown from repository source..."

# Install markitdown with the most useful document-conversion extras:
#   pdf    — PDF files (pdfminer, pdfplumber)
#   docx   — Word documents (mammoth, lxml)
#   pptx   — PowerPoint files (python-pptx)
#   xlsx   — Excel files (pandas, openpyxl)
#   xls    — Legacy Excel files (pandas, xlrd)
pip install -q --no-cache-dir \
  "$CLAUDE_PROJECT_DIR/packages/markitdown[pdf,docx,pptx,xlsx,xls]"

# openai is needed for LLM-based image captioning (optional but useful)
pip install -q --no-cache-dir openai

echo "==> markitdown installation complete."
echo "    Convert any file:  markitdown path/to/file.pdf"
echo "    Convert from URL:  markitdown https://example.com/doc.pdf"
echo "    Convert to stdout: markitdown -o output.md path/to/file.docx"
