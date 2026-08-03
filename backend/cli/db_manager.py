#!/usr/bin/env python3
"""
Database Management CLI for LishFind Production

Provides commands for database administration, monitoring, and maintenance.
"""

import asyncio
import click
import sys
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import init_db, close_db, health_check, execute_query
from database.backup import create_backup, restore_backup, list_backups, cleanup_old_backups
from database.performance import (
    analyze_table_performance, 
    get_slow_queries, 
    suggest_indexes,
    optimize_database,
    get_database_health
)
from core.config import settings


@click.group()
def cli():
    """LishFind Database Management CLI"""
    pass


@cli.command()
def health():
    """Check database health and connection."""
    async def _health():
        try:
            await init_db()
            health_status = await health_check()
            
            click.echo(f"Database Status: {health_status['status']}")
            
            if health_status['status'] == 'healthy':
                click.echo(f"✅ Response time: {health_status['response_time_ms']}ms")
                
                if 'database_info' in health_status:
                    info = health_status['database_info']
                    if info:
                        click.echo(f"📊 Database: {info.get('database_name', 'N/A')}")
                        if 'database_size' in info:
                            click.echo(f"💾 Size: {info['database_size']}")
                
                if 'pool_info' in health_status:
                    pool = health_status['pool_info']
                    if pool:
                        click.echo(f"🏊 Pool - Size: {pool.get('pool_size', 0)}, "
                                 f"Active: {pool.get('checked_out', 0)}")
            else:
                click.echo(f"❌ Error: {health_status.get('error', 'Unknown error')}")
                
        except Exception as e:
            click.echo(f"❌ Failed to check health: {e}")
        finally:
            await close_db()
    
    asyncio.run(_health())


@cli.command()
@click.option('--table', help='Analyze specific table')
def analyze(table):
    """Analyze database performance."""
    async def _analyze():
        try:
            await init_db()
            
            if table:
                # Analyze specific table
                result = await analyze_table_performance(table)
                
                click.echo(f"\n📊 Analysis for table: {table}")
                click.echo("=" * 50)
                
                if 'error' in result:
                    click.echo(f"❌ Error: {result['error']}")
                    return
                
                # Display results based on database type
                if 'column_stats' in result:
                    click.echo("\n📈 Column Statistics:")
                    for stat in result['column_stats'][:5]:  # Show first 5
                        click.echo(f"  • {stat.get('attname', 'N/A')}: "
                                 f"distinct={stat.get('n_distinct', 'N/A')}")
                
                if 'size_info' in result and result['size_info']:
                    size_info = result['size_info']
                    click.echo(f"\n💾 Size Information:")
                    click.echo(f"  • Total: {size_info.get('total_size', 'N/A')}")
                    click.echo(f"  • Table: {size_info.get('table_size', 'N/A')}")
                    click.echo(f"  • Indexes: {size_info.get('index_size', 'N/A')}")
                
                if 'index_stats' in result:
                    click.echo(f"\n🔍 Index Statistics:")
                    for idx in result['index_stats']:
                        click.echo(f"  • {idx.get('index_name', 'N/A')}: "
                                 f"scans={idx.get('idx_scan', 0)}")
            
            else:
                # General performance analysis
                click.echo("\n🚀 Database Performance Analysis")
                click.echo("=" * 50)
                
                # Get slow queries
                slow_queries = await get_slow_queries(5)
                if slow_queries:
                    click.echo("\n🐌 Slowest Queries:")
                    for i, query in enumerate(slow_queries, 1):
                        click.echo(f"  {i}. {query['query'][:60]}...")
                        click.echo(f"     Avg: {query['avg_time']:.3f}s, "
                                 f"Max: {query['max_time']:.3f}s, "
                                 f"Calls: {query['count']}")
                
                # Get index suggestions
                suggestions = await suggest_indexes()
                if suggestions:
                    click.echo(f"\n💡 Index Suggestions:")
                    for suggestion in suggestions[:3]:  # Show top 3
                        click.echo(f"  • {suggestion['table']}: {suggestion['reason']}")
                        click.echo(f"    Priority: {suggestion.get('priority', 'medium')}")
                
                # Overall health
                health_data = await get_database_health()
                click.echo(f"\n🏥 Overall Health: {health_data['status']}")
                
                if health_data.get('performance_issues'):
                    click.echo(f"⚠️  Issues:")
                    for issue in health_data['performance_issues']:
                        click.echo(f"  • {issue}")
                
        except Exception as e:
            click.echo(f"❌ Analysis failed: {e}")
        finally:
            await close_db()
    
    asyncio.run(_analyze())


@cli.command()
@click.option('--name', help='Backup name (auto-generated if not provided)')
@click.option('--compress/--no-compress', default=True, help='Compress backup file')
@click.option('--schema/--no-schema', default=True, help='Include schema in backup')
def backup(name, compress, schema):
    """Create database backup."""
    async def _backup():
        try:
            await init_db()
            
            click.echo("🗄️  Creating database backup...")
            
            result = await create_backup(
                backup_name=name,
                compress=compress,
                include_schema=schema
            )
            
            if result['status'] == 'success':
                click.echo(f"✅ Backup created successfully!")
                click.echo(f"📁 File: {result['backup_path']}")
                click.echo(f"💾 Size: {result.get('size_mb', 0):.2f} MB")
                click.echo(f"🗜️  Compressed: {result.get('compressed', False)}")
            else:
                click.echo(f"❌ Backup failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            click.echo(f"❌ Backup failed: {e}")
        finally:
            await close_db()
    
    asyncio.run(_backup())


@cli.command()
@click.argument('backup_path')
@click.option('--drop/--no-drop', default=False, 
              help='Drop existing data before restore')
@click.confirmation_option(prompt='Are you sure you want to restore the database?')
def restore(backup_path, drop):
    """Restore database from backup file."""
    async def _restore():
        try:
            await init_db()
            
            click.echo(f"🔄 Restoring database from {backup_path}...")
            
            result = await restore_backup(backup_path, drop_existing=drop)
            
            if result['status'] == 'success':
                click.echo("✅ Database restored successfully!")
                if 'output' in result and result['output']:
                    click.echo(f"📄 Output: {result['output'][:200]}...")
            else:
                click.echo(f"❌ Restore failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            click.echo(f"❌ Restore failed: {e}")
        finally:
            await close_db()
    
    asyncio.run(_restore())


@cli.command()
def list_backups():
    """List available backup files."""
    try:
        backups = list_backups()
        
        if not backups:
            click.echo("📭 No backups found")
            return
        
        click.echo(f"📁 Available backups ({len(backups)} total):")
        click.echo("=" * 80)
        
        for backup in backups:
            click.echo(f"📄 {backup['name']}")
            click.echo(f"   📅 Created: {backup['created_at']}")
            click.echo(f"   💾 Size: {backup['size_mb']} MB")
            click.echo(f"   🗜️  Compressed: {backup['compressed']}")
            click.echo()
            
    except Exception as e:
        click.echo(f"❌ Failed to list backups: {e}")


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to cleanup old backups?')
def cleanup():
    """Clean up old backup files."""
    async def _cleanup():
        try:
            result = await cleanup_old_backups()
            
            if result['status'] == 'success':
                removed = result['removed_backups']
                click.echo(f"🧹 Cleaned up {len(removed)} old backups")
                click.echo(f"💾 Freed {result['total_size_freed_mb']:.2f} MB")
                click.echo(f"📅 Retention: {result['retention_days']} days")
                
                if removed:
                    click.echo("\n📋 Removed backups:")
                    for backup in removed:
                        click.echo(f"  • {backup['name']} ({backup['size_mb']} MB)")
            else:
                click.echo(f"❌ Cleanup failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            click.echo(f"❌ Cleanup failed: {e}")
    
    asyncio.run(_cleanup())


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to optimize the database?')
def optimize():
    """Run database optimization commands."""
    async def _optimize():
        try:
            await init_db()
            
            click.echo("⚡ Optimizing database...")
            
            result = await optimize_database()
            
            if result['optimizations']:
                click.echo("✅ Optimizations completed:")
                for opt in result['optimizations']:
                    click.echo(f"  • {opt['command']}: {opt['description']}")
            
            if result['errors']:
                click.echo("⚠️  Some optimizations failed:")
                for error in result['errors']:
                    click.echo(f"  • {error}")
            
            if not result['optimizations'] and not result['errors']:
                click.echo("ℹ️  No optimizations were performed")
                
        except Exception as e:
            click.echo(f"❌ Optimization failed: {e}")
        finally:
            await close_db()
    
    asyncio.run(_optimize())


@cli.command()
@click.argument('sql')
def query(sql):
    """Execute raw SQL query (read-only)."""
    async def _query():
        try:
            await init_db()
            
            # Basic safety check for read-only queries
            sql_upper = sql.upper().strip()
            if any(keyword in sql_upper for keyword in 
                   ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE']):
                click.echo("❌ Only read-only queries are allowed")
                return
            
            click.echo(f"🔍 Executing query: {sql}")
            
            result = await execute_query(sql)
            
            if result:
                click.echo(f"📊 Results ({len(result)} rows):")
                for i, row in enumerate(result[:10]):  # Show first 10 rows
                    click.echo(f"  {i+1}: {dict(row)}")
                
                if len(result) > 10:
                    click.echo(f"  ... and {len(result) - 10} more rows")
            else:
                click.echo("📭 No results returned")
                
        except Exception as e:
            click.echo(f"❌ Query failed: {e}")
        finally:
            await close_db()
    
    asyncio.run(_query())


@cli.command()
def info():
    """Show database configuration and environment info."""
    click.echo("ℹ️  Database Configuration")
    click.echo("=" * 40)
    click.echo(f"Environment: {settings.ENVIRONMENT}")
    click.echo(f"Debug Mode: {settings.DEBUG}")
    
    # Sanitize database URL for display
    db_url = settings.DATABASE_URL
    if "@" in db_url:
        db_url = "***:" + db_url.split("@")[-1]
    click.echo(f"Database URL: {db_url}")
    
    click.echo(f"Pool Size: {settings.DATABASE_POOL_SIZE}")
    click.echo(f"Max Overflow: {settings.DATABASE_MAX_OVERFLOW}")
    
    if settings.REDIS_URL:
        redis_url = settings.REDIS_URL
        if "@" in redis_url:
            redis_url = "***:" + redis_url.split("@")[-1]
        click.echo(f"Redis URL: {redis_url}")
    else:
        click.echo("Redis: Disabled")


if __name__ == '__main__':
    cli()