-- =====================================================
-- Content Management System Database Migration
-- =====================================================
-- Date: 2025-12-17
-- Purpose: Add columns to downloads table and create purchase_history and gallery tables
-- =====================================================

-- =====================================================
-- 1. ADD COLUMNS TO DOWNLOADS TABLE
-- =====================================================

-- Add subcategory column
ALTER TABLE downloads 
ADD COLUMN IF NOT EXISTS subcategory VARCHAR(100);

-- Add cover_image_url column
ALTER TABLE downloads 
ADD COLUMN IF NOT EXISTS cover_image_url VARCHAR(500);

-- Add member_discount_percent column
ALTER TABLE downloads 
ADD COLUMN IF NOT EXISTS member_discount_percent INTEGER DEFAULT 0;

-- Add premium_discount_percent column
ALTER TABLE downloads 
ADD COLUMN IF NOT EXISTS premium_discount_percent INTEGER DEFAULT 0;

-- Add access_level column
ALTER TABLE downloads 
ADD COLUMN IF NOT EXISTS access_level VARCHAR(50) DEFAULT 'public';

-- Add purchase_count column
ALTER TABLE downloads 
ADD COLUMN IF NOT EXISTS purchase_count INTEGER DEFAULT 0;

-- Add total_revenue column
ALTER TABLE downloads 
ADD COLUMN IF NOT EXISTS total_revenue NUMERIC(10, 2) DEFAULT 0;

-- Add tags column (JSON)
ALTER TABLE downloads 
ADD COLUMN IF NOT EXISTS tags JSON;

-- Add published_date column
ALTER TABLE downloads 
ADD COLUMN IF NOT EXISTS published_date TIMESTAMP;

-- Add author column
ALTER TABLE downloads 
ADD COLUMN IF NOT EXISTS author VARCHAR(255);

-- Add language column
ALTER TABLE downloads 
ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en';

-- =====================================================
-- 2. CREATE PURCHASE_HISTORY TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS purchase_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    download_id INTEGER NOT NULL REFERENCES downloads(id) ON DELETE CASCADE,
    
    -- Payment details
    amount_paid NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    payment_method VARCHAR(50),
    payment_id VARCHAR(255),
    payment_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    
    -- Receipt
    invoice_number VARCHAR(100),
    receipt_url VARCHAR(500),
    
    -- Access
    access_granted_at TIMESTAMP,
    expires_at TIMESTAMP,
    
    -- Stats
    download_count INTEGER NOT NULL DEFAULT 0,
    last_downloaded_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Unique constraint: one purchase per user per download
    UNIQUE(user_id, download_id)
);

-- Create indexes for purchase_history
CREATE INDEX IF NOT EXISTS idx_purchase_history_user_id ON purchase_history(user_id);
CREATE INDEX IF NOT EXISTS idx_purchase_history_download_id ON purchase_history(download_id);
CREATE INDEX IF NOT EXISTS idx_purchase_history_payment_status ON purchase_history(payment_status);
CREATE INDEX IF NOT EXISTS idx_purchase_history_created_at ON purchase_history(created_at);

-- =====================================================
-- 3. CREATE GALLERY TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS gallery (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    description TEXT,
    image_url VARCHAR(500) NOT NULL,
    thumbnail_url VARCHAR(500),
    
    -- Categorization
    category VARCHAR(100),
    album VARCHAR(100),
    tags JSON,
    
    -- Metadata
    event_date TIMESTAMP,
    location VARCHAR(255),
    photographer VARCHAR(255),
    
    -- Display
    display_order INTEGER NOT NULL DEFAULT 0,
    is_featured BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Stats
    view_count INTEGER NOT NULL DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for gallery
CREATE INDEX IF NOT EXISTS idx_gallery_category ON gallery(category);
CREATE INDEX IF NOT EXISTS idx_gallery_album ON gallery(album);
CREATE INDEX IF NOT EXISTS idx_gallery_featured ON gallery(is_featured);
CREATE INDEX IF NOT EXISTS idx_gallery_active ON gallery(is_active);
CREATE INDEX IF NOT EXISTS idx_gallery_display_order ON gallery(display_order);

-- =====================================================
-- 4. VERIFY MIGRATION
-- =====================================================

-- Check downloads table columns
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'downloads' 
AND column_name IN (
    'subcategory', 'cover_image_url', 'member_discount_percent', 
    'premium_discount_percent', 'access_level', 'purchase_count', 
    'total_revenue', 'tags', 'published_date', 'author', 'language'
)
ORDER BY column_name;

-- Check purchase_history table
SELECT COUNT(*) as purchase_history_exists 
FROM information_schema.tables 
WHERE table_name = 'purchase_history';

-- Check gallery table
SELECT COUNT(*) as gallery_exists 
FROM information_schema.tables 
WHERE table_name = 'gallery';

-- =====================================================
-- MIGRATION COMPLETE
-- =====================================================
