-- 0002_report_approval_and_findings.sql
-- Agrega el ciclo de vida de aprobación del informe (SOP-008 / TPL-007) y los
-- campos de hallazgo que exigen STD-002 y SOP-006 del TMH Operations Framework.
--
-- La copia firmada del informe NO se almacena en la plataforma: el auditor la firma
-- y la envía por fuera. Acá queda únicamente el registro de quién aprobó y cuándo.
--
-- Idempotente: seguro de correr más de una vez.
--
-- Uso:
--   psql "$DATABASE_URL" -f migrations/0002_report_approval_and_findings.sql
--
-- No se ejecutó contra ninguna base desde este entorno: no había acceso a Postgres
-- disponible. Correr manualmente antes o durante el próximo deploy.

-- Aprobación del informe
ALTER TABLE audits ADD COLUMN IF NOT EXISTS report_status VARCHAR(20) NOT NULL DEFAULT 'draft';
ALTER TABLE audits ADD COLUMN IF NOT EXISTS report_version VARCHAR(10) NOT NULL DEFAULT '1.0';
ALTER TABLE audits ADD COLUMN IF NOT EXISTS approved_by_id INTEGER REFERENCES users (id);
ALTER TABLE audits ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS ix_audits_approved_by_id ON audits (approved_by_id);

-- Campos de hallazgo (STD-002 §Formato, SOP-006 §3)
ALTER TABLE findings ADD COLUMN IF NOT EXISTS affected_asset VARCHAR(255);
ALTER TABLE findings ADD COLUMN IF NOT EXISTS remediation_effort VARCHAR(20) DEFAULT 'Medium';
-- 'references' es palabra reservada en SQL: la columna se llama standard_references.
ALTER TABLE findings ADD COLUMN IF NOT EXISTS standard_references TEXT;
