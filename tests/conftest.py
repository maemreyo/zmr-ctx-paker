"""Pytest configuration and fixtures for ws-ctx-engine tests."""

import os

from hypothesis import Verbosity, settings

# Prevent macOS segfaults from PyTorch tokenizer parallelism in any test that
# imports sentence-transformers or tiktoken.  Must be set before heavy imports.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")

# Hypothesis profiles
# ci:    100 examples — use in CI via: pytest --hypothesis-profile=ci
# dev:   20 examples  — default for local dev runs
# debug: 5 examples   — fast smoke-check
settings.register_profile("ci", max_examples=100, verbosity=Verbosity.verbose)
settings.register_profile("dev", max_examples=20, verbosity=Verbosity.normal)
settings.register_profile("debug", max_examples=5, verbosity=Verbosity.debug)

# Default to dev profile; CI overrides with --hypothesis-profile=ci
settings.load_profile("dev")
