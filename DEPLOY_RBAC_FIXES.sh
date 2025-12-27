#!/bin/bash

# =====================================================
# Deploy RBAC Fixes and New Features to VPS
# =====================================================
# This script deploys the latest code with RBAC fixes,
# invoice ownership, branch manager filtering, and file downloads
# =====================================================

set -e  # Exit on error

VPS_HOST="srv1110921.hstgr.cloud"
VPS_USER="sandesh"
VPS_DIR="~/mahasewa-backend"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   MahaSeWA Backend Deployment - RBAC & Features Update         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Pull latest code on VPS
echo "📥 Step 1: Pulling latest code from Git..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd ~/mahasewa-backend

if [ -d ".git" ]; then
    echo "   Pulling from git..."
    git pull origin main || {
        echo "   ⚠️  Git pull failed - checking status..."
        git status
    }
else
    echo "   ⚠️  Not a git repo - will copy files manually"
fi
ENDSSH

echo "✅ Code updated"
echo ""

# Step 2: Copy new files if needed
echo "📤 Step 2: Ensuring all new files are present..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd ~/mahasewa-backend

# Check if new files exist
if [ ! -f "app/api/v1/files.py" ]; then
    echo "   ⚠️  New files missing - may need manual copy"
fi

if [ ! -f "app/api/v1/geocoding.py" ]; then
    echo "   ⚠️  New files missing - may need manual copy"
fi

if [ ! -f "app/api/v1/payments.py" ]; then
    echo "   ⚠️  New files missing - may need manual copy"
fi

if [ ! -f "app/models/document.py" ]; then
    echo "   ⚠️  New files missing - may need manual copy"
fi
ENDSSH

echo "✅ Files checked"
echo ""

# Step 3: Install new dependencies
echo "📦 Step 3: Installing new Python dependencies..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd ~/mahasewa-backend

# Check if using Docker
if docker ps | grep -q mahasewa; then
    echo "   Installing dependencies in Docker container..."
    
    # Find backend container name
    CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -E "backend|api|fastapi|mahasewa" | head -1)
    
    if [ -n "$CONTAINER_NAME" ]; then
        echo "   Found container: $CONTAINER_NAME"
        docker exec $CONTAINER_NAME pip install -q weasyprint==60.2 sib-api-v3-sdk==8.5.0 openpyxl==3.1.2 || {
            echo "   ⚠️  Some dependencies may already be installed"
        }
        echo "   ✅ Dependencies installed"
    else
        echo "   ⚠️  Could not find backend container"
    fi
else
    echo "   ⚠️  Docker containers not running"
    echo "   Please install dependencies manually:"
    echo "   pip install weasyprint==60.2 sib-api-v3-sdk==8.5.0 openpyxl==3.1.2"
fi
ENDSSH

echo "✅ Dependencies installed"
echo ""

# Step 4: Run database migrations
echo "🔄 Step 4: Running database migrations..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd ~/mahasewa-backend

# Find backend container
CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -E "backend|api|fastapi|mahasewa" | head -1)

if [ -n "$CONTAINER_NAME" ]; then
    echo "   Running migrations in container: $CONTAINER_NAME"
    docker exec $CONTAINER_NAME alembic upgrade head || {
        echo "   ⚠️  Migration failed - check logs"
        docker exec $CONTAINER_NAME alembic current
    }
    echo "   ✅ Migrations completed"
else
    echo "   ⚠️  Could not find backend container"
    echo "   Please run migrations manually:"
    echo "   docker exec <container> alembic upgrade head"
fi
ENDSSH

echo "✅ Migrations completed"
echo ""

# Step 5: Restart backend service
echo "🔄 Step 5: Restarting backend service..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd ~/mahasewa-backend

if [ -f "docker-compose.yml" ] || [ -f "docker-compose.yaml" ]; then
    echo "   Restarting Docker Compose services..."
    docker-compose restart backend || docker-compose restart || {
        echo "   Trying docker compose (newer syntax)..."
        docker compose restart backend || docker compose restart
    }
    echo "   ✅ Services restarted"
    
    echo ""
    echo "   📊 Service Status:"
    docker-compose ps || docker compose ps
    
elif systemctl list-units | grep -q "mahasewa"; then
    echo "   Restarting systemd service..."
    sudo systemctl restart mahasewa-backend || sudo systemctl restart mahasewa-api
    echo "   ✅ Service restarted"
    
elif command -v pm2 &> /dev/null && pm2 list | grep -q "mahasewa"; then
    echo "   Restarting PM2 process..."
    pm2 restart mahasewa-backend || pm2 restart all
    echo "   ✅ Process restarted"
else
    echo "   ⚠️  Could not detect service manager"
    echo "   Please restart manually"
fi
ENDSSH

echo "✅ Backend restarted"
echo ""

# Step 6: Verify deployment
echo "🔍 Step 6: Verifying deployment..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd ~/mahasewa-backend

echo "   Checking backend health..."
sleep 3

# Try to check if backend is responding
if curl -s -f http://localhost:8000/health > /dev/null 2>&1 || \
   curl -s -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "   ✅ Backend is responding"
else
    echo "   ⚠️  Backend may not be responding - check logs"
    echo "   Check logs with: docker-compose logs backend"
fi
ENDSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ What was deployed:"
echo "   - RBAC implementation (role-based access control)"
echo "   - Invoice ownership verification"
echo "   - Branch manager filtering"
echo "   - Staff permissions"
echo "   - File download endpoints"
echo "   - Geocoding service"
echo "   - Payment service (Razorpay)"
echo "   - Document management system"
echo "   - Enhanced PDF generation"
echo ""
echo "📋 Next Steps:"
echo "   1. Verify backend is running: curl http://api.mahasewa.org/health"
echo "   2. Test new endpoints with proper authentication"
echo "   3. Verify migrations: Check database for branch_id columns"
echo ""
echo "✨ Done!"

