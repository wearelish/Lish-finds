-- Enable required PostgreSQL extensions for LishFind
-- Production-ready configuration with performance optimizations

-- UUID generation (for primary keys)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Full-text search enhancements
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- Trigram matching for fuzzy search
CREATE EXTENSION IF NOT EXISTS btree_gin;    -- GIN indexes for better performance
CREATE EXTENSION IF NOT EXISTS unaccent;     -- Remove accents for better search

-- Performance monitoring and analytics
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- PostGIS for geographic data (optional, uncomment if needed for advanced mapping)
-- CREATE EXTENSION IF NOT EXISTS postgis;
-- CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Production database configuration
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';

-- Performance tuning
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_cache_size = '512MB';
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';

-- Connection and timeout settings
ALTER SYSTEM SET statement_timeout = '30s';
ALTER SYSTEM SET lock_timeout = '10s';
ALTER SYSTEM SET idle_in_transaction_session_timeout = '10min';

-- Logging configuration for production monitoring
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log slow queries (>1s)
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
ALTER SYSTEM SET log_lock_waits = on;
ALTER SYSTEM SET log_checkpoints = on;

-- WAL configuration for better performance
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;

-- Reload configuration
SELECT pg_reload_conf();

-- Create performance monitoring view
CREATE OR REPLACE VIEW db_performance_stats AS
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    min_time,
    max_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 20;

-- Verify extensions and show configuration
SELECT 
    extname as extension_name,
    extversion as version,
    'Enabled' as status
FROM pg_extension
WHERE extname IN (
    'uuid-ossp', 
    'pg_trgm', 
    'btree_gin', 
    'unaccent',
    'pg_stat_statements'
)
ORDER BY extname;

-- Show current configuration
SHOW shared_preload_libraries;
SHOW log_min_duration_statement;
SHOW statement_timeout;