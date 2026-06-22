# services/minihack_annex.py
"""
Busca el PDF del escaneo gratuito TheMiniHack por dominio y lo anexa al informe de auditoría.
Requiere MINIHACK_DATABASE_URL apuntando a la base de minihack (orders + reports).
"""

import os
import re


def _normalize_domain(value):
    if not value:
        return ''
    domain = str(value).strip().lower()
    domain = re.sub(r'^https?://', '', domain)
    domain = domain.split('/')[0].split(':')[0]
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain


def _get_minihack_connection():
    url = os.getenv('MINIHACK_DATABASE_URL')
    if not url:
        user = os.getenv('MINIHACK_PG_USER') or os.getenv('PG_USER')
        password = os.getenv('MINIHACK_PG_PASSWORD') or os.getenv('PG_PASSWORD')
        host = os.getenv('MINIHACK_PG_HOST', os.getenv('PG_HOST', '127.0.0.1'))
        port = int(os.getenv('MINIHACK_PG_PORT', os.getenv('PG_PORT', '5432')))
        name = os.getenv('MINIHACK_PG_DATABASE', 'minihack')
        if not (user and password and name):
            return None
        return pg8000.connect(user=user, password=password, host=host, port=port, database=name)

    # postgres://user:pass@host:5432/db
    match = re.match(r'^postgres(?:ql)?://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(.+)$', url)
    if not match:
        return None
    user, password, host, port, database = match.groups()
    return pg8000.connect(
        user=user,
        password=password,
        host=host,
        port=int(port or 5432),
        database=database.split('?')[0],
    )


def _resolve_pdf_path(raw_path, minihack_root=None):
    if not raw_path:
        return None
    path = str(raw_path).strip()
    if os.path.isabs(path) and os.path.exists(path):
        return path

    root = minihack_root or os.getenv('MINIHACK_ROOT', '/var/www/theminihack')
    candidates = [
        path,
        os.path.join(root, 'backend', path),
        os.path.join(root, path.lstrip('/')),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return os.path.abspath(candidate)
    return None


def find_free_scan_pdf(scan_domain):
    """Devuelve dict con pdf_path, target_url, order_id o None."""
    normalized = _normalize_domain(scan_domain)
    if not normalized:
        return None

    conn = _get_minihack_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT o.id, o.target_url, r.pdf_path, o.created_at
            FROM orders o
            JOIN reports r ON r.order_id = o.id
            WHERE o.service_type = 'free'
              AND o.status = 'completed'
              AND r.report_type = 'free'
              AND r.pdf_path IS NOT NULL
              AND (
                LOWER(REPLACE(REPLACE(o.target_url, 'https://', ''), 'http://', '')) LIKE %s
                OR LOWER(REPLACE(REPLACE(o.target_url, 'https://', ''), 'http://', '')) LIKE %s
              )
            ORDER BY o.created_at DESC
            LIMIT 1
            """,
            (f'%{normalized}%', f'%{normalized.replace("www.", "")}%'),
        )
        row = cursor.fetchone()
        if not row:
            return None

        order_id, target_url, pdf_path, created_at = row
        resolved = _resolve_pdf_path(pdf_path)
        if not resolved:
            return None

        return {
            'order_id': order_id,
            'target_url': target_url,
            'pdf_path': resolved,
            'created_at': created_at,
        }
    finally:
        conn.close()


def merge_pdfs(main_pdf_path, annex_pdf_path, output_path):
    """Anexa el PDF del escaneo gratuito al final del informe de auditoría."""
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    for pdf in (main_pdf_path, annex_pdf_path):
        reader = PdfReader(pdf)
        for page in reader.pages:
            writer.add_page(page)

    with open(output_path, 'wb') as out:
        writer.write(out)

    return output_path
