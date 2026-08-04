# services/risk_engine.py

from models import Finding, ChecklistResponse, Audit
from database import db

IMPACT_VALUES = {'Low': 1, 'Medium': 2, 'High': 3, 'Critical': 4}
PROBABILITY_VALUES = {'Low': 1, 'Medium': 2, 'High': 3}

# Plazos sugeridos de remediación por severidad (STD-002).
REMEDIATION_SLA = {
    'Critical': 'Inmediato (≤ 24 h)',
    'High': '≤ 7 días',
    'Medium': '≤ 30 días',
    'Low': '≤ 90 días',
    'Informational': 'A discreción',
}

def calculate_finding_risk(impact, probability):
    """
    Calcula el nivel de riesgo de un hallazgo basado en la matriz de impacto y probabilidad.
    Retorna (score, risk_level)
    """
    # 'Informativa' (STD-002) es una observación sin riesgo inmediato: no entra en la
    # matriz de impacto x probabilidad ni suma al score global de la auditoría.
    if impact == 'Informational':
        return 0, 'Informational'

    imp_val = IMPACT_VALUES.get(impact, 2)
    prob_val = PROBABILITY_VALUES.get(probability, 2)
    score = imp_val * prob_val

    # Rango de score de 1 a 12
    if score <= 2:
        return score, 'Low'
    elif score <= 4:
        return score, 'Medium'
    elif score <= 8:
        return score, 'High'
    else:
        return score, 'Critical'

def calculate_audit_risk(audit_id):
    """
    Calcula el riesgo global de una auditoría combinando el cumplimiento del checklist (40%)
    y la severidad del peor hallazgo registrado (60%).
    Actualiza la auditoría en base de datos.
    """
    audit = Audit.query.get(audit_id)
    if not audit:
        return 0.0, 'Low'
        
    # 1. Calcular cumplimiento de checklist
    responses = ChecklistResponse.query.filter_by(audit_id=audit_id).all()
    yes_count = sum(1 for r in responses if r.response == 'YES')
    no_count = sum(1 for r in responses if r.response == 'NO')
    
    total_relevant = yes_count + no_count
    if total_relevant > 0:
        compliance_rate = (yes_count / total_relevant) * 100
    else:
        compliance_rate = 100.0  # 100% cumplimiento si no hay respuestas
        
    checklist_risk_weight = 100.0 - compliance_rate  # A menor cumplimiento, mayor riesgo
    
    # 2. Calcular severidad de hallazgos
    findings = Finding.query.filter_by(audit_id=audit_id).all()
    max_finding_score = 0
    
    for f in findings:
        score, _ = calculate_finding_risk(f.impact, f.probability)
        if score > max_finding_score:
            max_finding_score = score
            
    # Escalar max_finding_score (0 a 12) a escala 0-100
    finding_risk_weight = (max_finding_score / 12) * 100
    
    # 3. Combinar scores
    global_score = (checklist_risk_weight * 0.4) + (finding_risk_weight * 0.6)
    global_score = round(global_score, 1)
    
    # Determinar nivel global
    if global_score <= 25:
        global_level = 'Low'
    elif global_score <= 50:
        global_level = 'Medium'
    elif global_score <= 75:
        global_level = 'High'
    else:
        global_level = 'Critical'
        
    # Actualizar auditoría
    audit.risk_score = global_score
    audit.risk_level = global_level
    db.session.commit()
    
    return global_score, global_level
