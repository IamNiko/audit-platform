-- 0001_add_indexes.sql
-- Agrega índices en columnas FK / de búsqueda frecuente que quedaron sin indexar.
-- Idempotente: seguro de correr más de una vez, y no bloquea escrituras
-- significativamente en tablas de este tamaño (usar CONCURRENTLY si en el futuro
-- estas tablas crecen mucho y esto corre contra una base con tráfico en vivo).
--
-- Uso:
--   psql "$DATABASE_URL" -f migrations/0001_add_indexes.sql
--
-- No se ejecutó contra ninguna base desde este entorno: no había acceso a
-- Postgres disponible. Correr manualmente antes o durante el próximo deploy.

CREATE INDEX IF NOT EXISTS ix_audits_company_id ON audits (company_id);
CREATE INDEX IF NOT EXISTS ix_audits_auditor_id ON audits (auditor_id);

CREATE INDEX IF NOT EXISTS ix_checklist_responses_audit_id ON checklist_responses (audit_id);
CREATE INDEX IF NOT EXISTS ix_checklist_responses_question_key ON checklist_responses (question_key);

CREATE INDEX IF NOT EXISTS ix_findings_audit_id ON findings (audit_id);

CREATE INDEX IF NOT EXISTS ix_evidences_audit_id ON evidences (audit_id);
CREATE INDEX IF NOT EXISTS ix_evidences_finding_id ON evidences (finding_id);

CREATE INDEX IF NOT EXISTS ix_assets_audit_id ON assets (audit_id);
