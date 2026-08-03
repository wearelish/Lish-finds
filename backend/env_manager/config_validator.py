"""
Configuration Validation System

Validates environment configurations including:
- Environment variable validation
- Configuration schema validation
- Security settings verification
- Dependency compatibility checks
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a configuration validation"""
    level: ValidationLevel
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None


class ConfigValidator:
    """Validates application configuration"""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.results: List[ValidationResult] = []
        
    def clear_results(self):
        """Clear validation results"""
        self.results = []
    
    def add_result(self, level: ValidationLevel, message: str, 
                  field: Optional[str] = None, suggestion: Optional[str] = None):
        """Add validation result"""
        result = ValidationResult(level, message, field, suggestion)
        self.results.append(result)
        
    def validate_environment_variables(self, config_path: Optional[str] = None) -> bool:
        """Validate environment variables"""
        self.clear_results()
        
        # Load environment file if provided
        if config_path:
            self._load_env_file(config_path)
        
        # Define required variables by environment
        required_vars = self._get_required_variables()
        optional_vars = self._get_optional_variables()
        
        # Check required variables
        all_valid = True
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                self.add_result(
                    ValidationLevel.ERROR,
                    f"Required environment variable '{var}' is not set",
                    field=var,
                    suggestion=f"Set {var} in your environment or .env file"
                )
                all_valid = False
            else:
                # Validate variable format
                if not self._validate_variable_format(var, value):
                    all_valid = False
        
        # Check optional variables
        for var in optional_vars:
            value = os.getenv(var)
            if value:
                self._validate_variable_format(var, value)
        
        # Check for deprecated variables
        self._check_deprecated_variables()
        
        # Check for security issues
        self._check_security_issues()
        
        return all_valid
    
    def _load_env_file(self, file_path: str):
        """Load environment variables from file"""
        if not os.path.exists(file_path):
            self.add_result(
                ValidationLevel.WARNING,
                f"Environment file not found: {file_path}"
            )
            return
        
        try:
            with open(file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip()
                        else:
                            self.add_result(
                                ValidationLevel.WARNING,
                                f"Invalid line format in {file_path}:{line_num}: {line}"
                            )
        except Exception as e:
            self.add_result(
                ValidationLevel.ERROR,
                f"Failed to load environment file {file_path}: {e}"
            )
    
    def _get_required_variables(self) -> List[str]:
        """Get required environment variables by environment"""
        base_required = [
            "SECRET_KEY",
            "DATABASE_URL",
            "ENVIRONMENT"
        ]
        
        if self.environment == "production":
            base_required.extend([
                "ALLOWED_HOSTS",
                "CORS_ORIGINS",
                "SENTRY_DSN",
                "LOG_LEVEL"
            ])
        elif self.environment == "staging":
            base_required.extend([
                "ALLOWED_HOSTS",
                "CORS_ORIGINS"
            ])
        
        return base_required
    
    def _get_optional_variables(self) -> List[str]:
        """Get optional environment variables"""
        return [
            "REDIS_URL",
            "OPENAI_API_KEY",
            "GEMINI_API_KEY",
            "SENTRY_DSN",
            "NEW_RELIC_LICENSE_KEY",
            "DATADOG_API_KEY",
            "SMTP_SERVER",
            "SMTP_PORT",
            "SMTP_USERNAME",
            "SMTP_PASSWORD",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "GCP_PROJECT_ID",
            "AZURE_TENANT_ID"
        ]
    
    def _validate_variable_format(self, var: str, value: str) -> bool:
        """Validate format of specific variables"""
        valid = True
        
        # URL validation
        if var.endswith('_URL') or var in ['DATABASE_URL', 'REDIS_URL']:
            if not self._is_valid_url(value):
                self.add_result(
                    ValidationLevel.ERROR,
                    f"Invalid URL format for {var}: {value}",
                    field=var,
                    suggestion="Use format: scheme://[user:password@]host[:port]/path"
                )
                valid = False
        
        # Secret key validation
        elif var in ['SECRET_KEY', 'JWT_SECRET']:
            if len(value) < 32:
                self.add_result(
                    ValidationLevel.WARNING,
                    f"{var} should be at least 32 characters long",
                    field=var,
                    suggestion="Use a cryptographically secure random string"
                )
            
            if value in ['your-secret-key', 'changeme', 'secret']:
                self.add_result(
                    ValidationLevel.ERROR,
                    f"{var} is using a default/insecure value",
                    field=var,
                    suggestion="Generate a secure random secret"
                )
                valid = False
        
        # Email validation
        elif 'EMAIL' in var or 'SMTP' in var:
            if '@' in value and not self._is_valid_email(value):
                self.add_result(
                    ValidationLevel.WARNING,
                    f"Invalid email format for {var}: {value}",
                    field=var
                )
        
        # Port validation
        elif 'PORT' in var:
            try:
                port = int(value)
                if port < 1 or port > 65535:
                    self.add_result(
                        ValidationLevel.ERROR,
                        f"Invalid port number for {var}: {value}",
                        field=var,
                        suggestion="Port must be between 1 and 65535"
                    )
                    valid = False
            except ValueError:
                self.add_result(
                    ValidationLevel.ERROR,
                    f"{var} must be a valid integer: {value}",
                    field=var
                )
                valid = False
        
        # Boolean validation
        elif var in ['DEBUG', 'TESTING', 'USE_REDIS', 'ENABLE_CORS']:
            if value.lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                self.add_result(
                    ValidationLevel.WARNING,
                    f"{var} should be a boolean value: {value}",
                    field=var,
                    suggestion="Use: true, false, 1, 0, yes, or no"
                )
        
        return valid
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None
    
    def _is_valid_email(self, email: str) -> bool:
        """Check if email is valid"""
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return email_pattern.match(email) is not None
    
    def _check_deprecated_variables(self):
        """Check for deprecated environment variables"""
        deprecated_vars = {
            'REDIS_HOST': 'Use REDIS_URL instead',
            'DB_HOST': 'Use DATABASE_URL instead',
            'API_HOST': 'Use ALLOWED_HOSTS instead'
        }
        
        for old_var, suggestion in deprecated_vars.items():
            if os.getenv(old_var):
                self.add_result(
                    ValidationLevel.WARNING,
                    f"Deprecated variable '{old_var}' is set",
                    field=old_var,
                    suggestion=suggestion
                )
    
    def _check_security_issues(self):
        """Check for security-related configuration issues"""
        # Check debug mode in production
        if self.environment == "production":
            debug = os.getenv('DEBUG', '').lower()
            if debug in ['true', '1', 'yes']:
                self.add_result(
                    ValidationLevel.ERROR,
                    "DEBUG mode is enabled in production",
                    field='DEBUG',
                    suggestion="Set DEBUG=false in production"
                )
        
        # Check for insecure CORS settings
        cors_origins = os.getenv('CORS_ORIGINS', '')
        if cors_origins == '*':
            self.add_result(
                ValidationLevel.WARNING,
                "CORS is configured to allow all origins",
                field='CORS_ORIGINS',
                suggestion="Specify exact origins for better security"
            )
        
        # Check for weak passwords in URLs
        database_url = os.getenv('DATABASE_URL', '')
        if database_url and ('password=123' in database_url or 'password=password' in database_url):
            self.add_result(
                ValidationLevel.ERROR,
                "Weak password detected in DATABASE_URL",
                field='DATABASE_URL',
                suggestion="Use a strong, unique password"
            )
    
    def validate_config_schema(self, config_file: str) -> bool:
        """Validate configuration against schema"""
        if not os.path.exists(config_file):
            self.add_result(
                ValidationLevel.ERROR,
                f"Configuration file not found: {config_file}"
            )
            return False
        
        try:
            with open(config_file, 'r') as f:
                if config_file.endswith('.json'):
                    config = json.load(f)
                elif config_file.endswith(('.yml', '.yaml')):
                    config = yaml.safe_load(f)
                else:
                    self.add_result(
                        ValidationLevel.ERROR,
                        f"Unsupported config file format: {config_file}"
                    )
                    return False
            
            return self._validate_config_structure(config)
            
        except Exception as e:
            self.add_result(
                ValidationLevel.ERROR,
                f"Failed to parse config file {config_file}: {e}"
            )
            return False
    
    def _validate_config_structure(self, config: Dict[str, Any]) -> bool:
        """Validate configuration structure"""
        valid = True
        
        # Check required sections
        required_sections = ['database', 'security', 'logging']
        for section in required_sections:
            if section not in config:
                self.add_result(
                    ValidationLevel.ERROR,
                    f"Missing required configuration section: {section}",
                    field=section
                )
                valid = False
        
        # Validate database configuration
        if 'database' in config:
            db_config = config['database']
            if 'url' not in db_config and 'host' not in db_config:
                self.add_result(
                    ValidationLevel.ERROR,
                    "Database configuration must include 'url' or 'host'",
                    field='database'
                )
                valid = False
        
        # Validate security configuration
        if 'security' in config:
            sec_config = config['security']
            if 'secret_key' not in sec_config:
                self.add_result(
                    ValidationLevel.ERROR,
                    "Security configuration must include 'secret_key'",
                    field='security.secret_key'
                )
                valid = False
        
        return valid
    
    def validate_dependencies(self) -> bool:
        """Validate dependency compatibility"""
        valid = True
        
        # Check if requirements.txt exists
        req_file = Path('requirements.txt')
        if not req_file.exists():
            self.add_result(
                ValidationLevel.WARNING,
                "requirements.txt not found"
            )
            return True
        
        try:
            with open(req_file, 'r') as f:
                requirements = f.read().splitlines()
            
            # Check for conflicting packages
            conflicts = self._check_package_conflicts(requirements)
            if conflicts:
                for conflict in conflicts:
                    self.add_result(
                        ValidationLevel.WARNING,
                        f"Potential package conflict: {conflict}"
                    )
            
            # Check for security vulnerabilities (basic check)
            vulnerable = self._check_vulnerable_packages(requirements)
            if vulnerable:
                for vuln in vulnerable:
                    self.add_result(
                        ValidationLevel.ERROR,
                        f"Vulnerable package detected: {vuln}",
                        suggestion="Update to a secure version"
                    )
                    valid = False
                    
        except Exception as e:
            self.add_result(
                ValidationLevel.ERROR,
                f"Failed to validate dependencies: {e}"
            )
            valid = False
        
        return valid
    
    def _check_package_conflicts(self, requirements: List[str]) -> List[str]:
        """Check for known package conflicts"""
        conflicts = []
        packages = [req.split('==')[0].split('>=')[0].split('<=')[0] 
                   for req in requirements if not req.startswith('#')]
        
        # Known conflicts
        conflict_pairs = [
            ('tensorflow', 'tensorflow-gpu'),
            ('pillow', 'pil')
        ]
        
        for pkg1, pkg2 in conflict_pairs:
            if pkg1 in packages and pkg2 in packages:
                conflicts.append(f"{pkg1} and {pkg2}")
        
        return conflicts
    
    def _check_vulnerable_packages(self, requirements: List[str]) -> List[str]:
        """Check for known vulnerable packages (basic implementation)"""
        vulnerable = []
        
        # This is a basic implementation. In production, use a proper 
        # vulnerability database like safety or snyk
        known_vulnerable = {
            'django<2.2.13': 'CVE-2020-13254',
            'flask<1.1.4': 'CVE-2021-23385',
            'requests<2.20.0': 'CVE-2018-18074'
        }
        
        for req in requirements:
            if not req.strip() or req.startswith('#'):
                continue
                
            for vuln_pattern, cve in known_vulnerable.items():
                if req.startswith(vuln_pattern.split('<')[0]):
                    vulnerable.append(f"{req} ({cve})")
        
        return vulnerable
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate validation report"""
        errors = [r for r in self.results if r.level == ValidationLevel.ERROR]
        warnings = [r for r in self.results if r.level == ValidationLevel.WARNING]
        info = [r for r in self.results if r.level == ValidationLevel.INFO]
        
        report = {
            'environment': self.environment,
            'timestamp': datetime.utcnow().isoformat(),
            'summary': {
                'total_issues': len(self.results),
                'errors': len(errors),
                'warnings': len(warnings),
                'info': len(info),
                'passed': len(errors) == 0
            },
            'issues': [
                {
                    'level': r.level.value,
                    'message': r.message,
                    'field': r.field,
                    'suggestion': r.suggestion
                }
                for r in self.results
            ]
        }
        
        return report
    
    def save_report(self, output_file: str):
        """Save validation report to file"""
        report = self.generate_report()
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Validation report saved to {output_file}")


from datetime import datetime