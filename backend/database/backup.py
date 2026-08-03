"""
Database backup and restoration utilities for production.

Supports PostgreSQL and SQLite with compression and encryption options.
"""

import os
import gzip
import shutil
import subprocess
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

import structlog
from sqlalchemy import text

from database.connection import get_db_session
from core.config import settings

logger = structlog.get_logger(__name__)

BACKUP_DIR = Path("backups")
BACKUP_DIR.mkdir(exist_ok=True)


class DatabaseBackup:
    """Database backup manager with support for multiple database types."""
    
    def __init__(self):
        self.backup_dir = BACKUP_DIR
        self.retention_days = getattr(settings, 'BACKUP_RETENTION_DAYS', 30)
        
    async def create_backup(self, 
                          backup_name: Optional[str] = None,
                          compress: bool = True,
                          include_schema: bool = True) -> Dict[str, Any]:
        """Create a database backup."""
        
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"lishfind_backup_{timestamp}"
        
        backup_path = self.backup_dir / f"{backup_name}.sql"
        
        try:
            if "postgresql" in settings.DATABASE_URL:
                result = await self._backup_postgresql(backup_path, include_schema)
            else:
                result = await self._backup_sqlite(backup_path, include_schema)
            
            # Compress if requested
            if compress and result["status"] == "success":
                compressed_path = await self._compress_backup(backup_path)
                result["backup_path"] = str(compressed_path)
                result["compressed"] = True
            else:
                result["backup_path"] = str(backup_path)
                result["compressed"] = False
            
            # Add metadata
            result.update({
                "backup_name": backup_name,
                "created_at": datetime.now().isoformat(),
                "database_type": "PostgreSQL" if "postgresql" in settings.DATABASE_URL else "SQLite",
                "include_schema": include_schema
            })
            
            logger.info(
                "Database backup created",
                backup_name=backup_name,
                backup_path=result["backup_path"],
                compressed=result["compressed"],
                size_mb=result.get("size_mb", 0)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Database backup failed",
                backup_name=backup_name,
                error=str(e),
                exc_info=True
            )
            return {
                "status": "failed",
                "error": str(e),
                "backup_name": backup_name
            }
    
    async def _backup_postgresql(self, backup_path: Path, include_schema: bool) -> Dict[str, Any]:
        """Create PostgreSQL backup using pg_dump."""
        
        # Parse database URL for pg_dump
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        
        # Build pg_dump command
        cmd = [
            "pg_dump",
            "--no-password",
            "--verbose",
            "--format=plain",
            "--encoding=UTF8",
        ]
        
        if include_schema:
            cmd.extend(["--create", "--clean"])
        else:
            cmd.append("--data-only")
        
        cmd.extend(["--file", str(backup_path), db_url])
        
        # Set environment variables for authentication
        env = os.environ.copy()
        if "PGPASSWORD" not in env and ":" in db_url:
            # Extract password from URL
            try:
                import urllib.parse
                parsed = urllib.parse.urlparse(db_url)
                if parsed.password:
                    env["PGPASSWORD"] = parsed.password
            except Exception:
                pass
        
        # Execute pg_dump
        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            return {
                "status": "success",
                "size_mb": round(size_mb, 2),
                "output": stdout.decode() if stdout else "",
            }
        else:
            error_msg = stderr.decode() if stderr else "Unknown pg_dump error"
            return {
                "status": "failed",
                "error": error_msg
            }
    
    async def _backup_sqlite(self, backup_path: Path, include_schema: bool) -> Dict[str, Any]:
        """Create SQLite backup using .dump command."""
        
        # Get database path from URL
        db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
        if db_path.startswith("./"):
            db_path = Path(db_path)
        else:
            db_path = Path(db_path)
        
        if not db_path.exists():
            return {
                "status": "failed",
                "error": f"Database file not found: {db_path}"
            }
        
        try:
            # Use sqlite3 command to create dump
            cmd = ["sqlite3", str(db_path), ".dump"]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Write dump to file
                with open(backup_path, 'w') as f:
                    f.write(stdout.decode())
                
                size_mb = backup_path.stat().st_size / (1024 * 1024)
                return {
                    "status": "success",
                    "size_mb": round(size_mb, 2),
                }
            else:
                error_msg = stderr.decode() if stderr else "Unknown sqlite3 error"
                return {
                    "status": "failed",
                    "error": error_msg
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _compress_backup(self, backup_path: Path) -> Path:
        """Compress backup file using gzip."""
        compressed_path = backup_path.with_suffix(backup_path.suffix + ".gz")
        
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove uncompressed file
        backup_path.unlink()
        
        return compressed_path
    
    async def restore_backup(self, backup_path: str, 
                           drop_existing: bool = False) -> Dict[str, Any]:
        """Restore database from backup."""
        
        backup_file = Path(backup_path)
        if not backup_file.exists():
            return {
                "status": "failed",
                "error": f"Backup file not found: {backup_path}"
            }
        
        try:
            # Decompress if needed
            if backup_file.suffix == ".gz":
                decompressed_path = backup_file.with_suffix("")
                with gzip.open(backup_file, 'rb') as f_in:
                    with open(decompressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_file = decompressed_path
            
            if "postgresql" in settings.DATABASE_URL:
                result = await self._restore_postgresql(backup_file, drop_existing)
            else:
                result = await self._restore_sqlite(backup_file, drop_existing)
            
            logger.info(
                "Database restore completed",
                backup_path=backup_path,
                status=result["status"]
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Database restore failed",
                backup_path=backup_path,
                error=str(e),
                exc_info=True
            )
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _restore_postgresql(self, backup_file: Path, 
                                drop_existing: bool) -> Dict[str, Any]:
        """Restore PostgreSQL database from backup."""
        
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        
        # Build psql command
        cmd = ["psql", "--no-password", "--file", str(backup_file)]
        
        if drop_existing:
            cmd.append("--single-transaction")
        
        cmd.append(db_url)
        
        # Set environment for authentication
        env = os.environ.copy()
        if "PGPASSWORD" not in env:
            try:
                import urllib.parse
                parsed = urllib.parse.urlparse(db_url)
                if parsed.password:
                    env["PGPASSWORD"] = parsed.password
            except Exception:
                pass
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            return {
                "status": "success",
                "output": stdout.decode() if stdout else ""
            }
        else:
            return {
                "status": "failed",
                "error": stderr.decode() if stderr else "Unknown psql error"
            }
    
    async def _restore_sqlite(self, backup_file: Path, 
                            drop_existing: bool) -> Dict[str, Any]:
        """Restore SQLite database from backup."""
        
        db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
        db_file = Path(db_path)
        
        if drop_existing and db_file.exists():
            # Backup existing database
            backup_existing = db_file.with_suffix(f".backup_{int(datetime.now().timestamp())}.db")
            shutil.copy2(db_file, backup_existing)
            db_file.unlink()
        
        # Restore from SQL dump
        cmd = ["sqlite3", str(db_file)]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        with open(backup_file, 'r') as f:
            sql_content = f.read()
        
        stdout, stderr = await process.communicate(input=sql_content.encode())
        
        if process.returncode == 0:
            return {
                "status": "success",
                "output": "SQLite database restored successfully"
            }
        else:
            return {
                "status": "failed",
                "error": stderr.decode() if stderr else "Unknown sqlite3 error"
            }
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups."""
        backups = []
        
        for backup_file in self.backup_dir.glob("*.sql*"):
            stat = backup_file.stat()
            backups.append({
                "name": backup_file.name,
                "path": str(backup_file),
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "compressed": backup_file.suffix == ".gz"
            })
        
        # Sort by creation time, newest first
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups
    
    async def cleanup_old_backups(self) -> Dict[str, Any]:
        """Remove backups older than retention period."""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        removed_backups = []
        total_size_freed = 0
        
        for backup_file in self.backup_dir.glob("*.sql*"):
            file_date = datetime.fromtimestamp(backup_file.stat().st_ctime)
            
            if file_date < cutoff_date:
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                removed_backups.append({
                    "name": backup_file.name,
                    "size_mb": round(size_mb, 2),
                    "created_at": file_date.isoformat()
                })
                total_size_freed += size_mb
                backup_file.unlink()
        
        logger.info(
            "Backup cleanup completed",
            removed_count=len(removed_backups),
            size_freed_mb=round(total_size_freed, 2),
            retention_days=self.retention_days
        )
        
        return {
            "status": "success",
            "removed_backups": removed_backups,
            "total_size_freed_mb": round(total_size_freed, 2),
            "retention_days": self.retention_days
        }
    
    async def verify_backup(self, backup_path: str) -> Dict[str, Any]:
        """Verify backup integrity."""
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            return {
                "status": "failed",
                "error": f"Backup file not found: {backup_path}"
            }
        
        try:
            # Check if file is compressed
            if backup_file.suffix == ".gz":
                # Test gzip integrity
                with gzip.open(backup_file, 'rt') as f:
                    # Read first few lines to verify
                    for _ in range(10):
                        line = f.readline()
                        if not line:
                            break
            else:
                # Test SQL file integrity
                with open(backup_file, 'r') as f:
                    # Check if it looks like SQL
                    content = f.read(1000)
                    if not any(keyword in content.upper() for keyword in 
                              ["CREATE", "INSERT", "DROP", "ALTER", "SELECT"]):
                        return {
                            "status": "failed",
                            "error": "File does not appear to contain SQL"
                        }
            
            return {
                "status": "success",
                "message": "Backup file is valid",
                "size_mb": round(backup_file.stat().st_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": f"Backup verification failed: {str(e)}"
            }


# Convenience functions
backup_manager = DatabaseBackup()

async def create_backup(**kwargs) -> Dict[str, Any]:
    """Create a database backup."""
    return await backup_manager.create_backup(**kwargs)

async def restore_backup(backup_path: str, **kwargs) -> Dict[str, Any]:
    """Restore database from backup."""
    return await backup_manager.restore_backup(backup_path, **kwargs)

def list_backups() -> List[Dict[str, Any]]:
    """List available backups."""
    return backup_manager.list_backups()

async def cleanup_old_backups() -> Dict[str, Any]:
    """Clean up old backups."""
    return await backup_manager.cleanup_old_backups()