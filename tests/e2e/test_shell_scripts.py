import pytest
import subprocess
import os
import time
import signal

@pytest.mark.e2e
def test_shell_scripts_flow():
    """
    Verifies that start.sh and stop.sh work as expected.
    This acts as a coverage test for the shell scripts.
    """
    
    # Ensure no previous process is running
    if os.path.exists("tudio_pid.txt"):
        subprocess.run(["./stop.sh"], check=False)
        time.sleep(1)

    # 1. Test start.sh
    print("\nRunning start.sh...")
    # Using specific env to ensure we don't accidentally rely on external state if possible,
    # but here we want to test the user's environment behavior, so we pass os.environ.
    # We pipe stdout/stderr to avoid cluttering test output, but capture for debugging.
    start_proc = subprocess.Popen(
        ["./start.sh"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=".",
        text=True
    )
    
    # Wait a bit for script to execute install and start server
    # start.sh runs uvicorn in background (nohup) and exits.
    # So start_proc should exit with 0 quickly.
    
    try:
        stdout, stderr = start_proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        start_proc.kill()
        pytest.fail("start.sh timed out (took > 30s)")

    if start_proc.returncode != 0:
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        pytest.fail(f"start.sh failed with exit code {start_proc.returncode}")

    # Verify PID file exists
    assert os.path.exists("tudio_pid.txt"), "tudio_pid.txt not created"
    
    pid = ""
    with open("tudio_pid.txt", "r") as f:
        pid = f.read().strip()
    
    assert pid.isdigit(), f"Invalid PID format: {pid}"
    
    # Verify process is actually running
    try:
        os.kill(int(pid), 0) # Signal 0 checks existence
    except OSError:
        pytest.fail(f"Process {pid} is not running after start.sh")

    print(f"Application started with PID {pid}")
    
    # Allow uvicorn to startup fully to avoid race conditions with stop
    time.sleep(2)

    # 2. Test stop.sh
    print("Running stop.sh...")
    stop_proc = subprocess.run(
        ["./stop.sh"],
        capture_output=True,
        text=True
    )
    
    assert stop_proc.returncode == 0, f"stop.sh failed: {stop_proc.stderr}"
    assert not os.path.exists("tudio_pid.txt"), "tudio_pid.txt should be removed after stop.sh"

    # Verify process is gone
    try:
        os.kill(int(pid), 0)
        # If we reach here, process still exists
        pytest.fail(f"Process {pid} was not killed by stop.sh")
    except OSError:
        # Expected: Process not found
        pass
    
    print("Shell scripts verified successfully.")
