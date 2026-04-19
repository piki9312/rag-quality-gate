"""English locale patterns (fallback)."""

from __future__ import annotations

import re

# English uses ASCII question mark
QUESTION_MARK = "?"

# No Japanese-specific patterns needed for English
JAPANESE_TEXT_RE = re.compile(r"[ぁ-んァ-ヶ一-龠々]")
ASCII_ALPHA_RE = re.compile(r"[A-Za-z]")
ASCII_LABEL_RE = re.compile(r"^[A-Za-z0-9_\- ]+$")
