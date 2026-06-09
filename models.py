from datetime import datetime
from database import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='auditor')  # 'superadmin', 'auditor'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    audits = db.relationship('Audit', backref='auditor', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    tax_id = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    province = db.Column(db.String(100))
    country = db.Column(db.String(100), default='Argentina')
    industry = db.Column(db.String(100))
    employee_count = db.Column(db.Integer)
    annual_revenue_range = db.Column(db.String(100))  # e.g. '0-50M', '50M-200M'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    audits = db.relationship('Audit', backref='company', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'company_name': self.company_name,
            'tax_id': self.tax_id,
            'address': self.address,
            'city': self.city,
            'province': self.province,
            'country': self.country,
            'industry': self.industry,
            'employee_count': self.employee_count,
            'annual_revenue_range': self.annual_revenue_range,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Audit(db.Model):
    __tablename__ = 'audits'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    auditor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    audit_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='draft')  # 'draft', 'in_progress', 'completed', 'delivered'
    risk_score = db.Column(db.Float, default=0.0)
    risk_level = db.Column(db.String(20), default='Low')  # 'Low', 'Medium', 'High', 'Critical'
    executive_summary = db.Column(db.Text)
    recommendations_ai = db.Column(db.Text)
    action_plan_30 = db.Column(db.Text)
    action_plan_60 = db.Column(db.Text)
    action_plan_90 = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    checklist_responses = db.relationship('ChecklistResponse', backref='audit', lazy=True, cascade='all, delete-orphan')
    findings = db.relationship('Finding', backref='audit', lazy=True, cascade='all, delete-orphan')
    assets = db.relationship('Asset', backref='audit', lazy=True, cascade='all, delete-orphan')
    evidences = db.relationship('Evidence', backref='audit', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'auditor_id': self.auditor_id,
            'audit_date': self.audit_date.isoformat() if self.audit_date else None,
            'status': self.status,
            'risk_score': self.risk_score,
            'risk_level': self.risk_level,
            'executive_summary': self.executive_summary,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ChecklistResponse(db.Model):
    __tablename__ = 'checklist_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey('audits.id', ondelete='CASCADE'), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    question_key = db.Column(db.String(100), nullable=False)
    response = db.Column(db.String(10), default='NA')  # 'YES', 'NO', 'NA'
    observations = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'audit_id': self.audit_id,
            'category': self.category,
            'question_key': self.question_key,
            'response': self.response,
            'observations': self.observations,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Finding(db.Model):
    __tablename__ = 'findings'
    
    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey('audits.id', ondelete='CASCADE'), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    impact = db.Column(db.String(20), default='Medium')  # 'Low', 'Medium', 'High', 'Critical'
    probability = db.Column(db.String(20), default='Medium')  # 'Low', 'Medium', 'High'
    risk_level = db.Column(db.String(20), default='Medium')  # 'Low', 'Medium', 'High', 'Critical'
    recommendation = db.Column(db.Text)
    status = db.Column(db.String(20), default='open')  # 'open', 'resolved'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    evidences = db.relationship('Evidence', backref='finding', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'audit_id': self.audit_id,
            'category': self.category,
            'title': self.title,
            'description': self.description,
            'impact': self.impact,
            'probability': self.probability,
            'risk_level': self.risk_level,
            'recommendation': self.recommendation,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Evidence(db.Model):
    __tablename__ = 'evidences'
    
    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey('audits.id', ondelete='CASCADE'), nullable=False)
    finding_id = db.Column(db.Integer, db.ForeignKey('findings.id', ondelete='SET NULL'), nullable=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # e.g., 'png', 'jpg', 'pdf', 'docx'
    file_path = db.Column(db.String(500), nullable=False)  # local path or URL
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'audit_id': self.audit_id,
            'finding_id': self.finding_id,
            'file_name': self.file_name,
            'file_type': self.file_type,
            'file_path': self.file_path,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None
        }


class Asset(db.Model):
    __tablename__ = 'assets'
    
    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey('audits.id', ondelete='CASCADE'), nullable=False)
    asset_type = db.Column(db.String(50), nullable=False)  # 'PC', 'Notebook', 'Server', 'Router', etc.
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    operating_system = db.Column(db.String(100))
    version = db.Column(db.String(50))
    observations = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'audit_id': self.audit_id,
            'asset_type': self.asset_type,
            'brand': self.brand,
            'model': self.model,
            'operating_system': self.operating_system,
            'version': self.version,
            'observations': self.observations,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
