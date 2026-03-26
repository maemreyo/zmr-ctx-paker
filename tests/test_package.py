"""Basic tests to verify package structure."""

import ws_ctx_engine


def test_package_version():
    """Test that package version is defined."""
    assert hasattr(ws_ctx_engine, "__version__")
    assert ws_ctx_engine.__version__ == "0.1.0"


def test_package_imports():
    """Test that package can be imported."""
    import ws_ctx_engine

    assert ws_ctx_engine is not None
