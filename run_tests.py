import os
import subprocess
import re
import sys

def run_test(filename):
    print(f"Running test: {filename} ", end="", flush=True)
    try:
        # Run main.py with the scm file
        result = subprocess.run(
            [sys.executable, "main.py", filename],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        output = result.stdout
        # Extract "Result: ..." lines
        actual_results = re.findall(r"Result: ([\d.-]+)", output)
        
        # Extract expected results from comments in the scm file
        with open(filename, 'r') as f:
            content = f.read()
        expected_results = re.findall(r";; Result: ([\d.-]+)", content)
        
        if not expected_results:
            print("[SKIPPED] (No expected results found in file)")
            return True

        if len(actual_results) != len(expected_results):
            print(f"[FAIL] (Result count mismatch: expected {len(expected_results)}, got {len(actual_results)})")
            print("Output:", output)
            return False
        
        all_passed = True
        for i, (actual, expected) in enumerate(zip(actual_results, expected_results)):
            # Compare floats with some tolerance
            if abs(float(actual) - float(expected)) > 0.0001:
                print(f"\n  [FAIL] at item {i+1}: expected {expected}, got {actual}")
                all_passed = False
        
        if all_passed:
            print("[PASS]")
            return True
        else:
            return False

    except subprocess.TimeoutExpired:
        print("[TIMEOUT]")
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def main():
    test_dir = "scms"
    test_files = sorted([
        os.path.join(test_dir, f) 
        for f in os.listdir(test_dir) 
        if f.startswith("test_level") and f.endswith(".scm")
    ])
    
    if not test_files:
        print("No test files found.")
        return

    passed_count = 0
    for test_file in test_files:
        if run_test(test_file):
            passed_count += 1
            
    print(f"\nSummary: {passed_count}/{len(test_files)} tests passed.")

if __name__ == "__main__":
    main()
