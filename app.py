# app.py

import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, g, make_response, send_file, abort
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from database import db, configure_database
from models import User, Company, Audit, ChecklistResponse, Finding, Asset, Evidence
from auth import encode_token, decode_token, login_required, role_required
from checklist_questions import CHECKLIST_QUESTIONS, get_question_by_key
from services.risk_engine import calculate_audit_risk, calculate_finding_risk
from services.ai_service import generate_audit_ai_insights
from services.pdf_generator import build_pdf_report

app = Flask(__name__)

# Configuración de la App
secret_key = os.getenv('SECRET_KEY') or os.getenv('JWT_SECRET')
if not secret_key:
    if os.getenv('FLASK_ENV') == 'production':
        raise RuntimeError('SECRET_KEY or JWT_SECRET must be configured in production')
    secret_key = 'dev-only-change-me'
app.config['SECRET_KEY'] = secret_key
configure_database(app)

# Carpeta de subida de evidencias
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Máximo 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'docx'}

# Detrás de Nginx: respetar IP real del cliente para rate limiting
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Rate limiting (en memoria; suficiente para una instancia)
# Debe inicializarse antes que CSRF para que cuente requests aunque fallen el token
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri='memory://'
)

# Protección CSRF (formularios y AJAX vía header X-CSRFToken)
app.config['WTF_CSRF_TIME_LIMIT'] = None  # válido mientras dure la sesión
csrf = CSRFProtect(app)

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    if request.accept_mimetypes.best == 'application/json' or request.is_json:
        return jsonify({'status': 'error', 'message': 'Sesión inválida o expirada. Recargue la página.'}), 400
    flash('La sesión expiró o el formulario es inválido. Intente nuevamente.', 'error')
    return redirect(request.referrer or url_for('login'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def current_user_can_access_audit(audit):
    if not g.current_user:
        return False
    if g.current_user.role == 'superadmin':
        return True
    return audit.auditor_id == g.current_user.id

def get_authorized_audit_or_404(audit_id):
    audit = Audit.query.get_or_404(audit_id)
    if not current_user_can_access_audit(audit):
        abort(403)
    return audit

# Hook para inyectar el usuario logueado en las plantillas
@app.before_request
def load_logged_in_user():
    if request.path.startswith('/static/uploads/') or request.path.startswith('/static/reports/'):
        abort(404)

    token = request.cookies.get('token')
    g.current_user = None
    if token:
        payload = decode_token(token)
        if not isinstance(payload, str):
            g.current_user = User.query.get(payload['sub'])

# ----------------- RUTAS DE AUTENTICACION -----------------

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute; 30 per hour', methods=['POST'])
def login():
    if g.current_user:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            # Probar también por email
            user = User.query.filter_by(email=username).first()
            if not user or not user.check_password(password):
                flash('Credenciales incorrectas.', 'error')
                return render_template('login.html')
                
        token = encode_token(user.id, user.role)
        if not token:
            flash('Error al generar sesión.', 'error')
            return render_template('login.html')
            
        resp = make_response(redirect(url_for('dashboard')))
        resp.set_cookie(
            'token',
            token,
            httponly=True,
            secure=os.getenv('FLASK_ENV') == 'production',
            samesite='Strict',
            max_age=86400
        ) # 24 horas
        flash(f'¡Bienvenido de nuevo, {user.username}!', 'success')
        return resp
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    resp = make_response(redirect(url_for('login')))
    resp.delete_cookie('token')
    flash('Sesión cerrada correctamente.', 'success')
    return resp

# ----------------- DASHBOARD GLOBAL (Módulo 9) -----------------

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    from sqlalchemy import func

    # RBAC: superadmin ve métricas globales, auditor solo de sus auditorías
    is_superadmin = g.current_user.role == 'superadmin'
    audit_filter = [] if is_superadmin else [Audit.auditor_id == g.current_user.id]

    total_audits = Audit.query.filter(*audit_filter).count()
    if is_superadmin:
        total_companies = Company.query.count()
    else:
        total_companies = db.session.query(func.count(func.distinct(Audit.company_id)))\
            .filter(*audit_filter).scalar() or 0
    
    # Inicializar estadísticas
    no_mfa_pct = 0.0
    no_backups_pct = 0.0
    insecure_remote_pct = 0.0
    industry_stats = {}
    size_stats = {}
    top_findings = []
    
    if total_audits > 0:
        def count_no_responses(question_key):
            q = ChecklistResponse.query.join(Audit).filter(
                ChecklistResponse.question_key == question_key,
                ChecklistResponse.response == 'NO',
                *audit_filter
            )
            return q.count()

        # Pct sin MFA (Key: mfa_users)
        no_mfa_pct = round((count_no_responses('mfa_users') / total_audits) * 100, 1)
        
        # Pct sin Backups (Key: backup_frequency)
        no_backups_pct = round((count_no_responses('backup_frequency') / total_audits) * 100, 1)
        
        # Pct Acceso Remoto Inseguro (RDP expuesto) (Key: remote_rdp)
        insecure_remote_pct = round((count_no_responses('remote_rdp') / total_audits) * 100, 1)
        
        # Promedio de riesgo por industria
        industry_scores = db.session.query(
            Company.industry, 
            func.avg(Audit.risk_score)
        ).join(Audit).filter(*audit_filter).group_by(Company.industry).all()
        industry_stats = {ind: round(score, 1) for ind, score in industry_scores if ind}
        
        # Promedio de riesgo por tamaño (revenue range)
        size_scores = db.session.query(
            Company.annual_revenue_range,
            func.avg(Audit.risk_score)
        ).join(Audit).filter(*audit_filter).group_by(Company.annual_revenue_range).all()
        size_stats = {sz: round(score, 1) for sz, score in size_scores if sz}
        
        # Top 10 Hallazgos Frecuentes
        top_f_query = db.session.query(
            Finding.title,
            Finding.category,
            func.count(Finding.id)
        ).join(Audit, Finding.audit_id == Audit.id).filter(*audit_filter)\
            .group_by(Finding.title, Finding.category)\
            .order_by(func.count(Finding.id).desc()).limit(10).all()
        top_findings = [{'title': title, 'category': cat, 'count': count} for title, cat, count in top_f_query]
        
    recent_audits = Audit.query.filter(*audit_filter).order_by(Audit.created_at.desc()).limit(5).all()
    
    return render_template(
        'dashboard.html',
        total_audits=total_audits,
        total_companies=total_companies,
        no_mfa_pct=no_mfa_pct,
        no_backups_pct=no_backups_pct,
        insecure_remote_pct=insecure_remote_pct,
        industry_stats=industry_stats,
        size_stats=size_stats,
        top_findings=top_findings,
        recent_audits=recent_audits
    )

# ----------------- GESTION DE CLIENTES (Módulo 1) -----------------

@app.route('/companies')
@login_required
def list_companies():
    companies = Company.query.order_by(Company.company_name).all()
    return render_template('companies/list.html', companies=companies)

@app.route('/companies/create', methods=['GET', 'POST'])
@login_required
def create_company():
    if request.method == 'POST':
        name = request.form.get('company_name')
        tax_id = request.form.get('tax_id')
        address = request.form.get('address')
        city = request.form.get('city')
        province = request.form.get('province')
        country = request.form.get('country', 'Argentina')
        industry = request.form.get('industry')
        employee_count = request.form.get('employee_count')
        revenue = request.form.get('annual_revenue_range')
        
        # Validar duplicados de tax_id (CUIT)
        existing = Company.query.filter_by(tax_id=tax_id).first()
        if existing:
            flash(f'Ya existe un cliente registrado con el CUIT/ID {tax_id}.', 'error')
            return render_template('companies/create.html')
            
        company = Company(
            company_name=name,
            tax_id=tax_id,
            address=address,
            city=city,
            province=province,
            country=country,
            industry=industry,
            employee_count=int(employee_count) if employee_count else 0,
            annual_revenue_range=revenue
        )
        db.session.add(company)
        db.session.commit()
        
        flash('Cliente registrado con éxito.', 'success')
        return redirect(url_for('list_companies'))
        
    return render_template('companies/create.html')

@app.route('/companies/<int:company_id>')
@login_required
def detail_company(company_id):
    company = Company.query.get_or_404(company_id)
    audits_query = Audit.query.filter_by(company_id=company_id)
    if g.current_user.role != 'superadmin':
        audits_query = audits_query.filter_by(auditor_id=g.current_user.id)
    audits = audits_query.order_by(Audit.audit_date.desc()).all()
    return render_template('companies/detail.html', company=company, audits=audits)

@app.route('/companies/<int:company_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_company(company_id):
    company = Company.query.get_or_404(company_id)
    if request.method == 'POST':
        company.company_name = request.form.get('company_name')
        company.tax_id = request.form.get('tax_id')
        company.address = request.form.get('address')
        company.city = request.form.get('city')
        company.province = request.form.get('province')
        company.country = request.form.get('country')
        company.industry = request.form.get('industry')
        
        employee_count = request.form.get('employee_count')
        company.employee_count = int(employee_count) if employee_count else 0
        company.annual_revenue_range = request.form.get('annual_revenue_range')
        
        db.session.commit()
        flash('Datos del cliente actualizados.', 'success')
        return redirect(url_for('detail_company', company_id=company.id))
        
    return render_template('companies/edit.html', company=company)

# ----------------- GESTION DE AUDITORIAS (Módulos 2-8) -----------------

@app.route('/audits')
@login_required
def list_audits():
    query = Audit.query
    if g.current_user.role != 'superadmin':
        query = query.filter_by(auditor_id=g.current_user.id)
    audits = query.order_by(Audit.audit_date.desc()).all()
    return render_template('audits/list.html', audits=audits)

@app.route('/audits/create', methods=['GET', 'POST'])
@login_required
def create_audit():
    companies = Company.query.order_by(Company.company_name).all()
    if request.method == 'POST':
        company_id = request.form.get('company_id')
        
        audit = Audit(
            company_id=company_id,
            auditor_id=g.current_user.id,
            status='draft',
            risk_score=0.0,
            risk_level='Low'
        )
        db.session.add(audit)
        db.session.commit()
        
        # Inicializar respuestas del checklist vacías en base de datos
        for cat in CHECKLIST_QUESTIONS:
            for q in cat['questions']:
                resp = ChecklistResponse(
                    audit_id=audit.id,
                    category=cat['category'],
                    question_key=q['key'],
                    response='NA',
                    observations=''
                )
                db.session.add(resp)
        db.session.commit()
        
        flash('Nueva auditoría inicializada con éxito.', 'success')
        return redirect(url_for('audit_workspace', audit_id=audit.id))
        
    # Si viene con un company_id por GET, lo pre-seleccionamos
    pre_company_id = request.args.get('company_id', type=int)
    return render_template('audits/create.html', companies=companies, pre_company_id=pre_company_id)

@app.route('/audits/<int:audit_id>/workspace')
@login_required
def audit_workspace(audit_id):
    audit = get_authorized_audit_or_404(audit_id)
    company = audit.company
    
    # Agrupar las respuestas del checklist cargadas en BD
    responses = ChecklistResponse.query.filter_by(audit_id=audit_id).all()
    responses_dict = {r.question_key: r for r in responses}
    
    # Preparar checklist estructurado para renderizar
    checklist_data = []
    for cat in CHECKLIST_QUESTIONS:
        cat_data = {
            'category': cat['category'],
            'questions': []
        }
        for q in cat['questions']:
            db_resp = responses_dict.get(q['key'])
            cat_data['questions'].append({
                'key': q['key'],
                'text': q['text'],
                'description': q['description'],
                'response': db_resp.response if db_resp else 'NA',
                'observations': db_resp.observations if db_resp else ''
            })
        checklist_data.append(cat_data)
        
    assets = Asset.query.filter_by(audit_id=audit_id).all()
    findings = Finding.query.filter_by(audit_id=audit_id).all()
    evidences = Evidence.query.filter_by(audit_id=audit_id).all()
    
    return render_template(
        'audits/workspace.html',
        audit=audit,
        company=company,
        checklist=checklist_data,
        assets=assets,
        findings=findings,
        evidences=evidences
    )

# Actualizar Estado (Módulo 2)
@app.route('/audits/<int:audit_id>/status', methods=['POST'])
@login_required
def update_audit_status(audit_id):
    audit = get_authorized_audit_or_404(audit_id)
    status = request.form.get('status')
    if status in ['draft', 'in_progress', 'completed', 'delivered']:
        audit.status = status
        db.session.commit()
        return jsonify({'status': 'success', 'message': f'Estado actualizado a {status}'})
    return jsonify({'status': 'error', 'message': 'Estado inválido'}), 400

# Guardar Checklist por AJAX (Módulo 3 - Autoguardado)
@app.route('/audits/<int:audit_id>/checklist/save', methods=['POST'])
@login_required
def save_checklist(audit_id):
    audit = get_authorized_audit_or_404(audit_id)
    data = request.json
    
    if not data:
        return jsonify({'status': 'error', 'message': 'No se enviaron datos'}), 400
        
    for item in data.get('responses', []):
        key = item.get('key')
        response_val = item.get('response')
        obs = item.get('observations', '')
        
        db_resp = ChecklistResponse.query.filter_by(audit_id=audit_id, question_key=key).first()
        if db_resp:
            db_resp.response = response_val
            db_resp.observations = obs
            
    db.session.commit()
    
    # Recalcular riesgo de la auditoría tras cambio en checklist
    score, level = calculate_audit_risk(audit_id)
    
    return jsonify({
        'status': 'success', 
        'risk_score': score, 
        'risk_level': level
    })

# CRUD Inventario por AJAX (Módulo 4)
@app.route('/audits/<int:audit_id>/assets', methods=['GET', 'POST'])
@login_required
def audit_assets(audit_id):
    get_authorized_audit_or_404(audit_id)
    if request.method == 'POST':
        # Agregar activo
        asset_type = request.form.get('asset_type')
        brand = request.form.get('brand')
        model = request.form.get('model')
        os_name = request.form.get('operating_system')
        version = request.form.get('version')
        observations = request.form.get('observations')
        
        asset = Asset(
            audit_id=audit_id,
            asset_type=asset_type,
            brand=brand,
            model=model,
            operating_system=os_name,
            version=version,
            observations=observations
        )
        db.session.add(asset)
        db.session.commit()
        
        flash('Activo registrado en el inventario.', 'success')
        return redirect(url_for('audit_workspace', audit_id=audit_id) + '#inventario')
        
    assets = Asset.query.filter_by(audit_id=audit_id).all()
    return jsonify([a.to_dict() for a in assets])

@app.route('/audits/<int:audit_id>/assets/<int:asset_id>/delete', methods=['POST'])
@login_required
def delete_asset(audit_id, asset_id):
    get_authorized_audit_or_404(audit_id)
    asset = Asset.query.filter_by(audit_id=audit_id, id=asset_id).first_or_404()
    db.session.delete(asset)
    db.session.commit()
    flash('Activo removido del inventario.', 'success')
    return redirect(url_for('audit_workspace', audit_id=audit_id) + '#inventario')

# CRUD Hallazgos por AJAX (Módulo 5, 6)
@app.route('/audits/<int:audit_id>/findings', methods=['GET', 'POST'])
@login_required
def audit_findings(audit_id):
    get_authorized_audit_or_404(audit_id)
    if request.method == 'POST':
        category = request.form.get('category')
        title = request.form.get('title')
        description = request.form.get('description')
        impact = request.form.get('impact')
        probability = request.form.get('probability')
        recommendation = request.form.get('recommendation')
        
        # Calcular riesgo individual
        score, risk_lvl = calculate_finding_risk(impact, probability)
        
        finding = Finding(
            audit_id=audit_id,
            category=category,
            title=title,
            description=description,
            impact=impact,
            probability=probability,
            risk_level=risk_lvl,
            recommendation=recommendation,
            status='open'
        )
        db.session.add(finding)
        db.session.commit()
        
        # Recalcular riesgo de la auditoría global
        calculate_audit_risk(audit_id)
        
        flash('Hallazgo registrado con éxito.', 'success')
        return redirect(url_for('audit_workspace', audit_id=audit_id) + '#hallazgos')
        
    findings = Finding.query.filter_by(audit_id=audit_id).all()
    return jsonify([f.to_dict() for f in findings])

@app.route('/audits/<int:audit_id>/findings/<int:finding_id>/delete', methods=['POST'])
@login_required
def delete_finding(audit_id, finding_id):
    get_authorized_audit_or_404(audit_id)
    finding = Finding.query.filter_by(audit_id=audit_id, id=finding_id).first_or_404()
    db.session.delete(finding)
    db.session.commit()
    
    # Recalcular riesgo de la auditoría global
    calculate_audit_risk(audit_id)
    
    flash('Hallazgo eliminado.', 'success')
    return redirect(url_for('audit_workspace', audit_id=audit_id) + '#hallazgos')

# Evidencias (Módulo 7)
@app.route('/audits/<int:audit_id>/evidence/upload', methods=['POST'])
@login_required
def upload_evidence(audit_id):
    get_authorized_audit_or_404(audit_id)
    if 'file' not in request.files:
        flash('No se seleccionó archivo.', 'error')
        return redirect(url_for('audit_workspace', audit_id=audit_id) + '#evidencias')
        
    file = request.files['file']
    finding_id = request.form.get('finding_id')
    
    if file.filename == '':
        flash('No se seleccionó archivo.', 'error')
        return redirect(url_for('audit_workspace', audit_id=audit_id) + '#evidencias')
        
    if file and allowed_file(file.filename):
        # Asegurar nombre de archivo limpio y único
        ext = file.filename.rsplit('.', 1)[1].lower()
        import uuid
        unique_name = f"evidence_{audit_id}_{uuid.uuid4().hex[:10]}.{ext}"
        safe_file_name = secure_filename(file.filename) or unique_name
        linked_finding_id = None
        if finding_id:
            finding = Finding.query.filter_by(audit_id=audit_id, id=finding_id).first()
            if not finding:
                flash('El hallazgo seleccionado no pertenece a esta auditoría.', 'error')
                return redirect(url_for('audit_workspace', audit_id=audit_id) + '#evidencias')
            linked_finding_id = finding.id

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(filepath)
        
        # Registrar en BD
        evidence = Evidence(
            audit_id=audit_id,
            finding_id=linked_finding_id,
            file_name=safe_file_name,
            file_type=ext,
            file_path=filepath
        )
        db.session.add(evidence)
        db.session.commit()
        
        flash('Evidencia subida correctamente.', 'success')
    else:
        flash('Extensión de archivo no permitida (solo PNG, JPG, JPEG, PDF, DOCX).', 'error')
        
    return redirect(url_for('audit_workspace', audit_id=audit_id) + '#evidencias')

@app.route('/audits/<int:audit_id>/evidence/<int:evidence_id>')
@login_required
def download_evidence(audit_id, evidence_id):
    get_authorized_audit_or_404(audit_id)
    evidence = Evidence.query.filter_by(audit_id=audit_id, id=evidence_id).first_or_404()
    file_path = os.path.realpath(evidence.file_path)
    upload_root = os.path.realpath(app.config['UPLOAD_FOLDER'])

    if not file_path.startswith(upload_root + os.sep) or not os.path.exists(file_path):
        abort(404)

    return send_file(file_path, as_attachment=False, download_name=evidence.file_name)

# IA (Módulo 10)
@app.route('/audits/<int:audit_id>/ai/generate', methods=['POST'])
@login_required
def generate_ai(audit_id):
    audit = get_authorized_audit_or_404(audit_id)
    
    # Forzar recálculo antes de llamar a IA
    calculate_audit_risk(audit_id)
    
    insights = generate_audit_ai_insights(audit_id)
    if not insights:
        return jsonify({'status': 'error', 'message': 'No se pudieron generar los insights.'}), 500
        
    # Retornar para que el auditor pueda previsualizar y editar
    return jsonify({
        'status': 'success',
        'insights': insights
    })

@app.route('/audits/<int:audit_id>/ai/save', methods=['POST'])
@login_required
def save_ai_insights(audit_id):
    audit = get_authorized_audit_or_404(audit_id)
    data = request.json
    
    if not data:
        return jsonify({'status': 'error', 'message': 'Sin datos'}), 400
        
    audit.executive_summary = data.get('executive_summary')
    audit.recommendations_ai = data.get('recommendations_ai')
    audit.action_plan_30 = data.get('action_plan_30')
    audit.action_plan_60 = data.get('action_plan_60')
    audit.action_plan_90 = data.get('action_plan_90')
    audit.conclusion = data.get('conclusion')
    
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Insights guardados correctamente.'})

# Informe PDF (Módulo 8)
@app.route('/audits/<int:audit_id>/report')
@login_required
def download_report(audit_id):
    get_authorized_audit_or_404(audit_id)
    # Asegurar que el riesgo esté actualizado
    calculate_audit_risk(audit_id)
    
    try:
        pdf_path = build_pdf_report(audit_id)
        if not pdf_path or not os.path.exists(pdf_path):
            flash('Error al generar el PDF.', 'error')
            return redirect(url_for('audit_workspace', audit_id=audit_id) + '#reporte')
            
        return send_file(pdf_path, as_attachment=True, download_name=os.path.basename(pdf_path))
    except Exception as e:
        print(f"Error generando reporte PDF: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error al procesar el reporte: {str(e)}', 'error')
        return redirect(url_for('audit_workspace', audit_id=audit_id) + '#reporte')

# Iniciar servidor
if __name__ == '__main__':
    # Usar puerto alternativo para evitar colisiones
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5005)),
        debug=os.getenv('FLASK_DEBUG') == '1'
    )
