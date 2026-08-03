"""
Secrets Management System

Provides secure handling of secrets including:
- Secret rotation and generation
- Encryption/decryption utilities
- Integration with cloud secret managers
- Local development secret management
"""

import os
import json
import base64
import secrets
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


class SecretsManager:
    """Manages application secrets securely"""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.secrets_dir = Path(f".secrets/{environment}")
        self.secrets_dir.mkdir(parents=True, exist_ok=True)
        self._fernet = None
        
    def _get_encryption_key(self, password: Optional[str] = None) -> bytes:
        """Generate encryption key from password or environment"""
        if password is None:
            password = os.getenv("SECRETS_PASSWORD", "default-dev-password")
        
        password_bytes = password.encode()
        salt = b"lishfind_salt_2024"  # Use a proper random salt in production
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password_bytes))
    
    def _get_cipher(self, password: Optional[str] = None) -> Fernet:
        """Get Fernet cipher instance"""
        if self._fernet is None:
            key = self._get_encryption_key(password)
            self._fernet = Fernet(key)
        return self._fernet
    
    def generate_secret(self, length: int = 32) -> str:
        """Generate a cryptographically secure secret"""
        return secrets.token_urlsafe(length)
    
    def generate_jwt_secret(self) -> str:
        """Generate JWT secret key"""
        return self.generate_secret(64)
    
    def generate_database_password(self) -> str:
        """Generate secure database password"""
        return self.generate_secret(32)
    
    def generate_api_key(self) -> str:
        """Generate API key"""
        return f"lish_{self.generate_secret(40)}"
    
    def encrypt_secret(self, secret: str, password: Optional[str] = None) -> str:
        """Encrypt a secret"""
        cipher = self._get_cipher(password)
        encrypted = cipher.encrypt(secret.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_secret(self, encrypted_secret: str, password: Optional[str] = None) -> str:
        """Decrypt a secret"""
        cipher = self._get_cipher(password)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_secret.encode())
        decrypted = cipher.decrypt(encrypted_bytes)
        return decrypted.decode()
    
    def store_secret(self, key: str, value: str, encrypt: bool = True, 
                    password: Optional[str] = None) -> None:
        """Store a secret securely"""
        secret_file = self.secrets_dir / f"{key}.json"
        
        secret_data = {
            "key": key,
            "created_at": datetime.utcnow().isoformat(),
            "encrypted": encrypt,
            "environment": self.environment
        }
        
        if encrypt:
            secret_data["value"] = self.encrypt_secret(value, password)
        else:
            secret_data["value"] = value
            logger.warning(f"Storing unencrypted secret: {key}")
        
        with open(secret_file, 'w') as f:
            json.dump(secret_data, f, indent=2)
        
        # Set restrictive permissions
        os.chmod(secret_file, 0o600)
        logger.info(f"Stored secret: {key}")
    
    def get_secret(self, key: str, password: Optional[str] = None) -> Optional[str]:
        """Retrieve a secret"""
        secret_file = self.secrets_dir / f"{key}.json"
        
        if not secret_file.exists():
            logger.warning(f"Secret not found: {key}")
            return None
        
        try:
            with open(secret_file, 'r') as f:
                secret_data = json.load(f)
            
            value = secret_data["value"]
            if secret_data.get("encrypted", True):
                value = self.decrypt_secret(value, password)
            
            return value
        except Exception as e:
            logger.error(f"Failed to retrieve secret {key}: {e}")
            return None
    
    def rotate_secret(self, key: str, password: Optional[str] = None) -> str:
        """Rotate a secret (generate new value)"""
        # Generate new secret based on key type
        if "jwt" in key.lower():
            new_secret = self.generate_jwt_secret()
        elif "database" in key.lower() or "db" in key.lower():
            new_secret = self.generate_database_password()
        elif "api" in key.lower():
            new_secret = self.generate_api_key()
        else:
            new_secret = self.generate_secret()
        
        # Backup old secret
        old_secret = self.get_secret(key, password)
        if old_secret:
            backup_key = f"{key}_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            self.store_secret(backup_key, old_secret, password=password)
        
        # Store new secret
        self.store_secret(key, new_secret, password=password)
        logger.info(f"Rotated secret: {key}")
        
        return new_secret
    
    def list_secrets(self) -> List[Dict[str, Any]]:
        """List all secrets (metadata only)"""
        secrets_list = []
        
        for secret_file in self.secrets_dir.glob("*.json"):
            try:
                with open(secret_file, 'r') as f:
                    secret_data = json.load(f)
                
                secrets_list.append({
                    "key": secret_data["key"],
                    "created_at": secret_data["created_at"],
                    "encrypted": secret_data.get("encrypted", True),
                    "environment": secret_data.get("environment", "unknown")
                })
            except Exception as e:
                logger.error(f"Failed to read secret file {secret_file}: {e}")
        
        return secrets_list
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret"""
        secret_file = self.secrets_dir / f"{key}.json"
        
        if not secret_file.exists():
            logger.warning(f"Secret not found: {key}")
            return False
        
        try:
            secret_file.unlink()
            logger.info(f"Deleted secret: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {key}: {e}")
            return False
    
    def export_secrets(self, output_file: str, password: Optional[str] = None, 
                      include_values: bool = False) -> None:
        """Export secrets to a file"""
        secrets_list = self.list_secrets()
        
        if include_values:
            for secret in secrets_list:
                value = self.get_secret(secret["key"], password)
                if value:
                    secret["value"] = "***REDACTED***"  # Never export actual values
        
        export_data = {
            "environment": self.environment,
            "exported_at": datetime.utcnow().isoformat(),
            "secrets": secrets_list
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Exported {len(secrets_list)} secrets to {output_file}")
    
    def setup_production_secrets(self) -> Dict[str, str]:
        """Setup initial production secrets"""
        secrets_to_create = {
            "jwt_secret": self.generate_jwt_secret(),
            "database_password": self.generate_database_password(),
            "redis_password": self.generate_secret(32),
            "api_key": self.generate_api_key(),
            "webhook_secret": self.generate_secret(32),
            "encryption_key": self.generate_secret(32)
        }
        
        for key, value in secrets_to_create.items():
            self.store_secret(key, value)
        
        logger.info("Setup production secrets")
        return secrets_to_create
    
    def validate_secrets_health(self) -> Dict[str, Any]:
        """Validate secrets health and rotation status"""
        health_report = {
            "environment": self.environment,
            "checked_at": datetime.utcnow().isoformat(),
            "total_secrets": 0,
            "encrypted_secrets": 0,
            "old_secrets": 0,
            "issues": []
        }
        
        secrets_list = self.list_secrets()
        health_report["total_secrets"] = len(secrets_list)
        
        for secret in secrets_list:
            if secret.get("encrypted", True):
                health_report["encrypted_secrets"] += 1
            
            # Check if secret is old (>90 days)
            created_at = datetime.fromisoformat(secret["created_at"])
            age = datetime.utcnow() - created_at
            if age > timedelta(days=90):
                health_report["old_secrets"] += 1
                health_report["issues"].append(
                    f"Secret '{secret['key']}' is {age.days} days old"
                )
        
        # Check for required secrets
        required_secrets = ["jwt_secret", "database_password"]
        for required in required_secrets:
            if not any(s["key"] == required for s in secrets_list):
                health_report["issues"].append(f"Missing required secret: {required}")
        
        return health_report


# Cloud Secrets Manager Integration
class CloudSecretsManager:
    """Integration with cloud secret management services"""
    
    def __init__(self, provider: str = "aws"):
        self.provider = provider.lower()
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize cloud provider client"""
        if self.provider == "aws":
            try:
                import boto3
                self.client = boto3.client('secretsmanager')
            except ImportError:
                logger.warning("boto3 not installed, AWS secrets unavailable")
        elif self.provider == "gcp":
            try:
                from google.cloud import secretmanager
                self.client = secretmanager.SecretManagerServiceClient()
            except ImportError:
                logger.warning("google-cloud-secret-manager not installed")
        elif self.provider == "azure":
            try:
                from azure.keyvault.secrets import SecretClient
                from azure.identity import DefaultAzureCredential
                # Initialize Azure Key Vault client
                logger.info("Azure Key Vault client would be initialized here")
            except ImportError:
                logger.warning("azure-keyvault-secrets not installed")
    
    def store_secret_in_cloud(self, key: str, value: str) -> bool:
        """Store secret in cloud provider"""
        if not self.client:
            logger.error(f"Cloud client not available for provider: {self.provider}")
            return False
        
        try:
            if self.provider == "aws":
                self.client.create_secret(
                    Name=key,
                    SecretString=value,
                    Description=f"LishFind secret: {key}"
                )
            # Add other providers as needed
            
            logger.info(f"Stored secret {key} in {self.provider}")
            return True
        except Exception as e:
            logger.error(f"Failed to store secret in cloud: {e}")
            return False
    
    def get_secret_from_cloud(self, key: str) -> Optional[str]:
        """Retrieve secret from cloud provider"""
        if not self.client:
            logger.error(f"Cloud client not available for provider: {self.provider}")
            return None
        
        try:
            if self.provider == "aws":
                response = self.client.get_secret_value(SecretId=key)
                return response['SecretString']
            # Add other providers as needed
            
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve secret from cloud: {e}")
            return None