-- Create production-ready indexes for optimal performance
-- This script creates indexes that complement the Alembic migrations

-- Performance indexes for business searches
-- Note: These may be redundant with Alembic migrations, but serve as backup

-- Business table indexes (if not created by Alembic)
-- CREATE INDEX IF NOT EXISTS idx_business_name_trgm ON businesses USING gin(name gin_trgm_ops);
-- CREATE INDEX IF NOT EXISTS idx_business_category ON businesses(category);
-- CREATE INDEX IF NOT EXISTS idx_business_location ON businesses(latitude, longitude);
-- CREATE INDEX IF NOT EXISTS idx_business_status ON businesses(status) WHERE status = 'active';

-- User table indexes (if not created by Alembic)  
-- CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);
-- CREATE INDEX IF NOT EXISTS idx_user_created_at ON users(created_at);

-- Reviews table indexes (if not created by Alembic)
-- CREATE INDEX IF NOT EXISTS idx_reviews_business_id ON reviews(business_id);
-- CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON reviews(user_id);
-- CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating);
-- CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews(created_at);

-- Analytics table indexes (if not created by Alembic)
-- CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON search_analytics(event_type);
-- CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON search_analytics(timestamp);
-- CREATE INDEX IF NOT EXISTS idx_analytics_session_id ON search_analytics(session_id);

-- Composite indexes for common query patterns
-- CREATE INDEX IF NOT EXISTS idx_business_category_status ON businesses(category, status) WHERE status = 'active';
-- CREATE INDEX IF NOT EXISTS idx_reviews_business_rating ON reviews(business_id, rating);

-- Partial indexes for better performance on filtered queries
-- CREATE INDEX IF NOT EXISTS idx_active_businesses ON businesses(id) WHERE status = 'active';
-- CREATE INDEX IF NOT EXISTS idx_recent_reviews ON reviews(id) WHERE created_at > CURRENT_DATE - INTERVAL '30 days';

-- Full-text search indexes
-- CREATE INDEX IF NOT EXISTS idx_business_search ON businesses USING gin(to_tsvector('english', name || ' ' || coalesce(description, '')));

-- Geographic indexes (if using PostGIS)
-- CREATE INDEX IF NOT EXISTS idx_business_geolocation ON businesses USING gist(ST_Point(longitude, latitude));

-- Show index usage statistics
CREATE OR REPLACE VIEW index_usage_stats AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Show table sizes
CREATE OR REPLACE VIEW table_sizes AS
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Query to identify missing indexes (run periodically)
CREATE OR REPLACE VIEW potential_missing_indexes AS
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    seq_tup_read / NULLIF(seq_scan, 0) as avg_seq_tup_read,
    'Consider adding index' as recommendation
FROM pg_stat_user_tables
WHERE seq_scan > 0
  AND seq_tup_read / NULLIF(seq_scan, 0) > 1000  -- Tables with large sequential scans
  AND idx_scan < seq_scan  -- More sequential scans than index scans
ORDER BY seq_tup_read DESC;

-- Create function to analyze query performance
CREATE OR REPLACE FUNCTION analyze_query_performance()
RETURNS TABLE(
    query_text text,
    total_calls bigint,
    total_time_ms numeric,
    avg_time_ms numeric,
    hit_rate_percent numeric
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        LEFT(pss.query, 100) as query_text,
        pss.calls as total_calls,
        ROUND(pss.total_time::numeric, 2) as total_time_ms,
        ROUND(pss.mean_time::numeric, 2) as avg_time_ms,
        ROUND(
            100.0 * pss.shared_blks_hit / 
            NULLIF(pss.shared_blks_hit + pss.shared_blks_read, 0), 2
        ) as hit_rate_percent
    FROM pg_stat_statements pss
    WHERE pss.calls > 10  -- Only queries called more than 10 times
    ORDER BY pss.total_time DESC
    LIMIT 20;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions for monitoring views
GRANT SELECT ON index_usage_stats TO PUBLIC;
GRANT SELECT ON table_sizes TO PUBLIC;
GRANT SELECT ON potential_missing_indexes TO PUBLIC;
GRANT EXECUTE ON FUNCTION analyze_query_performance() TO PUBLIC;