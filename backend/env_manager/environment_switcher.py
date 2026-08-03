"""
Environment Switching Utilities

Provides tools for switching between different environments:
- Environment configuration management
- Database switching utilities
- Service configuration switching
- Deployment environment management
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EnvironmentSwitcher:
    """Manages switching between different environments"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.environments = ["development", "staging", "production"]
        self.current_env = self._detect_current_environment()
        
    def _detect_current_environment(self) -> str:
        """Detect current environment"""
        # Check environment variable
        env = os.getenv('ENVIRONMENT')
        if env and env in self.environments:
            return env
            
        # Check .env file
        env_file = self.project_root / '.env'
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.strip().startswith('ENVIRONMENT='):
                            env = line.split('=', 1)[1].strip().strip('"\'')
                            if env in self.environments:
                                return env
            except Exception as e:
                logger.warning(f"Failed to read .env file: {e}")
        
        # Default to development
        return "development"
    
    def list_environments(self) -> List[Dict[str, Any]]:
        """List available environments with their status"""
        envs = []
        
        for env in self.environments:
            env_file = self.project_root / f'.env.{env}'
            config = {
                'name': env,
                'current': env == self.current_env,
                'config_exists': env_file.exists(),
                'config_file': str(env_file)
            }
            
            # Check if config is valid
            if config['config_exists']:
                config['valid'] = self._validate_env_config(env_file)
                config['last_modified'] = datetime.fromtimestamp(
                    env_file.stat().st_mtime
                ).isoformat()
            else:
                config['valid'] = False
                config['last_modified'] = None
            
            envs.append(config)
        
        return envs
    
    def _validate_env_config(self, env_file: Path) -> bool:
        """Basic validation of environment config file"""
        try:
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Check for required variables
            required_vars = ['ENVIRONMENT', 'DATABASE_URL', 'SECRET_KEY']
            for var in required_vars:
                if f'{var}=' not in content:
                    return False
            
            return True
        except Exception:
            return False
    
    def switch_environment(self, target_env: str, backup: bool = True) -> bool:
        """Switch to target environment"""
        if target_env not in self.environments:
            logger.error(f"Invalid environment: {target_env}")
            return False
        
        if target_env == self.current_env:
            logger.info(f"Already using environment: {target_env}")
            return True
        
        # Backup current .env if requested
        if backup:
            self._backup_current_env()
        
        # Copy target environment config
        target_file = self.project_root / f'.env.{target_env}'
        main_env_file = self.project_root / '.env'
        
        if not target_file.exists():
            logger.error(f"Environment config not found: {target_file}")
            return False
        
        try:
            shutil.copy2(target_file, main_env_file)
            self.current_env = target_env
            
            # Update environment variable
            os.environ['ENVIRONMENT'] = target_env
            
            logger.info(f"Switched to environment: {target_env}")
            
            # Run post-switch hooks
            self._run_post_switch_hooks(target_env)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch environment: {e}")
            return False
    
    def _backup_current_env(self):
        """Backup current .env file"""
        main_env_file = self.project_root / '.env'
        if main_env_file.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.project_root / f'.env.backup.{timestamp}'
            shutil.copy2(main_env_file, backup_file)
            logger.info(f"Backed up current .env to {backup_file}")
    
    def _run_post_switch_hooks(self, environment: str):
        """Run post-switch hooks for the environment"""
        hooks_dir = self.project_root / 'scripts' / 'env-hooks'
        
        if not hooks_dir.exists():
            return
        
        # Run global hooks
        global_hook = hooks_dir / 'post-switch.sh'
        if global_hook.exists():
            self._run_hook_script(global_hook, environment)
        
        # Run environment-specific hooks
        env_hook = hooks_dir / f'post-switch-{environment}.sh'
        if env_hook.exists():
            self._run_hook_script(env_hook, environment)
    
    def _run_hook_script(self, script_path: Path, environment: str):
        """Run a hook script"""
        try:
            env = os.environ.copy()
            env['TARGET_ENVIRONMENT'] = environment
            env['PROJECT_ROOT'] = str(self.project_root)
            
            result = subprocess.run(
                ['bash', str(script_path)],
                cwd=self.project_root,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"Hook script completed: {script_path}")
                if result.stdout:
                    logger.info(f"Hook output: {result.stdout}")
            else:
                logger.warning(f"Hook script failed: {script_path}")
                if result.stderr:
                    logger.warning(f"Hook error: {result.stderr}")
                    
        except Exception as e:
            logger.error(f"Failed to run hook script {script_path}: {e}")
    
    def create_environment_template(self, env_name: str, 
                                  source_env: Optional[str] = None) -> bool:
        """Create a new environment configuration template"""
        if env_name in self.environments:
            logger.warning(f"Environment {env_name} already exists")
        
        env_file = self.project_root / f'.env.{env_name}'
        
        if source_env and source_env in self.environments:
            # Copy from source environment
            source_file = self.project_root / f'.env.{source_env}'
            if source_file.exists():
                shutil.copy2(source_file, env_file)
                logger.info(f"Created {env_name} environment from {source_env}")
            else:
                logger.error(f"Source environment file not found: {source_file}")
                return False
        else:
            # Create from template
            template_content = self._get_env_template(env_name)
            try:
                with open(env_file, 'w') as f:
                    f.write(template_content)
                logger.info(f"Created {env_name} environment template")
            except Exception as e:
                logger.error(f"Failed to create environment template: {e}")
                return False
        
        # Add to environments list if not already there
        if env_name not in self.environments:
            self.environments.append(env_name)
        
        return True
    
    def _get_env_template(self, env_name: str) -> str:
        """Get environment template content"""
        template = f"""# {env_name.upper()} Environment Configuration
# Generated on {datetime.now().isoformat()}

# Environment
ENVIRONMENT={env_name}

# Application
DEBUG={"true" if env_name == "development" else "false"}
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=sqlite:///lishfind_{env_name}.db

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Security
ALLOWED_HOSTS={"localhost,127.0.0.1" if env_name == "development" else "your-domain.com"}
CORS_ORIGINS={"http://localhost:3000" if env_name == "development" else "https://your-domain.com"}

# Logging
LOG_LEVEL={"DEBUG" if env_name == "development" else "INFO"}

# External APIs (optional)
OPENAI_API_KEY=your-openai-key-here
GEMINI_API_KEY=your-gemini-key-here

# Monitoring (production/staging)
SENTRY_DSN=your-sentry-dsn-here

# Email (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
"""
        
        if env_name == "production":
            template += """
# Production-specific
ENABLE_HTTPS=true
SECURE_COOKIES=true
CSRF_COOKIE_SECURE=true
SESSION_COOKIE_SECURE=true

# Performance
MAX_CONNECTIONS=100
WORKER_TIMEOUT=30
"""
        
        return template
    
    def sync_environment_changes(self, source_env: str, target_env: str, 
                               exclude_keys: Optional[List[str]] = None) -> bool:
        """Sync configuration changes between environments"""
        source_file = self.project_root / f'.env.{source_env}'
        target_file = self.project_root / f'.env.{target_env}'
        
        if not source_file.exists():
            logger.error(f"Source environment file not found: {source_file}")
            return False
        
        if not target_file.exists():
            logger.error(f"Target environment file not found: {target_file}")
            return False
        
        exclude_keys = exclude_keys or [
            'ENVIRONMENT', 'DEBUG', 'DATABASE_URL', 'ALLOWED_HOSTS', 
            'CORS_ORIGINS', 'SECRET_KEY'
        ]
        
        try:
            # Read source config
            source_config = self._read_env_file(source_file)
            target_config = self._read_env_file(target_file)
            
            # Sync non-excluded keys
            changes = []
            for key, value in source_config.items():
                if key not in exclude_keys:
                    if key not in target_config or target_config[key] != value:
                        target_config[key] = value
                        changes.append(key)
            
            # Write updated target config
            self._write_env_file(target_file, target_config)
            
            if changes:
                logger.info(f"Synced {len(changes)} variables from {source_env} to {target_env}: {changes}")
            else:
                logger.info(f"No changes needed between {source_env} and {target_env}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync environments: {e}")
            return False
    
    def _read_env_file(self, file_path: Path) -> Dict[str, str]:
        """Read environment file into dictionary"""
        config = {}
        
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip().strip('"\'')
        
        return config
    
    def _write_env_file(self, file_path: Path, config: Dict[str, str]):
        """Write configuration dictionary to environment file"""
        # Read original file to preserve comments and structure
        original_lines = []
        if file_path.exists():
            with open(file_path, 'r') as f:
                original_lines = f.readlines()
        
        # Update existing lines and track processed keys
        processed_keys = set()
        updated_lines = []
        
        for line in original_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and '=' in stripped:
                key = stripped.split('=', 1)[0].strip()
                if key in config:
                    updated_lines.append(f'{key}={config[key]}\n')
                    processed_keys.add(key)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        # Add new keys at the end
        for key, value in config.items():
            if key not in processed_keys:
                updated_lines.append(f'{key}={value}\n')
        
        # Write updated content
        with open(file_path, 'w') as f:
            f.writelines(updated_lines)
    
    def validate_environment_setup(self, env_name: str) -> Dict[str, Any]:
        """Validate environment setup"""
        validation_result = {
            'environment': env_name,
            'valid': True,
            'issues': [],
            'warnings': []
        }
        
        env_file = self.project_root / f'.env.{env_name}'
        
        # Check if config file exists
        if not env_file.exists():
            validation_result['valid'] = False
            validation_result['issues'].append(f"Configuration file not found: {env_file}")
            return validation_result
        
        try:
            config = self._read_env_file(env_file)
            
            # Check required variables
            required_vars = ['ENVIRONMENT', 'DATABASE_URL', 'SECRET_KEY']
            for var in required_vars:
                if var not in config:
                    validation_result['valid'] = False
                    validation_result['issues'].append(f"Missing required variable: {var}")
                elif not config[var] or config[var] == f'your-{var.lower().replace("_", "-")}-here':
                    validation_result['valid'] = False
                    validation_result['issues'].append(f"Variable {var} is not configured")
            
            # Check environment-specific requirements
            if env_name == 'production':
                prod_requirements = ['ALLOWED_HOSTS', 'CORS_ORIGINS']
                for var in prod_requirements:
                    if var not in config:
                        validation_result['warnings'].append(f"Production should have {var} configured")
            
            # Check for placeholder values
            placeholder_patterns = ['your-', 'changeme', 'example', 'localhost']
            for key, value in config.items():
                if any(pattern in value.lower() for pattern in placeholder_patterns):
                    if key not in ['ALLOWED_HOSTS', 'CORS_ORIGINS'] or env_name != 'development':
                        validation_result['warnings'].append(f"{key} appears to use placeholder value: {value}")
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['issues'].append(f"Failed to validate config: {e}")
        
        return validation_result
    
    def get_environment_diff(self, env1: str, env2: str) -> Dict[str, Any]:
        """Get differences between two environments"""
        file1 = self.project_root / f'.env.{env1}'
        file2 = self.project_root / f'.env.{env2}'
        
        if not file1.exists() or not file2.exists():
            return {'error': 'One or both environment files not found'}
        
        try:
            config1 = self._read_env_file(file1)
            config2 = self._read_env_file(file2)
            
            diff = {
                'environment_1': env1,
                'environment_2': env2,
                'only_in_1': {},
                'only_in_2': {},
                'different_values': {},
                'same_values': {}
            }
            
            all_keys = set(config1.keys()) | set(config2.keys())
            
            for key in all_keys:
                if key in config1 and key not in config2:
                    diff['only_in_1'][key] = config1[key]
                elif key in config2 and key not in config1:
                    diff['only_in_2'][key] = config2[key]
                elif config1[key] != config2[key]:
                    diff['different_values'][key] = {
                        env1: config1[key],
                        env2: config2[key]
                    }
                else:
                    diff['same_values'][key] = config1[key]
            
            return diff
            
        except Exception as e:
            return {'error': f'Failed to compare environments: {e}'}