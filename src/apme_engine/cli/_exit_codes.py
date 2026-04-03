"""CLI exit code constants.

Aligns with conventions used by ruff, mypy, and shellcheck:
  0 = success (no violations)
  1 = violations found (actionable)
  2 = error (infrastructure / usage)
"""

EXIT_SUCCESS: int = 0
EXIT_VIOLATIONS: int = 1
EXIT_ERROR: int = 2
