"""Pytest configuration and fixtures for ws-ctx-engine tests."""

from hypothesis import settings, Verbosity

# Configure hypothesis profiles for different testing scenarios
# CI profile: Thorough testing with verbose output for CI/CD pipelines
settings.register_profile(
    "ci",
    max_examples=100,
    verbosity=Verbosity.verbose
)

# Dev profile: Faster testing for local development
settings.register_profile(
    "dev",
    max_examples=20,
    verbosity=Verbosity.normal
)

# Debug profile: Minimal examples with detailed output for debugging
settings.register_profile(
    "debug",
    max_examples=10,
    verbosity=Verbosity.debug
)

# Use CI profile by default for thorough testing
settings.load_profile("ci")
