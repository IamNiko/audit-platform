# services/pdf_generator.py

import os
import matplotlib
matplotlib.use('Agg')  # Configuración headless obligatoria para servidores
import matplotlib.pyplot as plt
from flask import render_template
from weasyprint import HTML
from models import Audit, Company, Finding, ChecklistResponse, Asset, Evidence
from database import db
from checklist_questions import CHECKLIST_QUESTIONS, get_question_by_key

def generate_risk_chart(audit_id, output_dir):
    """
    Genera un gráfico de barras horizontales con el nivel de riesgo por categoría
    y lo guarda como una imagen temporal.
    """
    responses = ChecklistResponse.query.filter_by(audit_id=audit_id).all()
    
    # Calcular cumplimiento y riesgo (100 - cumplimiento) por categoría
    categories = [cat["category"] for cat in CHECKLIST_QUESTIONS]
    category_scores = {}
    
    for cat in categories:
        cat_responses = [r for r in responses if r.category == cat]
        yes_count = sum(1 for r in cat_responses if r.response == 'YES')
        no_count = sum(1 for r in cat_responses if r.response == 'NO')
        total = yes_count + no_count
        
        if total > 0:
            compliance = (yes_count / total) * 100
            risk_score = 100.0 - compliance
        else:
            risk_score = 0.0  # Sin preguntas respondidas = 0 riesgo por defecto
            
        category_scores[cat] = risk_score
        
    # Filtrar solo categorías que tengan datos o mostrar todas
    # Vamos a mostrar todas las categorías de forma ordenada
    sorted_data = sorted(category_scores.items(), key=lambda x: x[1])
    cats = [x[0] for x in sorted_data]
    scores = [x[1] for x in sorted_data]
    
    # Colores según el nivel de riesgo
    colors = []
    for s in scores:
        if s <= 25:
            colors.append('#10b981')  # Verde (Bajo)
        elif s <= 50:
            colors.append('#f59e0b')  # Amarillo (Medio)
        elif s <= 75:
            colors.append('#f97316')  # Naranja (Alto)
        else:
            colors.append('#ef4444')  # Rojo (Crítico)
            
    # Dibujar gráfico
    plt.figure(figsize=(8, 5))
    # Fondo oscuro a juego con la marca
    plt.gcf().patch.set_facecolor('#0b0f19')
    ax = plt.gca()
    ax.set_facecolor('#151f32')
    
    bars = ax.barh(cats, scores, color=colors, height=0.6, edgecolor='#24354f')
    
    # Estilos de textos y grillas
    ax.tick_params(colors='#f3f4f6', labelsize=9)
    ax.set_xlabel('Nivel de Riesgo (%)', color='#9ca3af', fontsize=10, labelpad=10)
    ax.set_xlim(0, 100)
    ax.grid(axis='x', linestyle='--', color='#24354f', alpha=0.7)
    
    # Quitar bordes innecesarios
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_color('#24354f')
        
    plt.title('Riesgo por Categoría de Seguridad', color='#f3f4f6', fontsize=12, pad=15, weight='bold')
    plt.tight_layout()
    
    # Guardar
    os.makedirs(output_dir, exist_ok=True)
    chart_filename = f"risk_chart_{audit_id}.png"
    chart_path = os.path.join(output_dir, chart_filename)
    plt.savefig(chart_path, facecolor='#0b0f19', dpi=150)
    plt.close()
    
    return chart_path

def build_pdf_report(audit_id):
    """
    Compila el informe completo en PDF utilizando WeasyPrint.
    Retorna la ruta absoluta del archivo generado.
    """
    audit = Audit.query.get(audit_id)
    if not audit:
        return None
        
    company = audit.company
    findings = Finding.query.filter_by(audit_id=audit_id).all()
    checklist_responses = ChecklistResponse.query.filter_by(audit_id=audit_id).all()
    assets = Asset.query.filter_by(audit_id=audit_id).all()
    evidences = Evidence.query.filter_by(audit_id=audit_id).all()
    
    # Crear carpeta de reportes e imágenes temporales
    reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../static/reports'))
    uploads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../static/uploads'))
    os.makedirs(reports_dir, exist_ok=True)
    
    # Generar gráfico de riesgo
    chart_path = generate_risk_chart(audit_id, uploads_dir)
    
    # Agrupar hallazgos por severidad
    critical_findings = [f for f in findings if f.risk_level == 'Critical']
    important_findings = [f for f in findings if f.risk_level in ['High', 'Medium']]
    low_findings = [f for f in findings if f.risk_level == 'Low']
    
    # Mapear respuestas de checklist con preguntas correspondientes
    checklist_mapped = []
    for r in checklist_responses:
        q = get_question_by_key(r.question_key)
        if q:
            checklist_mapped.append({
                'category': r.category,
                'question': q['text'],
                'response': r.response,
                'observations': r.observations
            })
            
    # Renderizar el HTML del reporte
    # Pasamos las rutas locales de los archivos como absolutas ('file://...') para que WeasyPrint las lea
    chart_uri = 'file://' + chart_path
    
    # Si las evidencias son locales, pasamos sus rutas absolutas también
    evidences_list = []
    for ev in evidences:
        abs_ev_path = os.path.abspath(ev.file_path)
        ev_uri = 'file://' + abs_ev_path if os.path.exists(abs_ev_path) else ev.file_path
        evidences_list.append({
            'file_name': ev.file_name,
            'file_type': ev.file_type,
            'uri': ev_uri
        })
        
    rendered_html = render_template(
        'reports/report_template.html',
        audit=audit,
        company=company,
        critical_findings=critical_findings,
        important_findings=important_findings,
        low_findings=low_findings,
        checklist_responses=checklist_mapped,
        assets=assets,
        evidences=evidences_list,
        chart_uri=chart_uri
    )
    
    pdf_filename = f"Reporte_Auditoria_{company.company_name.replace(' ', '_')}_{audit.id}.pdf"
    pdf_path = os.path.join(reports_dir, pdf_filename)
    
    # Compilar a PDF con WeasyPrint
    HTML(string=rendered_html).write_pdf(pdf_path)
    
    return pdf_path
