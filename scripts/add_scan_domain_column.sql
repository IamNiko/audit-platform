-- Migración: dominio del escaneo gratuito TheMiniHack (anexo PDF)
ALTER TABLE audits ADD COLUMN IF NOT EXISTS scan_domain VARCHAR(255);
