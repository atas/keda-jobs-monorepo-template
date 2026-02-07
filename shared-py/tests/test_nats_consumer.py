from shared_py.nats_consumer import run_consumer


def test_import():
    """Verify the module imports and run_consumer is callable."""
    assert callable(run_consumer)
