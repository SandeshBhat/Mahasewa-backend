#!/bin/bash

# Quick script to deploy CORS fix to VPS
# This will pull latest code and restart the backend

set -e

echo "🚀 Deploying CORS Fix to Backend..."
echo ""

# VPS connection details (update if different)
VPS_HOST="srv1110921.hstgr.cloud"
VPS_USER="sandesh"
VPS_DIR="~/mahasewa-backend"

echo "📋 Step 1: Connecting to VPS..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'

echo "📥 Step 2: Pulling latest code..."
cd ~/mahasewa-backend

# Check if git repo exists
if [ -d ".git" ]; then
    echo "   Pulling from git..."
    git pull origin main || echo "   ⚠️  Git pull failed - continuing with restart"
else
    echo "   ⚠️  Not a git repo - will restart with existing code"
fi

echo ""
echo "🔄 Step 3: Restarting backend service..."

# Check if using Docker Compose
if [ -f "docker-compose.yml" ]; then
    echo "   Using Docker Compose..."
    docker-compose restart backend || docker-compose restart || echo "   ⚠️  Restart failed"
    
    # If backend service name is different, try common names
    docker-compose ps | grep -q "backend\|api\|fastapi" || {
        echo "   Trying to restart all services..."
        docker-compose restart
    }
    
    echo "   ✅ Docker services restarted"
    
# Check if using systemd
elif systemctl list-units | grep -q "mahasewa"; then
    echo "   Using systemd..."
    sudo systemctl restart mahasewa-backend || sudo systemctl restart mahasewa-api
    echo "   ✅ Systemd service restarted"
    
# Check if using PM2
elif command -v pm2 &> /dev/null && pm2 list | grep -q "mahasewa\|backend\|api"; then
    echo "   Using PM2..."
    pm2 restart mahasewa-backend || pm2 restart all
    echo "   ✅ PM2 process restarted"
    
else
    echo "   ⚠️  Could not detect service manager"
    echo "   Please restart manually:"
    echo "   - Docker: docker-compose restart"
    echo "   - Systemd: sudo systemctl restart mahasewa-backend"
    echo "   - PM2: pm2 restart mahasewa-backend"
fi

echo ""
echo "⏳ Step 4: Waiting for service to start..."
sleep 5

echo ""
echo "🧪 Step 5: Testing backend health..."
curl -s https://api.mahasewa.org/health && echo "" || echo "   ⚠️  Health check failed"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Test login at: https://mahasewa.vercel.app/login"
echo "   2. Check browser console for CORS errors"
echo "   3. If still failing, check logs: docker-compose logs -f backend"

ENDSSH

echo ""
echo "🎉 Deployment script completed!"
echo ""
echo "⚠️  If you see errors, you may need to:"
echo "   1. SSH manually: ssh ${VPS_USER}@${VPS_HOST}"
echo "   2. Navigate: cd ~/mahasewa-backend"
echo "   3. Pull code: git pull origin main"
echo "   4. Restart: docker-compose restart"
