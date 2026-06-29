import unittest
import sys

from test_heavy_duty import HeavyDutySourceCodeTestCase
from test_statistics_impact_level import StatisticsImpactLevelTestCase
from test_statistics_bare_fiber_interruption import StatisticsBareFiberInterruptionTestCase

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite((
        loader.loadTestsFromTestCase(HeavyDutySourceCodeTestCase),
        loader.loadTestsFromTestCase(StatisticsImpactLevelTestCase),
        loader.loadTestsFromTestCase(StatisticsBareFiberInterruptionTestCase),
    ))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    with open('test_failures.txt', 'w', encoding='utf-8') as f:
        if not result.wasSuccessful():
            f.write("=== Failures Detail ===\n")
            for failure in result.failures:
                f.write(f"Test: {failure[0]}\n")
                f.write(f"Traceback:\n{failure[1]}\n")
                f.write("="*40 + "\n")
            sys.exit(1)
        else:
            f.write("All tests passed successfully!\n")
            sys.exit(0)
