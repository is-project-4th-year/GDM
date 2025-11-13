import click
from flask import current_app
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from app import db
from app.models.user import User


@click.command()
@click.option('--name', prompt='Admin full name', help='Full name of the admin user')
@click.option('--email', prompt='Admin email', help='Email address for the admin user')
@click.option('--password', prompt=True, hide_input=True, 
              confirmation_prompt=True, help='Password for the admin user')
@with_appcontext
def create_admin(name, email, password):
    """Create an admin user."""
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email.lower()).first()
    if existing_user:
        click.echo(f'Error: User with email {email} already exists.')
        return
    
    try:
        # Create admin user
        admin = User.create_admin(name=name, email=email, password=password)
        
        # Save to database
        db.session.add(admin)
        db.session.commit()
        
        click.echo(f'✅ Admin user created successfully!')
        click.echo(f'   Name: {admin.name}')
        click.echo(f'   Email: {admin.email}')
        click.echo(f'   Role: {admin.role}')
        click.echo(f'\nYou can now log in at: http://localhost:5000/auth/login')
        
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error creating admin user: {str(e)}')


@click.command()
@with_appcontext
def init_db():
    """Initialize the database."""
    try:
        db.create_all()
        click.echo('✅ Database initialized successfully!')
    except Exception as e:
        click.echo(f'Error initializing database: {str(e)}')


def register_cli_commands(app):
    """Register CLI commands with the Flask app."""
    app.cli.add_command(create_admin)
    app.cli.add_command(init_db)