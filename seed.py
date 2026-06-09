import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from database import db
from models import User, Company

def seed_db():
    app = Flask(__name__)
    # Use SQLite for default local seeding, or Postgres if DATABASE_URL is set
    db_url = os.getenv('DATABASE_URL') or 'sqlite:///audit.db'
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+pg8000://')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        print("Creando tablas en la base de datos...")
        db.create_all()
        
        # Check if users already exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("Creando usuario Administrador por defecto...")
            admin = User(
                username='admin',
                email='admin@theminihack.com',
                role='superadmin'
            )
            admin.set_password('adminpassword123')
            db.session.add(admin)
        else:
            print("Usuario admin ya existe.")

        auditor_user = User.query.filter_by(username='auditor').first()
        if not auditor_user:
            print("Creando usuario Auditor por defecto...")
            auditor = User(
                username='auditor',
                email='auditor@theminihack.com',
                role='auditor'
            )
            auditor.set_password('auditorpassword123')
            db.session.add(auditor)
        else:
            print("Usuario auditor ya existe.")
            
        # Add a test company to facilitate quick manual verification
        test_company = Company.query.filter_by(company_name='Empresa Demo S.A.').first()
        if not test_company:
            print("Creando empresa demo...")
            demo = Company(
                company_name='Empresa Demo S.A.',
                tax_id='30-71123456-9',
                address='Av. Corrientes 1234',
                city='CABA',
                province='Buenos Aires',
                country='Argentina',
                industry='Tecnología',
                employee_count=45,
                annual_revenue_range='50M-200M'
            )
            db.session.add(demo)
            
        db.session.commit()
        print("Base de datos inicializada y poblada con éxito!")

if __name__ == '__main__':
    seed_db()
