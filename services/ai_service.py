# services/ai_service.py

import os
import json
from openai import OpenAI
from models import Audit, Company, Finding, ChecklistResponse
from database import db
from checklist_questions import get_question_by_key

def generate_audit_ai_insights(audit_id):
    """
    Genera resúmenes ejecutivos, planes de remediación de 30/60/90 días y conclusiones
    usando OpenAI GPT. Si la API Key no está disponible, cae de manera segura a un
    generador local determinista basado en reglas para asegurar la continuidad operativa.
    """
    audit = Audit.query.get(audit_id)
    if not audit:
        return None
        
    company = audit.company
    findings = Finding.query.filter_by(audit_id=audit_id).all()
    checklist_responses = ChecklistResponse.query.filter_by(audit_id=audit_id).all()
    
    # Recolectar brechas críticas (respuestas 'NO')
    no_responses = [r for r in checklist_responses if r.response == 'NO']
    failed_controls = []
    for r in no_responses:
        q = get_question_by_key(r.question_key)
        if q:
            failed_controls.append(f"{r.category}: {q['text']}")
            
    # Recolectar hallazgos activos
    active_findings = []
    for f in findings:
        active_findings.append(
            f"- [{f.risk_level}] {f.title}: {f.description} (Recomendación: {f.recommendation})"
        )
        
    api_key = os.getenv('OPENAI_API_KEY')
    
    # 1. Si no hay API Key, usamos el Generador de Respaldo Seguro (Local Rule-based engine)
    if not api_key:
        print("OPENAI_API_KEY no configurada. Generando insights de respaldo local...")
        return generate_mock_insights(company, audit, failed_controls, active_findings)
        
    # 2. Conexión con OpenAI
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
        Actúa como un arquitecto senior de ciberseguridad y socio co-fundador de la consultora "The Mini Hack".
        Debes redactar el informe ejecutivo de ciberseguridad para el cliente "{company.company_name}", que pertenece al sector "{company.industry}".
        
        Datos de la Auditoría:
        - Nivel de Riesgo Global: {audit.risk_level} (Score: {audit.risk_score}/100)
        - Cantidad de Empleados: {company.employee_count}
        - Controles de seguridad fallidos (Checklist NO):
        {chr(10).join(['  * ' + c for c in failed_controls]) if failed_controls else '  * Ninguno (Cumple todos los controles base)'}
        
        Hallazgos Específicos Detectados:
        {chr(10).join(active_findings) if active_findings else '  * Ninguno (No se registraron vulnerabilidades adicionales)'}
        
        Genera la siguiente información estructurada de manera extremadamente profesional, pragmática, sin tecnicismos excesivos y orientada a nivel ejecutivo.

        REGLAS DE REDACCIÓN (obligatorias):
        1. Las respuestas del checklist son DECLARACIONES del cliente relevadas en la auditoría
           presencial, no verificaciones técnicas. No afirmes que algo "se comprobó", "se detectó"
           o "se verificó" salvo que aparezca en la lista de hallazgos específicos.
        2. Distinguí hechos de inferencias:
           - Hecho (respaldado por un control fallido o un hallazgo listado): redactalo en afirmativo,
             mencionando de dónde sale ("según lo relevado", "de acuerdo a lo informado por el cliente").
           - Inferencia (riesgo probable que deducís del contexto pero que no está en los datos de
             arriba): redactala SIEMPRE en condicional ("podría", "es probable que",
             "se recomienda verificar"). Nunca la presentes como un hecho.
        3. No inventes datos técnicos que no estén en la información provista: nada de IPs, puertos,
           versiones, nombres de sistemas, CVEs ni cantidades que no aparezcan arriba.
        4. Si no hay información suficiente para una sección, decilo explícitamente en vez de
           rellenar con supuestos.

        Retorna ÚNICAMENTE un objeto JSON válido con las siguientes claves (sin código Markdown, sin bloques ```json, solo texto plano JSON):
        {{
            "executive_summary": "Un resumen ejecutivo del estado actual de ciberseguridad de la empresa, destacando riesgos latentes por su industria y tamaño.",
            "recommendations_ai": "Recomendaciones técnicas y organizativas personalizadas principales.",
            "action_plan_30": "Acciones urgentes a ejecutar en los primeros 30 días (enfocarse en riesgos Críticos/Altos y controles base fallidos).",
            "action_plan_60": "Acciones de mediano plazo para los días 31 a 60 (robustecimiento, backups, políticas).",
            "action_plan_90": "Acciones estratégicas para los días 61 a 90 (capacitaciones, mejora continua).",
            "conclusion": "Una conclusión profesional de cierre sobre la resiliencia y el camino a seguir para la empresa."
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Cost-effective, high performance
            messages=[
                {"role": "system", "content": (
                    "Eres un experto en ciberseguridad que genera informes técnicos estructurados en JSON. "
                    "Escribes solo lo que los datos respaldan: los hechos en afirmativo y todo lo demás en "
                    "condicional, marcado como algo a verificar. Nunca inventas evidencia técnica."
                )},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content.strip()
        # Limpiar posibles bloques markdown que a veces GPT agrega a pesar de las instrucciones
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        data = json.loads(content)
        return data
        
    except Exception as e:
        print(f"Error llamando a OpenAI API: {e}. Usando generador de respaldo...")
        return generate_mock_insights(company, audit, failed_controls, active_findings)

def generate_mock_insights(company, audit, failed_controls, active_findings):
    """
    Genera reportes de respaldo coherentes basados en plantillas para evitar fallos de servicio.
    """
    # Determinar foco según controles fallidos
    focos = []
    if any("MFA" in c or "Contraseñas" in c for c in failed_controls):
        focos.append("la falta de Autenticación Multifactor (MFA) y políticas débiles de acceso")
    if any("Backup" in c or "Servidores" in c for c in failed_controls):
        focos.append("la ausencia de respaldos de seguridad aislados u offline contra ransomware")
    if any("WiFi" in c or "Red" in c or "Firewall" in c for c in failed_controls):
        focos.append("vulnerabilidades de segmentación en redes perimetrales e inalámbricas")
    if any("Capacitación" in c or "Políticas" in c for c in failed_controls):
        focos.append("la necesidad de formalizar políticas y capacitar al factor humano")
        
    foco_text = ", ".join(focos) if focos else "desviaciones menores de controles operativos estándar"
    
    summary = (
        f"Tras la auditoría realizada a {company.company_name} (Sector: {company.industry}), y según la información "
        f"relevada con la organización, se determinó una postura de seguridad con un nivel de riesgo global "
        f"{audit.risk_level.upper()} (Score: {audit.risk_score}/100). "
        f"Las brechas declaradas se concentran principalmente en: {foco_text}. "
        f"Dada la escala de la empresa ({company.employee_count} empleados), sería recomendable mitigar los "
        f"vectores de entrada más comunes para reducir el riesgo de una interrupción de la operación."
    )
    
    recs = (
        "1. Robustecer el perímetro de red deshabilitando accesos directos innecesarios (ej. RDP/SSH expuestos).\n"
        "2. Habilitar y exigir MFA en todas las cuentas de correo electrónico y accesos VPN.\n"
        "3. Implementar un esquema de backup bajo la regla 3-2-1 (con al menos una copia offline/inmutable).\n"
        "4. Reducir privilegios administrativos en las estaciones de trabajo de los usuarios finales."
    )
    
    p30 = (
        "- Deshabilitar puertos expuestos a Internet (RDP 3389) y configurar accesos remotos por VPN segura.\n"
        "- Activar MFA (Autenticación Multifactor) obligatoria en Microsoft 365, Google Workspace y cuentas críticas.\n"
        "- Corregir de inmediato hallazgos catalogados como Críticos o Altos."
    )
    
    p60 = (
        "- Reconfigurar y probar el proceso de copias de seguridad daily, implementando una copia aislada de la red.\n"
        "- Instalar o verificar que el antivirus/EDR corporativo esté desplegado y actualizado en el 100% de los equipos.\n"
        "- Establecer un inventario formal de hardware y revisar cuentas de ex-empleados activas."
    )
    
    p90 = (
        "- Formalizar una política básica de seguridad de la información corporativa.\n"
        "- Realizar un taller de concientización sobre Phishing e Ingeniería Social para todo el personal.\n"
        "- Programar la siguiente auditoría técnica y revisión de reglas de firewall."
    )
    
    conclusion = (
        f"La empresa {company.company_name} cuenta con una infraestructura base sobre la cual se pueden consolidar "
        f"mejoras sustanciales con bajo costo operativo. La adopción de las medidas urgentes detalladas para los próximos "
        f"30 días reducirá significativamente la superficie de ataque expuesta ante amenazas automatizadas y dirigidas."
    )
    
    return {
        "executive_summary": summary,
        "recommendations_ai": recs,
        "action_plan_30": p30,
        "action_plan_60": p60,
        "action_plan_90": p90,
        "conclusion": conclusion
    }
