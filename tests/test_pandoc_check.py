import pytest

def test_pypandoc_import():
    try:
        import pypandoc
        assert True
    except ImportError:
        pytest.fail("pypandoc is not installed")

def test_pandoc_version():
    import pypandoc
    # This might fail if pandoc is not found by pypandoc even if it's on system path
    version = pypandoc.get_pandoc_version()
    assert version is not None
    print(f"Pandoc version via pypandoc: {version}")
