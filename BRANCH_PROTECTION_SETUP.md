# Branch Protection Setup Guide

## Enable Branch Protection on GitHub

To ensure no code is merged into `main` unless CI succeeds, follow these steps:

### 1. Go to Repository Settings
1. Navigate to your repository on GitHub
2. Click **Settings** → **Branches**

### 2. Add Branch Protection Rule
1. Click **Add rule** or **Add branch protection rule**
2. In **Branch name pattern**, enter: `main`

### 3. Configure Protection Rules

Enable these settings:

#### ✅ Required Checks
- [x] **Require status checks to pass before merging**
- [x] **Require branches to be up to date before merging**

Select these required status checks:
- `detect-changes`
- `test-user-service`
- `test-api-gateway`
- `test-campaign-service`
- `test-donation-service`
- `test-banking-service`
- `test-payment-service`
- `test-notification-service`
- `test-frontend`
- `build`

#### ✅ Additional Recommended Settings
- [x] **Require a pull request before merging**
  - Required approvals: 1 (or more)
- [x] **Require conversation resolution before merging**
- [x] **Do not allow bypassing the above settings** (prevents admins from bypassing)

### 4. Save Changes
Click **Create** or **Save changes**

---

## How It Works

### On Pull Request:
1. **Change Detection**: Identifies which services changed
2. **Run Tests**: Only tests for changed services run
3. **Status Check**: PR cannot be merged unless all tests pass
4. **Build Skip**: Docker images are NOT built on PRs (only on push to main)

### On Push to Main:
1. **Change Detection**: Identifies which services changed
2. **Run Tests**: Only tests for changed services run
3. **Build Images**: Only changed services are built and pushed to DockerHub
4. **Deploy**: Only changed services are deployed to Kubernetes

---

## CI/CD Pipeline Features

### ✅ Smart Change Detection
- Uses `dorny/paths-filter` to detect which microservice folders changed
- Only runs tests/builds for modified services
- Saves time and CI resources

### ✅ Parallel Testing
- Each service's tests run in parallel
- Faster feedback on PRs
- Independent test jobs per service

### ✅ Test-Driven Deployment
- Build job requires all test jobs to pass
- Deploy job requires build to succeed
- Fail-fast: Stops pipeline on first test failure

### ✅ Efficient Builds
- Only builds Docker images for changed services
- Uses GitHub SHA as unique image tag
- Pushes only necessary images to DockerHub

### ✅ Targeted Deployments
- Only deploys changed services to Kubernetes
- Reduces deployment time
- Minimizes risk of unnecessary pod restarts

---

## Example Workflow

### Scenario: You modify only `payment-service/main.py`

**What happens:**

1. **PR Created**:
   - ✅ `detect-changes` → detects `payment-service` changed
   - ✅ `test-payment-service` → runs payment service tests
   - ⏭️ Other test jobs → skipped (no changes)
   - ⏭️ `build` → skipped (PR, not push to main)
   - **Result**: PR can be merged if tests pass

2. **PR Merged to Main**:
   - ✅ `detect-changes` → detects `payment-service` changed
   - ✅ `test-payment-service` → runs payment service tests
   - ⏭️ Other test jobs → skipped
   - ✅ `build` → builds ONLY payment-service Docker image
   - ✅ `deploy` → deploys ONLY payment-service to K8s
   - **Result**: Only payment-service updated, 8x faster than full rebuild

---

## Skip CI/CD Manually

To skip CI or CD (for README updates, etc.):

```bash
# Skip CI (no tests, no build)
git commit -m "update docs [skip ci]"

# Skip CD (tests + build run, but no deploy)
git commit -m "fix typo [skip cd]"
```

---

## Test Pipeline Locally

### Add tests to your services:

```bash
# Example for payment-service
mkdir payment-service/tests
touch payment-service/tests/__init__.py
touch payment-service/tests/test_main.py
```

### Sample test file:
```python
# payment-service/tests/test_main.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

---

## Troubleshooting

### Tests not running?
- Check that test files exist in `service-name/tests/`
- Verify test discovery: `pytest tests/ -v`

### Build failing?
- Check Docker credentials in GitHub Secrets
- Verify Dockerfile exists in service root

### Deploy failing?
- Check DigitalOcean credentials
- Verify deployment names match K8s cluster
- Check kubectl context: `kubectl config current-context`

---

## GitHub Secrets Required

Ensure these secrets are set in GitHub repository settings:

- `DOCKERHUB_USERNAME` - Your DockerHub username
- `DOCKERHUB_TOKEN` - DockerHub access token
- `DIGITALOCEAN_ACCESS_TOKEN` - DigitalOcean API token
- `DO_CLUSTER_NAME` - Your Kubernetes cluster name

**Path**: Repository → Settings → Secrets and variables → Actions
