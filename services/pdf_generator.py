# services/pdf_generator.py

import os
from datetime import datetime, timezone
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import render_template
from werkzeug.utils import secure_filename
from weasyprint import HTML
from models import Audit, Finding, ChecklistResponse, Asset, Evidence
from checklist_questions import CHECKLIST_QUESTIONS, get_question_by_key
from services.risk_engine import REMEDIATION_SLA

RISK_LABELS = {
    'Informational': 'Informativo',
    'Low': 'Bajo',
    'Medium': 'Medio',
    'High': 'Alto',
    'Critical': 'Crítico',
}

STATUS_LABELS = {
    'draft': 'Borrador',
    'in_progress': 'En progreso',
    'completed': 'Completada',
    'delivered': 'Entregada',
}


def _compute_compliance_stats(responses):
    yes_count = sum(1 for r in responses if r.response == 'YES')
    no_count = sum(1 for r in responses if r.response == 'NO')
    na_count = sum(1 for r in responses if r.response == 'NA')
    total_relevant = yes_count + no_count
    compliance_pct = round((yes_count / total_relevant) * 100, 1) if total_relevant else 0.0
    return {
        'yes_count': yes_count,
        'no_count': no_count,
        'na_count': na_count,
        'compliance_pct': compliance_pct,
    }


def _build_failed_controls(responses):
    failed = []
    for r in responses:
        if r.response != 'NO':
            continue
        q = get_question_by_key(r.question_key)
        if not q:
            continue
        failed.append({
            'category': r.category,
            'question': q['text'],
            'observations': r.observations or '',
        })
    return failed


def _build_category_scores(responses):
    scores = {}
    for cat in CHECKLIST_QUESTIONS:
        category = cat['category']
        cat_responses = [r for r in responses if r.category == category]
        yes_count = sum(1 for r in cat_responses if r.response == 'YES')
        no_count = sum(1 for r in cat_responses if r.response == 'NO')
        total = yes_count + no_count
        if total > 0:
            compliance = (yes_count / total) * 100
            scores[category] = round(100.0 - compliance, 1)
        else:
            scores[category] = 0.0
    return scores


def generate_risk_chart(audit_id, category_scores, output_dir):
    sorted_data = sorted(category_scores.items(), key=lambda x: x[1])
    cats = [x[0] for x in sorted_data]
    scores = [x[1] for x in sorted_data]

    colors = []
    for s in scores:
        if s <= 25:
            colors.append('#10b981')
        elif s <= 50:
            colors.append('#f59e0b')
        elif s <= 75:
            colors.append('#f97316')
        else:
            colors.append('#ef4444')

    plt.figure(figsize=(8, 5))
    plt.gcf().patch.set_facecolor('#ffffff')
    ax = plt.gca()
    ax.set_facecolor('#f8fafc')

    ax.barh(cats, scores, color=colors, height=0.6, edgecolor='#e2e8f0')
    ax.tick_params(colors='#334155', labelsize=9)
    ax.set_xlabel('Nivel de riesgo (%)', color='#64748b', fontsize=10, labelpad=10)
    ax.set_xlim(0, 100)
    ax.grid(axis='x', linestyle='--', color='#e2e8f0', alpha=0.9)

    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_color('#e2e8f0')

    plt.title('Riesgo por categoría de seguridad', color='#0f172a', fontsize=12, pad=15, weight='bold')
    plt.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    chart_path = os.path.join(output_dir, f"risk_chart_{audit_id}.png")
    plt.savefig(chart_path, facecolor='#ffffff', dpi=150)
    plt.close()
    return chart_path


def build_report_context(audit_id):
    audit = Audit.query.get(audit_id)
    if not audit:
        return None

    company = audit.company
    findings = Finding.query.filter_by(audit_id=audit_id).all()
    checklist_responses = ChecklistResponse.query.filter_by(audit_id=audit_id).all()
    assets = Asset.query.filter_by(audit_id=audit_id).all()
    evidences = Evidence.query.filter_by(audit_id=audit_id).all()

    compliance = _compute_compliance_stats(checklist_responses)
    failed_controls = _build_failed_controls(checklist_responses)
    category_scores = _build_category_scores(checklist_responses)

    critical_findings = [f for f in findings if f.risk_level == 'Critical']
    important_findings = [f for f in findings if f.risk_level in ['High', 'Medium']]
    low_findings = [f for f in findings if f.risk_level == 'Low']
    informational_findings = [f for f in findings if f.risk_level == 'Informational']

    finding_counts = {
        'total': len(findings),
        'critical': len(critical_findings),
        'high': sum(1 for f in findings if f.risk_level == 'High'),
        'medium': sum(1 for f in findings if f.risk_level == 'Medium'),
        'low': len(low_findings),
        'informational': len(informational_findings),
    }

    return {
        'audit': audit,
        'company': company,
        'compliance': compliance,
        'failed_controls': failed_controls,
        'category_scores': category_scores,
        'critical_findings': critical_findings,
        'important_findings': important_findings,
        'low_findings': low_findings,
        'informational_findings': informational_findings,
        'finding_counts': finding_counts,
        'assets': assets,
        'evidences': evidences,
        'risk_label': RISK_LABELS.get(audit.risk_level, audit.risk_level),
        'status_label': STATUS_LABELS.get(audit.status, audit.status),
        'risk_labels': RISK_LABELS,
        'remediation_sla': REMEDIATION_SLA,
        # Mientras el informe no esté aprobado, el PDF sale marcado como borrador.
        'is_draft': audit.report_status != 'approved',
        'approved_by': audit.approved_by,
        'approved_at': audit.approved_at,
        'report_version': audit.report_version,
    }


def build_pdf_report(audit_id):
    ctx = build_report_context(audit_id)
    if not ctx:
        return None

    audit = ctx['audit']
    company = ctx['company']

    reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../static/reports'))
    uploads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../static/uploads'))
    os.makedirs(reports_dir, exist_ok=True)

    chart_path = generate_risk_chart(audit_id, ctx['category_scores'], uploads_dir)
    chart_uri = 'file://' + chart_path

    evidences_for_pdf = []
    for ev in ctx['evidences']:
        abs_ev_path = os.path.abspath(ev.file_path)
        ev_uri = 'file://' + abs_ev_path if os.path.exists(abs_ev_path) else ev.file_path
        evidences_for_pdf.append({
            'file_name': ev.file_name,
            'file_type': ev.file_type,
            'uri': ev_uri,
        })

    report_ctx = {k: v for k, v in ctx.items() if k != 'evidences'}
    report_ctx['evidences'] = evidences_for_pdf
    report_ctx['chart_uri'] = chart_uri

    rendered_html = render_template('reports/report_template.html', **report_ctx)

    # Nomenclatura STD-003: <Cliente>_Informe_<Tipo>_v<version>_<YYYY-MM-DD>.pdf
    # El borrador lleva sufijo para que no se confunda con el entregable final.
    safe_company_name = secure_filename(company.company_name) or f"company_{company.id}"
    report_date = (audit.audit_date or audit.created_at or datetime.now(timezone.utc)).strftime('%Y-%m-%d')
    draft_suffix = '_BORRADOR' if ctx['is_draft'] else ''
    pdf_filename = (
        f"{safe_company_name}_Informe_Auditoria"
        f"_v{audit.report_version}_{report_date}{draft_suffix}.pdf"
    )
    pdf_path = os.path.join(reports_dir, pdf_filename)

    HTML(string=rendered_html).write_pdf(pdf_path)
    return pdf_path
