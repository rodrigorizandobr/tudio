#!/bin/bash

# Configuration
APP_HOST="0.0.0.0"
APP_PORT="8000"
PID_FILE="tudio_pid.txt"

echo "============================================"
echo "   Tudio V2 - Automated Startup Script"
echo "============================================"

# 1. Environment Checks
echo "[1/4] Checking Environment..."
if command -v python &> /dev/null; then
    PYTHON_EXEC="python"
elif command -v python3 &> /dev/null; then
    PYTHON_EXEC="python3"
else
    echo "ERROR: python or python3 could not be found."
    exit 1
fi

echo "Using Python interpreter: $($PYTHON_EXEC --version) at $(command -v $PYTHON_EXEC)"

if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found."
    exit 1
fi

# 2. Install Dependencies (Build Step)
echo "[2/4] Installing/Updating Dependencies..."
$PYTHON_EXEC -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies."
    exit 1
fi

# 2.5 Infrastructure Checks (Datastore)
echo "[2.5/4] Checking Google Cloud Infrastructure..."
if command -v gcloud &> /dev/null; then
    # Check if project ID is set in gcloud
    GCLOUD_PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$GCLOUD_PROJECT" ]; then
        echo "WARNING: No gcloud project set. Skipping Datastore check."
    else
        echo "Active Project: $GCLOUD_PROJECT"
        
        # Check for active account
        GCLOUD_ACCOUNT=$(gcloud config get-value account 2>/dev/null)
        if [ -z "$GCLOUD_ACCOUNT" ]; then
            echo "WARNING: No active gcloud account found for CLI."
            echo "Running 'gcloud auth login' to enable database creation..."
            gcloud auth login
        fi

        # Check if database (default) exists
        # We suppress output to avoid clutter, checking exit code or output string
        DB_LIST=$(gcloud firestore databases list --format="value(name)" --filter="name:projects/$GCLOUD_PROJECT/databases/\(default\)" 2>/dev/null)
        
        if [ -z "$DB_LIST" ]; then
            echo "Datastore (default) not found. Attempting to create..."
            gcloud firestore databases create --location=us-central1 --type=datastore-mode --quiet
            if [ $? -eq 0 ]; then
                echo "SUCCESS: Datastore created."
            else
                echo "WARNING: Failed to create Datastore. Startup might fail if it doesn't exist."
                echo "Try running: gcloud firestore databases create --location=us-central1 --type=datastore-mode"
            fi
        else
            echo "Datastore (default) exists."
        fi
    fi
else
    echo "WARNING: gcloud CLI not found. Skipping infrastructure automation."
fi

# 5. Start Application
echo "[5/6] Starting Uvicorn Server..."

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p $OLD_PID > /dev/null; then
        echo "WARNING: App seems to be already running with PID $OLD_PID."
        echo "Please stop it first using ./stop.sh or kill it manually."
        exit 1
    else
        echo "Found stale PID file. Removing..."
        rm "$PID_FILE"
    fi
fi

# Parse Arguments
TEST_MODE=0
SKIP_E2E=0
RUN_TESTS=0

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --test-mode) 
            TEST_MODE=1 
            ;;
        --skip-e2e) 
            SKIP_E2E=1 
            ;;
        --test)
            RUN_TESTS=1
            ;;
    esac
    shift
done

# 3. Quality Gates (Test & Coverage) - SKIPPED BY DEFAULT
echo "[3/5] Running Quality Gates..."
if [ $RUN_TESTS -eq 1 ] && [ "$APP_ENV" != "prd" ]; then
    echo "Test flag detected. Running all tests..."
    
    # 3.1 Backend Unit Tests
    echo "--> [Gate 1] Backend Unit Tests (Target: 70% coverage)"
    $PYTHON_EXEC -m pytest backend/tests/unit --cov=backend --cov-report=term-missing --cov-fail-under=70
    if [ $? -ne 0 ]; then
        echo "❌ Backend Unit Tests FAILED or Coverage below 70%."
        exit 1
    fi

    # 3.2 Backend Integration Tests
    echo "--> [Gate 2] Backend Integration Tests (Target: 80% coverage)"
    # Note: Coverage append to unit tests
    $PYTHON_EXEC -m pytest backend/tests/integration --cov=backend --cov-append --cov-report=term-missing --cov-fail-under=80
    if [ $? -ne 0 ]; then
        echo "❌ Backend Integration Tests FAILED or Coverage below 80%."
        exit 1
    fi

    # 3.3 Frontend Unit Tests
    if command -v npm &> /dev/null; then
        echo "--> [Gate 3] Frontend Unit Tests"
        cd frontend
        npm run test:unit
        if [ $? -ne 0 ]; then
             echo "❌ Frontend Unit Tests FAILED."
             exit 1
        fi
        cd ..
    else
        echo "⚠️ npm not found. Skipping Frontend Tests."
    fi

    # 3.4 E2E Tests (Playwright) - MOVED TO AFTER START
    echo "ℹ️ E2E Tests will run after server startup."
    
    echo "✅ Pre-flight Quality Gates Passed!"
else
    echo "Skipping Quality Gates (Pass --test to run them)."
fi

# 4. Build Frontend
echo "[4/6] Building Frontend..."
if command -v npm &> /dev/null; then
    cd frontend
    echo "Cleaning old build..."
    rm -rf dist
    echo "Installing frontend dependencies..."
    npm install --silent
    echo "Building frontend..."
    npm run build
    if [ $? -ne 0 ]; then
        echo "ERROR: Frontend build failed."
        exit 1
    fi
    cd ..
    echo "Frontend built successfully."
else
    echo "WARNING: npm not found. Skipping frontend build. UI might be outdated."
fi

# ... (rest of the startup logic) ...
export BYPASS_RATE_LIMIT=True

if [ $TEST_MODE -eq 1 ]; then
    echo "⚠️ STARTING IN TEST MODE (TESTING=True) - Mocks Enabled"
    export TESTING=True
fi

nohup $PYTHON_EXEC -m uvicorn backend.main:app --host $APP_HOST --port $APP_PORT --reload > storage/logs/server.out 2>&1 &
NEW_PID=$!

echo $NEW_PID > "$PID_FILE"

echo "SUCCESS! Tudio V2 started with PID: $NEW_PID"
echo "Docs: http://localhost:$APP_PORT/doc"

# 6. Post-Start E2E Tests
if [ $RUN_TESTS -eq 1 ] && [ "$APP_ENV" != "prd" ] && [ $SKIP_E2E -eq 0 ]; then
    echo "[6/6] Running Post-Start Quality Gates (E2E)..."
    
    # Wait for Server
    echo "Waiting for server to be ready..."
    MAX_RETRIES=30
    COUNT=0
    SERVER_READY=0
    
    while [ $COUNT -lt $MAX_RETRIES ]; do
        if curl -s http://$APP_HOST:$APP_PORT/health > /dev/null; then
            SERVER_READY=1
            break
        fi
        echo -n "."
        sleep 1
        COUNT=$COUNT+1
    done
    echo ""
    
    if [ $SERVER_READY -eq 1 ]; then
        echo "Server is UP. Running E2E Tests..."
        
        if command -v npx &> /dev/null; then
             echo "--> [Gate 4] E2E Tests (Playwright)"
             # Run playwright sequentially to avoid resource contention/rate limits
             (cd frontend && npx playwright test --workers=1)
             if [ $? -ne 0 ]; then
                 echo "❌ E2E Tests FAILED."
                 echo "Stopping server due to Quality Gate failure..."
                 kill $NEW_PID
                 rm "$PID_FILE"
                 exit 1
             else
                 echo "✅ E2E Tests PASSED!"
             fi
        else
             echo "⚠️ npx not found. Skipping E2E."
        fi
    else
        echo "❌ Server failed to start within timeout."
        kill $NEW_PID
        rm "$PID_FILE"
        exit 1
    fi
fi

# 7. Cleanup Test Data
if [ $RUN_TESTS -eq 1 ] && [ "$APP_ENV" != "prd" ]; then
    echo "[7/7] Cleaning up test data..."
    $PYTHON_EXEC backend/scripts/cleanup_test_data.py
    if [ $? -eq 0 ]; then
        echo "✅ Test data cleanup successful."
    else
        echo "⚠️ Test data cleanup failed (non-critical)."
    fi
fi

echo "--------------------------------------------"
echo "Streaming logs (Press Ctrl+C to stop viewing logs, App will continue running)..."
echo "============================================"
tail -f storage/logs/server.out
