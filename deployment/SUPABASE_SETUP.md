# Supabase Database Setup for LishFind

## Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Click "Start your project"
3. Sign up/login with GitHub
4. Create new project:
   - **Name**: `lishfind-database`
   - **Database Password**: Generate strong password (save it!)
   - **Region**: Choose closest to you
   - **Pricing Plan**: Free tier

## Step 2: Enable PostGIS Extension

1. In your Supabase dashboard, go to **Database > Extensions**
2. Search for "postgis"
3. Enable the PostGIS extension
4. Wait for it to be installed

## Step 3: Run Initial Database Schema

1. Go to **SQL Editor** in your Supabase dashboard
2. Create a new query and run this SQL:

```sql
-- Enable PostGIS extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create businesses table
CREATE TABLE IF NOT EXISTS businesses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    phone VARCHAR(20),
    email VARCHAR(100),
    website VARCHAR(255),
    description TEXT,
    rating DECIMAL(3,2),
    price_range VARCHAR(10),
    location GEOMETRY(POINT, 4326),
    opening_hours JSONB,
    amenities TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create spatial index for location queries
CREATE INDEX IF NOT EXISTS idx_businesses_location ON businesses USING GIST (location);

-- Create regular indexes
CREATE INDEX IF NOT EXISTS idx_businesses_category ON businesses (category);
CREATE INDEX IF NOT EXISTS idx_businesses_city ON businesses (city);
CREATE INDEX IF NOT EXISTS idx_businesses_rating ON businesses (rating);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(128) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create user searches table for analytics
CREATE TABLE IF NOT EXISTS user_searches (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    location GEOMETRY(POINT, 4326),
    results_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create spatial index for user searches
CREATE INDEX IF NOT EXISTS idx_user_searches_location ON user_searches USING GIST (location);

-- Insert sample data
INSERT INTO businesses (name, category, address, city, state, zip_code, phone, email, website, description, rating, price_range, location, opening_hours, amenities)
VALUES 
('Coffee Central', 'Coffee Shop', '123 Main St', 'Portland', 'OR', '97201', '(503) 555-0100', 'info@coffeecentral.com', 'https://coffeecentral.com', 'Artisan coffee shop with locally roasted beans', 4.5, '$$', ST_GeomFromText('POINT(-122.6784 45.5152)', 4326), 
 '{"monday": "6:00-20:00", "tuesday": "6:00-20:00", "wednesday": "6:00-20:00", "thursday": "6:00-20:00", "friday": "6:00-21:00", "saturday": "7:00-21:00", "sunday": "7:00-19:00"}',
 ARRAY['wifi', 'outdoor_seating', 'wheelchair_accessible']),

('Green Leaf Restaurant', 'Restaurant', '456 Oak Ave', 'Portland', 'OR', '97202', '(503) 555-0200', 'contact@greenleaf.com', 'https://greenleaf.com', 'Farm-to-table restaurant with organic ingredients', 4.2, '$$$', ST_GeomFromText('POINT(-122.6587 45.5051)', 4326),
 '{"tuesday": "17:00-22:00", "wednesday": "17:00-22:00", "thursday": "17:00-22:00", "friday": "17:00-23:00", "saturday": "17:00-23:00", "sunday": "17:00-21:00"}',
 ARRAY['vegetarian_options', 'outdoor_seating', 'reservations']),

('TechHub Coworking', 'Coworking Space', '789 Pine St', 'Portland', 'OR', '97205', '(503) 555-0300', 'hello@techhub.com', 'https://techhub.com', 'Modern coworking space for tech professionals', 4.7, '$$', ST_GeomFromText('POINT(-122.6851 45.5272)', 4326),
 '{"monday": "8:00-18:00", "tuesday": "8:00-18:00", "wednesday": "8:00-18:00", "thursday": "8:00-18:00", "friday": "8:00-17:00"}',
 ARRAY['wifi', 'meeting_rooms', 'parking', 'wheelchair_accessible']);
```

## Step 4: Get Database Connection Details

1. Go to **Settings > Database** in your Supabase dashboard
2. Copy the connection string (it looks like):
   ```
   postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
   ```
3. Save this for your environment variables

## Step 5: Test Connection

You can test the connection using the SQL Editor or by running:

```sql
-- Test PostGIS is working
SELECT PostGIS_Version();

-- Test sample query
SELECT name, category, ST_AsText(location) as location_text 
FROM businesses 
LIMIT 5;
```

## Environment Variables for Backend

Add these to your deployment:

```
DATABASE_URL=postgresql://postgres:[your-password]@db.[your-project-ref].supabase.co:5432/postgres
```

## Notes

- Supabase free tier includes:
  - Up to 500MB database storage
  - Up to 2GB bandwidth per month
  - PostGIS extension included
  - Automatic backups
- The database URL includes SSL by default (secure)
- Row Level Security (RLS) is available but not required for this setup