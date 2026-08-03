"""
Environment Management CLI Tool

Command-line interface for managing production environments:
- Secrets management
- Configuration validation
- Environment switching
- Deployment preparation
"""

import click
import sys
import json
from pathlib import Path
from typing import Optional

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from env_manager.secrets_manager import SecretsManager, CloudSecretsManager
from env_manager.config_validator import ConfigValidator, ValidationLevel
from env_manager.environment_switcher import EnvironmentSwitcher


@click.group()
@click.option('--environment', '-e', default='development', 
              help='Environment to operate on (development, staging, production)')
@click.pass_context
def cli(ctx, environment):
    """LishFind Environment Management CLI"""
    ctx.ensure_object(dict)
    ctx.obj['environment'] = environment


# Secrets Management Commands
@cli.group()
@click.pass_context
def secrets(ctx):
    """Manage application secrets"""
    pass


@secrets.command()
@click.option('--key', '-k', required=True, help='Secret key name')
@click.option('--value', '-v', help='Secret value (will prompt if not provided)')
@click.option('--encrypt/--no-encrypt', default=True, help='Encrypt the secret')
@click.option('--password', '-p', help='Encryption password')
@click.pass_context
def add(ctx, key, value, encrypt, password):
    """Add a new secret"""
    env = ctx.obj['environment']
    manager = SecretsManager(env)
    
    if not value:
        value = click.prompt(f'Enter value for secret "{key}"', hide_input=True)
    
    try:
        manager.store_secret(key, value, encrypt=encrypt, password=password)
        click.echo(f"✅ Secret '{key}' added successfully")
    except Exception as e:
        click.echo(f"❌ Failed to add secret: {e}", err=True)
        sys.exit(1)


@secrets.command()
@click.option('--key', '-k', required=True, help='Secret key name')
@click.option('--password', '-p', help='Encryption password')
@click.pass_context
def get(ctx, key, password):
    """Retrieve a secret"""
    env = ctx.obj['environment']
    manager = SecretsManager(env)
    
    try:
        value = manager.get_secret(key, password=password)
        if value:
            click.echo(f"Secret '{key}': {value}")
        else:
            click.echo(f"❌ Secret '{key}' not found", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Failed to retrieve secret: {e}", err=True)
        sys.exit(1)


@secrets.command()
@click.pass_context
def list(ctx):
    """List all secrets"""
    env = ctx.obj['environment']
    manager = SecretsManager(env)
    
    try:
        secrets_list = manager.list_secrets()
        
        if not secrets_list:
            click.echo("No secrets found")
            return
        
        click.echo(f"\nSecrets in {env} environment:")
        click.echo("-" * 50)
        
        for secret in secrets_list:
            encrypted = "🔒" if secret.get('encrypted', True) else "🔓"
            click.echo(f"{encrypted} {secret['key']} (created: {secret['created_at']})")
            
    except Exception as e:
        click.echo(f"❌ Failed to list secrets: {e}", err=True)
        sys.exit(1)


@secrets.command()
@click.option('--key', '-k', required=True, help='Secret key to rotate')
@click.option('--password', '-p', help='Encryption password')
@click.pass_context
def rotate(ctx, key, password):
    """Rotate a secret (generate new value)"""
    env = ctx.obj['environment']
    manager = SecretsManager(env)
    
    try:
        new_value = manager.rotate_secret(key, password=password)
        click.echo(f"✅ Secret '{key}' rotated successfully")
        click.echo(f"New value: {new_value}")
    except Exception as e:
        click.echo(f"❌ Failed to rotate secret: {e}", err=True)
        sys.exit(1)


@secrets.command()
@click.pass_context
def setup(ctx):
    """Setup initial production secrets"""
    env = ctx.obj['environment']
    manager = SecretsManager(env)
    
    if env != 'production':
        click.echo("⚠️  This command is intended for production environment", err=True)
        if not click.confirm('Continue anyway?'):
            sys.exit(1)
    
    try:
        secrets_created = manager.setup_production_secrets()
        click.echo(f"✅ Created {len(secrets_created)} production secrets:")
        
        for key in secrets_created.keys():
            click.echo(f"  - {key}")
            
    except Exception as e:
        click.echo(f"❌ Failed to setup secrets: {e}", err=True)
        sys.exit(1)


@secrets.command()
@click.pass_context
def health(ctx):
    """Check secrets health status"""
    env = ctx.obj['environment']
    manager = SecretsManager(env)
    
    try:
        health_report = manager.validate_secrets_health()
        
        click.echo(f"\nSecrets Health Report - {env}")
        click.echo("=" * 40)
        click.echo(f"Total secrets: {health_report['total_secrets']}")
        click.echo(f"Encrypted: {health_report['encrypted_secrets']}")
        click.echo(f"Old secrets (>90 days): {health_report['old_secrets']}")
        
        if health_report['issues']:
            click.echo(f"\n⚠️  Issues found:")
            for issue in health_report['issues']:
                click.echo(f"  - {issue}")
        else:
            click.echo("\n✅ No issues found")
            
    except Exception as e:
        click.echo(f"❌ Failed to check health: {e}", err=True)
        sys.exit(1)


# Configuration Validation Commands
@cli.group()
@click.pass_context
def config(ctx):
    """Validate and manage configuration"""
    pass


@config.command()
@click.option('--config-file', '-f', help='Configuration file to validate')
@click.pass_context
def validate(ctx, config_file):
    """Validate environment configuration"""
    env = ctx.obj['environment']
    validator = ConfigValidator(env)
    
    try:
        # Validate environment variables
        env_valid = validator.validate_environment_variables(config_file)
        
        # Validate dependencies
        deps_valid = validator.validate_dependencies()
        
        # Generate report
        report = validator.generate_report()
        
        # Display results
        click.echo(f"\nConfiguration Validation - {env}")
        click.echo("=" * 40)
        
        if report['summary']['passed']:
            click.echo("✅ Configuration is valid")
        else:
            click.echo("❌ Configuration validation failed")
        
        click.echo(f"Errors: {report['summary']['errors']}")
        click.echo(f"Warnings: {report['summary']['warnings']}")
        
        # Show issues
        if report['issues']:
            click.echo("\nIssues:")
            for issue in report['issues']:
                icon = "❌" if issue['level'] == 'error' else "⚠️"
                click.echo(f"{icon} {issue['message']}")
                if issue['suggestion']:
                    click.echo(f"   Suggestion: {issue['suggestion']}")
        
        # Exit with error code if validation failed
        if not report['summary']['passed']:
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Validation failed: {e}", err=True)
        sys.exit(1)


@config.command()
@click.option('--output', '-o', help='Output file for report')
@click.pass_context
def report(ctx, output):
    """Generate configuration validation report"""
    env = ctx.obj['environment']
    validator = ConfigValidator(env)
    
    try:
        # Run validation
        validator.validate_environment_variables()
        validator.validate_dependencies()
        
        # Generate and save report
        if output:
            validator.save_report(output)
            click.echo(f"✅ Report saved to {output}")
        else:
            report = validator.generate_report()
            click.echo(json.dumps(report, indent=2))
            
    except Exception as e:
        click.echo(f"❌ Failed to generate report: {e}", err=True)
        sys.exit(1)


# Environment Switching Commands
@cli.group()
@click.pass_context
def env(ctx):
    """Manage environments"""
    pass


@env.command()
def list():
    """List available environments"""
    switcher = EnvironmentSwitcher()
    environments = switcher.list_environments()
    
    click.echo("\nAvailable Environments:")
    click.echo("-" * 30)
    
    for env_info in environments:
        current = "→" if env_info['current'] else " "
        valid = "✅" if env_info['valid'] else "❌"
        exists = "📁" if env_info['config_exists'] else "❓"
        
        click.echo(f"{current} {exists} {valid} {env_info['name']}")
        if env_info['config_exists'] and env_info['last_modified']:
            click.echo(f"    Last modified: {env_info['last_modified']}")


@env.command()
@click.argument('target_env')
@click.option('--no-backup', is_flag=True, help='Skip backing up current .env')
def switch(target_env, no_backup):
    """Switch to target environment"""
    switcher = EnvironmentSwitcher()
    
    try:
        success = switcher.switch_environment(target_env, backup=not no_backup)
        if success:
            click.echo(f"✅ Switched to {target_env} environment")
        else:
            click.echo(f"❌ Failed to switch to {target_env}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Switch failed: {e}", err=True)
        sys.exit(1)


@env.command()
@click.argument('env_name')
@click.option('--from-env', help='Copy from existing environment')
def create(env_name, from_env):
    """Create new environment configuration"""
    switcher = EnvironmentSwitcher()
    
    try:
        success = switcher.create_environment_template(env_name, from_env)
        if success:
            click.echo(f"✅ Created {env_name} environment")
        else:
            click.echo(f"❌ Failed to create {env_name}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Creation failed: {e}", err=True)
        sys.exit(1)


@env.command()
@click.argument('env_name')
def validate_env(env_name):
    """Validate environment setup"""
    switcher = EnvironmentSwitcher()
    
    try:
        result = switcher.validate_environment_setup(env_name)
        
        click.echo(f"\nEnvironment Validation - {env_name}")
        click.echo("=" * 30)
        
        if result['valid']:
            click.echo("✅ Environment is valid")
        else:
            click.echo("❌ Environment validation failed")
        
        if result['issues']:
            click.echo("\nIssues:")
            for issue in result['issues']:
                click.echo(f"❌ {issue}")
        
        if result['warnings']:
            click.echo("\nWarnings:")
            for warning in result['warnings']:
                click.echo(f"⚠️ {warning}")
        
        if not result['valid']:
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Validation failed: {e}", err=True)
        sys.exit(1)


@env.command()
@click.argument('env1')
@click.argument('env2')
def diff(env1, env2):
    """Show differences between two environments"""
    switcher = EnvironmentSwitcher()
    
    try:
        diff_result = switcher.get_environment_diff(env1, env2)
        
        if 'error' in diff_result:
            click.echo(f"❌ {diff_result['error']}", err=True)
            sys.exit(1)
        
        click.echo(f"\nEnvironment Diff: {env1} ↔ {env2}")
        click.echo("=" * 40)
        
        if diff_result['only_in_1']:
            click.echo(f"\nOnly in {env1}:")
            for key, value in diff_result['only_in_1'].items():
                click.echo(f"  {key}={value}")
        
        if diff_result['only_in_2']:
            click.echo(f"\nOnly in {env2}:")
            for key, value in diff_result['only_in_2'].items():
                click.echo(f"  {key}={value}")
        
        if diff_result['different_values']:
            click.echo(f"\nDifferent values:")
            for key, values in diff_result['different_values'].items():
                click.echo(f"  {key}:")
                click.echo(f"    {env1}: {values[env1]}")
                click.echo(f"    {env2}: {values[env2]}")
        
        if not any([diff_result['only_in_1'], diff_result['only_in_2'], diff_result['different_values']]):
            click.echo("✅ No differences found")
            
    except Exception as e:
        click.echo(f"❌ Diff failed: {e}", err=True)
        sys.exit(1)


# Deployment Commands
@cli.group()
def deploy():
    """Deployment utilities"""
    pass


@deploy.command()
@click.option('--environment', '-e', default='production', 
              help='Target environment')
@click.option('--platform', '-p', 
              type=click.Choice(['railway', 'render', 'fly', 'heroku', 'vercel']),
              help='Deployment platform')
@click.option('--validate-only', is_flag=True, help='Only validate, do not deploy')
def prepare(environment, platform, validate_only):
    """Prepare for deployment"""
    click.echo(f"Preparing {environment} deployment for {platform or 'multiple platforms'}...")
    
    # Validate configuration
    validator = ConfigValidator(environment)
    env_valid = validator.validate_environment_variables()
    
    if not env_valid:
        click.echo("❌ Configuration validation failed", err=True)
        report = validator.generate_report()
        for issue in report['issues']:
            if issue['level'] == 'error':
                click.echo(f"  {issue['message']}")
        sys.exit(1)
    
    # Validate secrets
    secrets_manager = SecretsManager(environment)
    health_report = secrets_manager.validate_secrets_health()
    
    if health_report['issues']:
        click.echo("⚠️  Secrets health issues found:")
        for issue in health_report['issues']:
            click.echo(f"  {issue}")
    
    if validate_only:
        click.echo("✅ Validation completed")
        return
    
    click.echo("✅ Environment ready for deployment")
    
    if platform:
        click.echo(f"\nNext steps for {platform}:")
        _show_deployment_steps(platform, environment)


def _show_deployment_steps(platform: str, environment: str):
    """Show platform-specific deployment steps"""
    steps = {
        'railway': [
            "1. Install Railway CLI: npm install -g @railway/cli",
            "2. Login: railway login",
            "3. Deploy: railway up --service backend",
        ],
        'render': [
            "1. Connect GitHub repository to Render",
            "2. Set environment variables in Render dashboard",
            "3. Deploy using render.yaml configuration",
        ],
        'fly': [
            "1. Install Fly CLI: curl -L https://fly.io/install.sh | sh",
            "2. Login: flyctl auth login",
            "3. Deploy: flyctl deploy",
        ],
        'heroku': [
            "1. Install Heroku CLI",
            "2. Login: heroku login",
            "3. Deploy: git push heroku main",
        ],
        'vercel': [
            "1. Install Vercel CLI: npm install -g vercel",
            "2. Login: vercel login", 
            "3. Deploy: vercel --prod",
        ]
    }
    
    for step in steps.get(platform, []):
        click.echo(step)


if __name__ == '__main__':
    cli()