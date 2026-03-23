import os
import subprocess
import sys
import time

def run_command(command, cwd=None, env=None):
    print(f"Running: {command}")
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=cwd,
        env=env
    )
    for line in iter(process.stdout.readline, ""):
        print(line, end="")
    process.stdout.close()
    return process.wait()

def cleanup_ports(ports):
    print(f"Cleaning up ports: {ports}")
    for port in ports:
        try:
            # Get PIDs using the port
            cmd = f"lsof -ti:{port}"
            pids = subprocess.check_output(cmd, shell=True, text=True).strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"Killing process {pid} on port {port}")
                    subprocess.run(f"kill -9 {pid}", shell=True)
        except subprocess.CalledProcessError:
            print(f"Port {port} is already free.")

def main():
    print("=== Tudio V2 Autonomous Quality Verification ===")
    
    # 1. Cleanup
    cleanup_ports([8000, 5173])
    
    # 2. Setup Environment
    env = os.environ.copy()
    
    # Add common npm/npx locations to PATH for Mac/Linux
    extra_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
    env["PATH"] = ":".join(extra_paths) + ":" + env.get("PATH", "")
    
    env["PYTHONPATH"] = f"{os.getcwd()}:{env.get('PYTHONPATH', '')}"
    env["TESTING"] = "True"
    env["BYPASS_RATE_LIMIT"] = "True"
    
    env["USE_E2E_MOCKS"] = "False"  # Unit tests should NOT use fallback mocks
    
    # 3. Backend Unit & Integration Tests (Coverage 85%)
    print("\n--- Running Backend Tests (Unit + Integration) ---")
    exit_code = run_command(
        f"{sys.executable} -m pytest backend/tests/ --cov=backend --cov-report=term-missing --cov-fail-under=85",
        env=env
    )
    if exit_code != 0:
        print("❌ Backend Tests failed or Coverage below 85%.")
        sys.exit(1)
    
    # 4. Frontend Unit Tests
    print("\n--- Running Frontend Unit Tests ---")
    exit_code = run_command("cd frontend && npm run test:unit", env=env)
    if exit_code != 0:
        print("❌ Frontend Unit Tests failed.")
        sys.exit(1)
        
    # 5. Start Temporary Server for E2E
    print("\n--- Starting Temporary Server for E2E ---")
    e2e_env = env.copy()
    e2e_env["USE_E2E_MOCKS"] = "True"  # Server should use mocks for performance
    
    server_process = subprocess.Popen(
        f"{sys.executable} -m uvicorn backend.main:app --host 0.0.0.0 --port 8000",
        shell=True,
        env=e2e_env
    )
    
    # Wait for server
    print("Waiting for server...")
    time.sleep(5) 
    
    # 6. Run E2E Tests
    print("\n--- Running E2E Tests (Playwright) ---")
    e2e_exit_code = run_command("cd frontend && npx playwright test --workers=1", env=env)
    
    # Kill server
    print("\nCleaning up server...")
    server_process.terminate()
    cleanup_ports([8000])
    
    if e2e_exit_code != 0:
        print("❌ E2E Tests failed.")
        sys.exit(1)
        
    print("\n✅ ALL QUALITY GATES PASSED! Ready for delivery.")

if __name__ == "__main__":
    main()
