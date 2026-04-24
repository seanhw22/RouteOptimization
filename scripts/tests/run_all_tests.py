"""
Master test runner - Runs all test scripts in sequence
Validates the complete MDVRP refactoring implementation
"""

import subprocess
import sys


def run_test(script_name, description):
    """Run a test script and report results"""
    print("\n" + "=" * 70)
    print(f"Running: {description}")
    print(f"Script: {script_name}")
    print("=" * 70)

    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=False,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print(f"\n[OK] {description} - PASSED")
            return True
        else:
            print(f"\n[ERROR] {description} - FAILED (exit code: {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        print(f"\n[ERROR] {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"\n[ERROR] {description} - ERROR: {e}")
        return False


def main():
    """Run all tests in sequence"""
    print("=" * 70)
    print("MDVRP REFACTORING - MASTER TEST SUITE")
    print("=" * 70)
    print("\nThis will run all test scripts to validate the implementation.")
    print("Estimated total time: ~30 seconds\n")

    tests = [
        ("test_integration.py", "Integration Tests (All Solvers with CSV)"),
        ("test_export.py", "Export Format Tests (CSV, PDF, GeoJSON)"),
        ("test_edge_cases.py", "Edge Case and Error Handling Tests"),
        ("../algorithms/benchmark_performance.py", "Performance Benchmarking"),
    ]

    results = {}
    for script, description in tests:
        results[description] = run_test(script, description)

    # Final summary
    print("\n" + "=" * 70)
    print("TEST SUITE SUMMARY")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for description, result in results.items():
        status = "[OK] PASSED" if result else "[ERROR] FAILED"
        print(f"{status} - {description}")

    print("\n" + "-" * 70)
    print(f"Total: {passed}/{total} test suites passed")

    if passed == total:
        print("\n[OK] ALL TESTS PASSED! Implementation is complete and validated.")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} test suite(s) failed. Please review.")
        return 1


if __name__ == "__main__":
    exit(main())
