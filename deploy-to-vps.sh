#!/bin/bash

# MahaSeWA VPS Deployment Script
# This script automates the deployment of MahaSeWA infrastructure to srv1110921.hstgr.cloud

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   MahaSeWA VPS Deployment - srv1110921.hstgr.cloud            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

VPS_HOST="31.97.236.102"
VPS_USER="root"
VPS_DIR="~/mahasewa-backend"

echo "📋 Step 1: Creating directory on VPS..."
ssh ${VPS_USER}@${VPS_HOST} "mkdir -p ~/mahasewa-backend"

echo "✅ Directory created"
echo ""

echo "📤 Step 2: Copying Docker Compose configuration..."
scp docker-compose.production.yml ${VPS_USER}@${VPS_HOST}:${VPS_DIR}/docker-compose.yml

echo "✅ Docker Compose file uploaded"
echo ""

echo "📤 Step 3: Copying environment template..."
scp env.production.example ${VPS_USER}@${VPS_HOST}:${VPS_DIR}/.env

echo "✅ Environment template uploaded"
echo ""

echo "🔐 Step 4: Generating secure passwords..."
echo ""
echo "──────────────────────────────────────────────────────────────"
echo "SAVE THESE PASSWORDS SECURELY!"
echo "──────────────────────────────────────────────────────────────"
echo ""

POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -hex 32)
PGADMIN_PASSWORD=$(openssl rand -base64 32)

echo "PostgreSQL Password: $POSTGRES_PASSWORD"
echo "Redis Password:      $REDIS_PASSWORD"
echo "Secret Key:          $SECRET_KEY"
echo "PgAdmin Password:    $PGADMIN_PASSWORD"
echo ""
echo "──────────────────────────────────────────────────────────────"
echo ""

echo "📝 Step 5: Updating .env file on VPS..."

ssh ${VPS_USER}@${VPS_HOST} << EOF
cd ${VPS_DIR}

# Update .env file with generated passwords
sed -i "s/POSTGRES_PASSWORD=CHANGE_THIS_TO_STRONG_PASSWORD/POSTGRES_PASSWORD=${POSTGRES_PASSWORD}/g" .env
sed -i "s/:CHANGE_THIS_TO_STRONG_PASSWORD@mahasewa-postgres/:${POSTGRES_PASSWORD}@mahasewa-postgres/g" .env
sed -i "s/REDIS_PASSWORD=CHANGE_THIS_TO_STRONG_REDIS_PASSWORD/REDIS_PASSWORD=${REDIS_PASSWORD}/g" .env
sed -i "s/:CHANGE_THIS_TO_STRONG_REDIS_PASSWORD@mahasewa-redis/:${REDIS_PASSWORD}@mahasewa-redis/g" .env
sed -i "s/SECRET_KEY=GENERATE_WITH_openssl_rand_hex_32/SECRET_KEY=${SECRET_KEY}/g" .env
sed -i "s/PGADMIN_PASSWORD=CHANGE_THIS_TO_STRONG_PASSWORD/PGADMIN_PASSWORD=${PGADMIN_PASSWORD}/g" .env

echo "✅ Environment file updated"
EOF

echo ""

START_SERVICES="y"

if [[ $START_SERVICES =~ ^[Yy]$ ]]; then
    echo ""
    echo "🚀 Step 6: Starting Docker services..."
    
    ssh ${VPS_USER}@${VPS_HOST} << EOF
cd ${VPS_DIR}
docker compose -f docker-compose.yml up -d
echo ""
echo "📊 Services Status:"
docker compose -f docker-compose.yml ps
EOF
    
    echo ""
    echo "✅ Services started successfully!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎉 Deployment Complete!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📍 Services Running:"
    echo "   PostgreSQL: ${VPS_HOST}:5433"
    echo "   Redis:      ${VPS_HOST}:6380"
    echo "   PgAdmin:    http://${VPS_HOST}:5051"
    echo ""
    echo "🔗 Connection Strings:"
    echo ""
    echo "   External (from local):"
    echo "   DATABASE_URL=postgresql://mahasewa_user:${POSTGRES_PASSWORD}@${VPS_HOST}:5433/mahasewa_db"
    echo ""
    echo "   Internal (on VPS):"
    echo "   DATABASE_URL=postgresql://mahasewa_user:${POSTGRES_PASSWORD}@mahasewa-postgres:5432/mahasewa_db"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "⏭️  Next: Run database migrations"
    echo "   cd /Users/sandesh/Projects/MahaSeWA/backend"
    echo "   export DATABASE_URL=\"postgresql://mahasewa_user:${POSTGRES_PASSWORD}@${VPS_HOST}:5433/mahasewa_db\""
    echo "   source venv/bin/activate"
    echo "   alembic upgrade head"
    echo ""
else
    echo ""
    echo "✅ Files deployed successfully!"
    echo ""
    echo "To start services later, SSH into VPS and run:"
    echo "   cd ${VPS_DIR}"
    echo "   docker-compose up -d"
    echo ""
fi

echo "✨ Done!"

