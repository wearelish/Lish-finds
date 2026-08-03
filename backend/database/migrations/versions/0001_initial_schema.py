"""Initial schema with users, businesses, reviews and analytics

Revision ID: 0001
Revises: 
Create Date: 2024-08-01 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create PostGIS extension
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('role', sa.Enum('USER', 'BUSINESS', 'ADMIN', name='userrole'), nullable=False, default='USER'),
        sa.Column('verification_token', sa.String(length=255), nullable=True),
        sa.Column('reset_password_token', sa.String(length=255), nullable=True),
        sa.Column('preferences', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Create businesses table
    op.create_table('businesses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('subcategory', sa.String(length=100), nullable=True),
        sa.Column('location', geoalchemy2.Geography(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('latitude', sa.DECIMAL(precision=10, scale=8), nullable=True),
        sa.Column('longitude', sa.DECIMAL(precision=11, scale=8), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=False, default='India'),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('instagram', sa.String(length=255), nullable=True),
        sa.Column('facebook', sa.String(length=255), nullable=True),
        sa.Column('whatsapp', sa.String(length=20), nullable=True),
        sa.Column('opening_hours', sa.JSON(), nullable=True),
        sa.Column('services', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('amenities', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('price_range', sa.String(length=20), nullable=True),
        sa.Column('photos', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='pending'),
        sa.Column('verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('claimed', sa.Boolean(), nullable=False, default=False),
        sa.Column('rating', sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column('review_count', sa.Integer(), nullable=False, default=0),
        sa.Column('popularity_score', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('slug', sa.String(length=255), nullable=True),
        sa.Column('keywords', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_businesses_name'), 'businesses', ['name'])
    op.create_index(op.f('ix_businesses_category'), 'businesses', ['category'])
    op.create_index(op.f('ix_businesses_city'), 'businesses', ['city'])
    op.create_index(op.f('ix_businesses_status'), 'businesses', ['status'])
    op.create_index(op.f('ix_businesses_verified'), 'businesses', ['verified'])
    op.create_index(op.f('ix_businesses_owner_id'), 'businesses', ['owner_id'])
    op.create_index(op.f('ix_businesses_slug'), 'businesses', ['slug'], unique=True)
    op.create_index('ix_businesses_location', 'businesses', ['location'])
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_businesses_owner_id', 'businesses', 'users',
        ['owner_id'], ['id']
    )
    
    # Create reviews table
    op.create_table('reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False, default='lishfind'),
        sa.Column('verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('helpful_count', sa.Integer(), nullable=False, default=0),
        sa.Column('sentiment', sa.String(length=20), nullable=True),
        sa.Column('sentiment_score', sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column('keywords', sa.JSON(), nullable=True),
        sa.Column('topics', sa.JSON(), nullable=True),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('external_url', sa.String(length=500), nullable=True),
        sa.Column('author_name', sa.String(length=255), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('business_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_reviews_source'), 'reviews', ['source'])
    op.create_index(op.f('ix_reviews_sentiment'), 'reviews', ['sentiment'])
    op.create_index(op.f('ix_reviews_user_id'), 'reviews', ['user_id'])
    op.create_index(op.f('ix_reviews_business_id'), 'reviews', ['business_id'])
    
    # Create foreign key constraints for reviews
    op.create_foreign_key(
        'fk_reviews_user_id', 'reviews', 'users',
        ['user_id'], ['id']
    )
    op.create_foreign_key(
        'fk_reviews_business_id', 'reviews', 'businesses',
        ['business_id'], ['id']
    )
    
    # Create saved_businesses table
    op.create_table('saved_businesses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('business_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_saved_businesses_user_id'), 'saved_businesses', ['user_id'])
    op.create_index(op.f('ix_saved_businesses_business_id'), 'saved_businesses', ['business_id'])
    
    # Create foreign key constraints for saved_businesses
    op.create_foreign_key(
        'fk_saved_businesses_user_id', 'saved_businesses', 'users',
        ['user_id'], ['id']
    )
    op.create_foreign_key(
        'fk_saved_businesses_business_id', 'saved_businesses', 'businesses',
        ['business_id'], ['id']
    )
    
    # Create search_history table
    op.create_table('search_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('intent_data', sa.JSON(), nullable=True),
        sa.Column('results_count', sa.Integer(), nullable=False, default=0),
        sa.Column('search_location', sa.String(length=255), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_search_history_user_id'), 'search_history', ['user_id'])
    op.create_index(op.f('ix_search_history_session_id'), 'search_history', ['session_id'])
    
    # Create foreign key constraint for search_history
    op.create_foreign_key(
        'fk_search_history_user_id', 'search_history', 'users',
        ['user_id'], ['id']
    )
    
    # Create business_analytics table
    op.create_table('business_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('profile_views', sa.Integer(), nullable=False, default=0),
        sa.Column('search_appearances', sa.Integer(), nullable=False, default=0),
        sa.Column('photo_views', sa.Integer(), nullable=False, default=0),
        sa.Column('phone_clicks', sa.Integer(), nullable=False, default=0),
        sa.Column('direction_requests', sa.Integer(), nullable=False, default=0),
        sa.Column('website_clicks', sa.Integer(), nullable=False, default=0),
        sa.Column('saves', sa.Integer(), nullable=False, default=0),
        sa.Column('reviews_count', sa.Integer(), nullable=False, default=0),
        sa.Column('average_rating', sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column('search_rank_avg', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('search_keywords', sa.JSON(), nullable=True),
        sa.Column('business_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_business_analytics_date'), 'business_analytics', ['date'])
    op.create_index(op.f('ix_business_analytics_business_id'), 'business_analytics', ['business_id'])
    
    # Create foreign key constraint for business_analytics
    op.create_foreign_key(
        'fk_business_analytics_business_id', 'business_analytics', 'businesses',
        ['business_id'], ['id']
    )
    
    # Create search_analytics table
    op.create_table('search_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('query_text', sa.String(length=500), nullable=False),
        sa.Column('query_category', sa.String(length=100), nullable=True),
        sa.Column('query_intent', sa.JSON(), nullable=True),
        sa.Column('results_count', sa.Integer(), nullable=False, default=0),
        sa.Column('avg_response_time_ms', sa.Integer(), nullable=True),
        sa.Column('clicks_count', sa.Integer(), nullable=False, default=0),
        sa.Column('click_through_rate', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('search_location', sa.String(length=255), nullable=True),
        sa.Column('search_source', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_search_analytics_date'), 'search_analytics', ['date'])
    op.create_index(op.f('ix_search_analytics_query_category'), 'search_analytics', ['query_category'])
    
    # Create user_engagement table
    op.create_table('user_engagement',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_data', sa.JSON(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('business_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('referrer', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_user_engagement_event_type'), 'user_engagement', ['event_type'])
    op.create_index(op.f('ix_user_engagement_user_id'), 'user_engagement', ['user_id'])
    op.create_index(op.f('ix_user_engagement_session_id'), 'user_engagement', ['session_id'])
    op.create_index(op.f('ix_user_engagement_business_id'), 'user_engagement', ['business_id'])
    
    # Create foreign key constraints for user_engagement
    op.create_foreign_key(
        'fk_user_engagement_user_id', 'user_engagement', 'users',
        ['user_id'], ['id']
    )
    op.create_foreign_key(
        'fk_user_engagement_business_id', 'user_engagement', 'businesses',
        ['business_id'], ['id']
    )


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('user_engagement')
    op.drop_table('search_analytics')
    op.drop_table('business_analytics')
    op.drop_table('search_history')
    op.drop_table('saved_businesses')
    op.drop_table('reviews')
    op.drop_table('businesses')
    op.drop_table('users')
    
    # Drop PostGIS extension (be careful in production)
    op.execute('DROP EXTENSION IF EXISTS postgis CASCADE')