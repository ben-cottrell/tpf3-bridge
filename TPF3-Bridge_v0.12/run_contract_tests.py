"""Run reusable offline contract checks without retaining reports or logs."""
from pathlib import Path
import unittest

if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(str(root / 'validation'), pattern='test_contracts.py')
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
