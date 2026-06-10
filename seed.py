"""
Bootstrap inicial de PostgreSQL: crea el esquema completo y usuarios base.
Ejecutar una sola vez: python seed.py

Requiere .env con DATABASE_URL o PG_USER / PG_PASSWORD / PG_DATABASE.
"""
import os
import secrets
import sys
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from database import db, configure_database
# Importar todos los modelos para que create_all registre el esquema completo
from models import User, Company, Audit, ChecklistResponse, Finding, Asset, Evidence  # noqa: F401


def get_seed_password(env_var, label):
    password = os.getenv(env_var)
    if not password:
        password = secrets.token_urlsafe(12)
        print(f'[SEED] {env_var} no definida. Contraseña generada para {label}: {password}')
        print('[SEED] Guárdela ahora: no se volverá a mostrar.')
    return password


def seed_db(reset=False, force=False):
    app = Flask(__name__)
    configure_database(app)

    with app.app_context():
        if reset:
            if not force:
                confirm = input(
                    '[SEED] ¡ADVERTENCIA! Se eliminarán TODAS las tablas y datos.\n'
                    '[SEED] Escriba "CONFIRMAR" para continuar: '
                ).strip()
                if confirm != 'CONFIRMAR':
                    print('[SEED] Reset cancelado.')
                    return
            print('[SEED] Eliminando tablas existentes...')
            db.drop_all()

        print('Creando esquema PostgreSQL...')
        db.create_all()

        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email=os.getenv('SEED_ADMIN_EMAIL', 'admin@audit.local'),
                role='superadmin',
            )
            admin.set_password(get_seed_password('SEED_ADMIN_PASSWORD', 'admin'))
            db.session.add(admin)
            print('Usuario admin creado.')
        else:
            print('Usuario admin ya existe.')

        if not User.query.filter_by(username='auditor').first():
            auditor = User(
                username='auditor',
                email=os.getenv('SEED_AUDITOR_EMAIL', 'auditor@audit.local'),
                role='auditor',
            )
            auditor.set_password(get_seed_password('SEED_AUDITOR_PASSWORD', 'auditor'))
            db.session.add(auditor)
            print('Usuario auditor creado.')
        else:
            print('Usuario auditor ya existe.')

        if not Company.query.filter_by(company_name='Empresa Demo S.A.').first():
            demo = Company(
                company_name='Empresa Demo S.A.',
                tax_id='30-71123456-9',
                address='Av. Corrientes 1234',
                city='CABA',
                province='Buenos Aires',
                country='Argentina',
                industry='Tecnología',
                employee_count=45,
                annual_revenue_range='50M-200M',
            )
            db.session.add(demo)
            print('Empresa demo creada.')
        else:
            print('Empresa demo ya existe.')

        db.session.commit()
        print('Bootstrap completado.')


if __name__ == '__main__':
    reset = '--reset' in sys.argv
    force = '--force' in sys.argv  # Para CI/CD sin TTY: python seed.py --reset --force
    seed_db(reset=reset, force=force)
