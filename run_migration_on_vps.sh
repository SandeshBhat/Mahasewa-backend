#!/bin/bash

# =====================================================
# Run Database Migration on VPS
# =====================================================
# This script runs the content management migration on the VPS
# =====================================================

set -e  # Exit on error

VPS_HOST="srv1110921.hstgr.cloud"
VPS_USER="sandesh"
VPS_DIR="~/mahasewa-backend"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   MahaSeWA Database Migration - Content Management System     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Copy migration files to VPS
echo "📤 Step 1: Copying migration files to VPS..."
scp migrations/content_management.sql ${VPS_USER}@${VPS_HOST}:${VPS_DIR}/migration.sql 2>/dev/null || {
    echo "⚠️  Could not copy via SCP. Please copy manually:"
    echo "   scp backend/migrations/content_management.sql ${VPS_USER}@${VPS_HOST}:${VPS_DIR}/migration.sql"
    echo ""
}

# Step 2: Run migration on VPS
echo "🚀 Step 2: Running migration on VPS..."
echo ""

ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd ~/mahasewa-backend

echo "📋 Checking Docker services..."
if ! docker ps | grep -q mahasewa-postgres; then
    echo "❌ PostgreSQL container is not running!"
    echo "   Please start it with: docker-compose up -d"
    exit 1
fi

echo "✅ PostgreSQL container is running"
echo ""

echo "📊 Current database tables:"
docker exec mahasewa-postgres psql -U mahasewa_user -d mahasewa_db -c "\dt" 2>/dev/null | head -20 || echo "Could not list tables"
echo ""

echo "🔄 Running migration..."
if [ -f migration.sql ]; then
    docker exec -i mahasewa-postgres psql -U mahasewa_user -d mahasewa_db < migration.sql
    echo "✅ Migration completed!"
else
    echo "❌ migration.sql not found!"
    echo "   Please copy the file first:"
    echo "   scp backend/migrations/content_management.sql ${VPS_USER}@${VPS_HOST}:${VPS_DIR}/migration.sql"
    exit 1
fi

echo ""
echo "📊 Verifying migration..."
echo ""

echo "Checking downloads table columns:"
docker exec mahasewa-postgres psql -U mahasewa_user -d mahasewa_db -c "
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'downloads' 
AND column_name IN ('subcategory', 'cover_image_url', 'member_discount_percent', 'access_level', 'tags')
ORDER BY column_name;
" 2>/dev/null || echo "Could not verify downloads columns"

echo ""
echo "Checking purchase_history table:"
docker exec mahasewa-postgres psql -U mahasewa_user -d mahasewa_db -c "
SELECT COUNT(*) as table_exists 
FROM information_schema.tables 
WHERE table_name = 'purchase_history';
" 2>/dev/null || echo "Could not verify purchase_history"

echo ""
echo "Checking gallery table:"
docker exec mahasewa-postgres psql -U mahasewa_user -d mahasewa_db -c "
SELECT COUNT(*) as table_exists 
FROM information_schema.tables 
WHERE table_name = 'gallery';
" 2>/dev/null || echo "Could not verify gallery"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Migration Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ENDSSH

echo ""
echo "✅ Migration script completed!"
echo ""
echo "📝 Next Steps:"
echo "   1. Test API endpoints"
echo "   2. Verify data in database"
echo "   3. Start using new features!"
echo ""
