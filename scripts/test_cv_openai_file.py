#!/usr/bin/env python3
"""
Lokal sinov: PDF/DOCX yo‘lini bering.

  cd ai_cv_system
  export OPENAI_API_KEY=sk-...   # yoki
  export GEMINI_API_KEY=...      # (auto rejimda OpenAI 429 bo‘lsa ishlatiladi)

  python scripts/test_cv_openai_file.py "/path/to/CV.pdf"
"""
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from services.cv_file_extract import extract_structured_profile_from_cv_file
import json


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_cv_openai_file.py /path/to/file.pdf")
        sys.exit(1)
    path = sys.argv[1]
    has_oai = bool((os.getenv("OPENAI_API_KEY") or "").strip())
    has_gem = bool(
        (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    )
    if not has_oai and not has_gem:
        print("Set OPENAI_API_KEY and/or GEMINI_API_KEY (Google AI Studio) in env")
        sys.exit(1)
    out = extract_structured_profile_from_cv_file(path)
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
