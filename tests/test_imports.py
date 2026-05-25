def test_engine_package_imports():
    import engine

    assert engine.__version__ == "0.1.0"
