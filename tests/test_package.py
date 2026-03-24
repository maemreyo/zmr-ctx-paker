"""Basic tests to verify package structure."""

import context_packer


def test_package_version():
    """Test that package version is defined."""
    assert hasattr(context_packer, "__version__")
    assert context_packer.__version__ == "0.1.0"


def test_package_imports():
    """Test that package can be imported."""
    import context_packer
    
    assert context_packer is not None
