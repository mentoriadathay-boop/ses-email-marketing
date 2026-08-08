import os
import csv
import io
import threading
import uuid
import calendar as cal_module
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
from flask import (Flask, render_template, request, jsonify, redirect,
                   url_for, flash, Response, send_from_directory, session)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import hashlib
import hmac
import json
import secrets
import string
from werkzeug.utils import secure_filename
import psycopg2
import psycopg2.extras
import requests as http_requests
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from apscheduler.schedulers.background import BackgroundScheduler
import re
import math
import email_client as ec

try:
    from bs4 import BeautifulSoup
    BS4_OK = True
except ImportError:
    BS4_OK = False

try:
    import anthropic as _anthropic
    ANTHROPIC_OK = True
except ImportError:
    ANTHROPIC_OK = False

try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_OK = True
except ImportError:
    FIRECRAWL_OK = False

EMAIL_RE = re.compile(r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.permanent_session_lifetime = timedelta(days=30)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
IMAGES_FOLDER = os.path.join(UPLOAD_FOLDER, 'imagens')
ALLOWED_EXTENSIONS = {'csv'}
ALLOWED_IMAGE_EXT = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
_raw_app_url = os.environ.get('APP_URL', '').strip().rstrip('/')
if not _raw_app_url:
    _railway_domain = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '').strip()
    if _railway_domain:
        _raw_app_url = f'https://{_railway_domain}'
    else:
        _raw_app_url = 'http://127.0.0.1:5000'
APP_URL = _raw_app_url
UNSPLASH_ACCESS_KEY = os.environ.get('UNSPLASH_ACCESS_KEY', '')
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')
FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY', '')
HOTMART_TOKEN = os.environ.get('HOTMART_TOKEN', '')
HOTMART_SECRET = os.environ.get('HOTMART_SECRET', '')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'mentoriadathay@gmail.com')
DATABASE_URL = os.environ.get('DATABASE_URL', '')
# psycopg2 exige postgresql:// mas Railway/Heroku fornecem postgres://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)

@app.errorhandler(413)
def _erro_payload_grande(e):
    if request.path.startswith('/ia/') or request.path.startswith('/api/') or request.path.startswith('/email/'):
        return jsonify({'erro': 'Conteúdo muito grande (limite de 5MB). Tente remover imagens grandes ou reduzir o texto.'}), 413
    return e

@app.errorhandler(Exception)
def _erro_geral(e):
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        if request.path.startswith('/ia/') or request.path.startswith('/api/') or request.path.startswith('/email/'):
            return jsonify({'erro': f'Erro {e.code}: {e.description}'}), e.code
        return e
    app.logger.exception('Erro não tratado em %s', request.path)
    if request.path.startswith('/ia/') or request.path.startswith('/api/') or request.path.startswith('/email/'):
        return jsonify({'erro': f'Erro interno: {e}'}), 500
    flash(f'Erro interno: {e}', 'danger')
    return redirect(request.referrer or url_for('index'))

PIXEL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00'
    b'\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00'
    b'\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02'
    b'\x44\x01\x00\x3b'
)

_DEFAULT_TEMPLATES = [
    ('Boas-vindas caloroso', 'Relacionamento',
     'Bem-vindo, {nome}! Estamos felizes em te ter aqui',
     '<p>Olá, <strong>{nome}</strong>!</p><p>É um prazer tê-lo(a) conosco. Estou animado(a) para começar essa jornada juntos!</p><p>Nos próximos dias vou compartilhar conteúdos e oportunidades que podem agregar muito ao seu negócio.</p><p>Qualquer dúvida, basta responder este email.</p><p>Um abraço,<br><strong>Equipe ConvertMail</strong></p>'),
    ('Follow-up após 3 dias', 'Follow-up',
     '{nome}, ainda pensando na nossa conversa?',
     '<p>Olá, <strong>{nome}</strong>,</p><p>Passaram alguns dias desde meu último contato e queria saber se você teve a chance de refletir sobre o que conversamos.</p><p>Fico à disposição para responder qualquer dúvida ou marcar uma conversa rápida de 15 minutos.</p><p>Me avise como posso ajudar!</p><p>Atenciosamente,<br><strong>Equipe ConvertMail</strong></p>'),
    ('Apresentação de produto/serviço', 'Vendas',
     '{nome}, conheça nossa solução para o seu negócio',
     '<p>Olá, <strong>{nome}</strong>!</p><p>Quero aproveitar para apresentar nossa solução que tem ajudado empresas como a sua a <strong>aumentar resultados</strong>.</p><ul><li>Atendimento personalizado</li><li>Resultados comprovados</li><li>Suporte dedicado</li></ul><p>Posso preparar uma apresentação personalizada para você?</p><p>Atenciosamente,<br><strong>Equipe ConvertMail</strong></p>'),
    ('Convite para reunião', 'Relacionamento',
     '{nome}, podemos conversar 15 minutos?',
     '<p>Olá, <strong>{nome}</strong>!</p><p>Gostaria de agendar uma conversa rápida de 15 minutos para entender melhor os desafios do seu negócio e mostrar como podemos ajudar.</p><p>Qual horário funciona melhor para você?</p><p>Aguardo seu retorno!</p><p>Atenciosamente,<br><strong>Equipe ConvertMail</strong></p>'),
    ('Proposta comercial', 'Vendas',
     '{nome}, preparei uma proposta especial para você',
     '<p>Olá, <strong>{nome}</strong>!</p><p>Conforme conversamos, preparei uma proposta personalizada pensando nas necessidades específicas do seu negócio.</p><ul><li>Solução sob medida para o seu segmento</li><li>Condições especiais de investimento</li><li>Implementação rápida e suporte completo</li></ul><p>Podemos agendar uma chamada para detalhar tudo?</p><p>Atenciosamente,<br><strong>Equipe ConvertMail</strong></p>'),
    ('Reengajamento de lead frio', 'Reengajamento',
     '{nome}, faz tempo que não nos falamos...',
     '<p>Olá, <strong>{nome}</strong>!</p><p>Já faz algum tempo desde nosso último contato e queria saber como você está e como vai o seu negócio.</p><p>Temos novidades que podem ser relevantes para você agora.</p><p>Posso te enviar algumas informações?</p><p>Atenciosamente,<br><strong>Equipe ConvertMail</strong></p>'),
    ('Agradecimento pós-reunião', 'Relacionamento',
     '{nome}, obrigado pelo seu tempo hoje!',
     '<p>Olá, <strong>{nome}</strong>!</p><p>Quero agradecer pela conversa de hoje. Foi muito produtivo conhecer melhor o seu negócio e os desafios que você enfrenta.</p><p>Como combinado, vou preparar os próximos passos e enviar para você em breve.</p><p>Um abraço,<br><strong>Equipe ConvertMail</strong></p>'),
    ('Última tentativa de contato', 'Follow-up',
     '{nome}, última mensagem minha sobre isso',
     '<p>Olá, <strong>{nome}</strong>,</p><p>Tentei entrar em contato algumas vezes e entendo que você deve estar ocupado(a).</p><p>Esta será minha última mensagem sobre este assunto.</p><p>Se em algum momento fizer sentido conversar, estarei aqui. Basta responder este email.</p><p>Sucesso no seu negócio!</p><p>Atenciosamente,<br><strong>Equipe ConvertMail</strong></p>'),
]

# ── Banco de dados (PostgreSQL) ─────────────────────────────────────────────

class DBConn:
    """Wrapper fino sobre psycopg2 que imita a API do sqlite3."""
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def execute(self, sql, params=()):
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

def get_db():
    raw = psycopg2.connect(DATABASE_URL)
    return DBConn(raw)

def init_db():
    conn = get_db()
    tables = [
        '''CREATE TABLE IF NOT EXISTS campaigns (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL,
            sender_email TEXT NOT NULL, total_contacts INTEGER DEFAULT 0,
            sent INTEGER DEFAULT 0, errors INTEGER DEFAULT 0, bounces INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT NOW(), finished_at TIMESTAMP
        )''',
        '''CREATE TABLE IF NOT EXISTS campaign_logs (
            id SERIAL PRIMARY KEY, campaign_id INTEGER NOT NULL,
            contact_email TEXT NOT NULL, contact_name TEXT, status TEXT NOT NULL,
            error_message TEXT, sent_at TIMESTAMP DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS sequences (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL, description TEXT,
            sender_email TEXT NOT NULL DEFAULT '', status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS sequence_steps (
            id SERIAL PRIMARY KEY, sequence_id INTEGER NOT NULL,
            step_number INTEGER NOT NULL, day_offset INTEGER NOT NULL,
            subject TEXT NOT NULL, body_html TEXT NOT NULL, condition TEXT DEFAULT 'always',
            ab_subject_b TEXT, ab_body_b TEXT, ab_ratio INTEGER DEFAULT 50
        )''',
        '''CREATE TABLE IF NOT EXISTS sequence_contacts (
            id SERIAL PRIMARY KEY, sequence_id INTEGER NOT NULL,
            contact_email TEXT NOT NULL, contact_name TEXT,
            current_step INTEGER DEFAULT 1, status TEXT DEFAULT 'active',
            next_send_at TIMESTAMP, started_at TIMESTAMP DEFAULT NOW(),
            finished_at TIMESTAMP
        )''',
        '''CREATE TABLE IF NOT EXISTS sequence_logs (
            id SERIAL PRIMARY KEY, sequence_id INTEGER NOT NULL,
            contact_email TEXT NOT NULL, step_number INTEGER NOT NULL,
            status TEXT NOT NULL, error_message TEXT, ab_version TEXT DEFAULT 'A',
            sent_at TIMESTAMP DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS email_opens (
            id SERIAL PRIMARY KEY, sequence_id INTEGER,
            contact_email TEXT NOT NULL, step_number INTEGER,
            opened_at TIMESTAMP DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS email_templates (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL, category TEXT,
            subject TEXT, body_html TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS signature (
            id SERIAL PRIMARY KEY, name TEXT, body_html TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS contact_scores (
            id SERIAL PRIMARY KEY, email TEXT NOT NULL UNIQUE,
            score INTEGER DEFAULT 0, updated_at TIMESTAMP DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS send_analytics (
            id SERIAL PRIMARY KEY, contact_email TEXT NOT NULL,
            sent_at TIMESTAMP NOT NULL, opened_at TIMESTAMP,
            hour_of_day INTEGER, day_of_week INTEGER
        )''',
        '''CREATE TABLE IF NOT EXISTS contacts (
            id SERIAL PRIMARY KEY, email TEXT NOT NULL UNIQUE,
            name TEXT, phone TEXT, company TEXT, position TEXT,
            status TEXT DEFAULT 'lead', score INTEGER DEFAULT 0, tags TEXT, notes TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS contact_activities (
            id SERIAL PRIMARY KEY, contact_email TEXT NOT NULL,
            type TEXT NOT NULL, description TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS blacklist (
            id SERIAL PRIMARY KEY, email TEXT NOT NULL UNIQUE,
            reason TEXT, added_at TIMESTAMP DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS contact_purchases (
            id SERIAL PRIMARY KEY, contact_email TEXT NOT NULL,
            product TEXT NOT NULL, purchased_at DATE,
            created_at TIMESTAMP DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS mailings (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL,
            filename TEXT NOT NULL, contact_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS mailing_contacts (
            id SERIAL PRIMARY KEY,
            mailing_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            name TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            UNIQUE(mailing_id, email)
        )''',
        '''CREATE TABLE IF NOT EXISTS email_accounts (
            id SERIAL PRIMARY KEY,
            label TEXT NOT NULL DEFAULT 'Principal',
            imap_server TEXT NOT NULL,
            imap_port INTEGER NOT NULL DEFAULT 993,
            smtp_server TEXT NOT NULL,
            smtp_port INTEGER NOT NULL DEFAULT 587,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            use_ssl BOOLEAN DEFAULT TRUE,
            sent_folder TEXT DEFAULT 'Sent',
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS uploaded_images (
            id TEXT PRIMARY KEY,
            mime_type TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS brand_kits (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            logo_url TEXT,
            slogan TEXT,
            primary_color TEXT DEFAULT '#1a3a6b',
            secondary_color TEXT DEFAULT '#D4AF37',
            accent_color TEXT DEFAULT '#4361ee',
            text_color TEXT DEFAULT '#333333',
            bg_color TEXT DEFAULT '#ffffff',
            font_primary TEXT DEFAULT 'Arial',
            font_secondary TEXT DEFAULT 'Georgia',
            tone_of_voice TEXT,
            instagram TEXT, facebook TEXT, linkedin TEXT,
            youtube TEXT, whatsapp TEXT, website TEXT,
            signature_name TEXT, signature_role TEXT, signature_phone TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )''',
        '''CREATE TABLE IF NOT EXISTS nichos (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT NOW()
        )''',
    ]
    for sql in tables:
        conn.execute(sql)

    _NICHOS_SEED = [
        'Empreendedorismo e Negócios','Saúde e Bem-Estar','Desenvolvimento Pessoal e Espiritualidade',
        'Mulheres','Liderança e Gestão','Educação e Ensino','Marketing Digital e Vendas',
        'Relacionamentos e Família','Beleza e Estética','Carreira e Recursos Humanos',
        'Finanças e Investimentos','Tecnologia e Inovação','Direito e Advocacia','Coaching',
        'Alimentação e Nutrição','Psicologia e Terapia','Fitness e Esportes','Arte e Cultura',
        'Mentoria e Consultoria',
    ]
    for n in _NICHOS_SEED:
        conn.execute('INSERT INTO nichos (name) VALUES (%s) ON CONFLICT (name) DO NOTHING', (n,))

    # Migrations idempotentes via bloco DO
    for col_sql in [
        "ALTER TABLE sequence_steps ADD COLUMN ab_subject_b TEXT",
        "ALTER TABLE sequence_steps ADD COLUMN ab_body_b TEXT",
        "ALTER TABLE sequence_steps ADD COLUMN ab_ratio INTEGER DEFAULT 50",
        "ALTER TABLE sequence_logs ADD COLUMN ab_version TEXT DEFAULT 'A'",
        "ALTER TABLE contacts ADD COLUMN product_interest TEXT",
        "ALTER TABLE contacts ADD COLUMN source TEXT",
        "ALTER TABLE campaigns ADD COLUMN mailing_id INTEGER",
        "ALTER TABLE campaigns ADD COLUMN sequence_id INTEGER",
        "ALTER TABLE campaigns ADD COLUMN scheduled_at TIMESTAMP",
        "ALTER TABLE campaigns ADD COLUMN csv_filename TEXT",
        "ALTER TABLE sequences ADD COLUMN start_date DATE",
        "ALTER TABLE sequences ADD COLUMN preferred_hour INTEGER",
        "ALTER TABLE signature ADD COLUMN sender_name TEXT DEFAULT 'ConvertMail'",
        "ALTER TABLE contacts ADD COLUMN nicho TEXT",
        "ALTER TABLE mailing_contacts ADD COLUMN nicho TEXT DEFAULT ''",
        "ALTER TABLE email_opens ADD COLUMN campaign_id INTEGER",
        "ALTER TABLE contact_purchases ADD COLUMN amount NUMERIC(12,2) DEFAULT 0",
        "ALTER TABLE contact_purchases ADD COLUMN campaign_id INTEGER",
        "ALTER TABLE campaigns ADD COLUMN resent_from INTEGER",
        "ALTER TABLE campaigns ADD COLUMN total_opened INTEGER DEFAULT 0",
        "ALTER TABLE campaigns ADD COLUMN total_clicked INTEGER DEFAULT 0",
        "ALTER TABLE contacts ADD COLUMN whatsapp TEXT",
        "ALTER TABLE contacts ADD COLUMN whatsapp_notes TEXT",
        "ALTER TABLE contacts ADD COLUMN city TEXT",
        "ALTER TABLE contacts ADD COLUMN state TEXT",
        "ALTER TABLE contacts ADD COLUMN country TEXT",
    ]:
        try:
            conn.execute(f"DO $$ BEGIN {col_sql}; EXCEPTION WHEN duplicate_column THEN NULL; END $$")
        except Exception:
            conn.rollback()

    conn.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id SERIAL PRIMARY KEY,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        body TEXT,
        contact_email TEXT,
        campaign_id INTEGER,
        read BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW()
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS warmup_plans (
        id SERIAL PRIMARY KEY,
        sender_email TEXT NOT NULL,
        daily_limit INTEGER DEFAULT 10,
        current_day INTEGER DEFAULT 0,
        total_days INTEGER DEFAULT 14,
        growth_rate NUMERIC(4,2) DEFAULT 1.5,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT NOW()
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS capture_forms (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        tag TEXT DEFAULT '',
        sequence_id INTEGER,
        heading TEXT DEFAULT 'Inscreva-se',
        description TEXT DEFAULT 'Receba novidades no seu email.',
        button_text TEXT DEFAULT 'Cadastrar',
        primary_color TEXT DEFAULT '#4361ee',
        created_at TIMESTAMP DEFAULT NOW()
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT,
        status TEXT DEFAULT 'active',
        role TEXT DEFAULT 'user',
        hotmart_transaction TEXT,
        hotmart_subscription TEXT,
        plan TEXT DEFAULT 'pro',
        created_at TIMESTAMP DEFAULT NOW(),
        expires_at TIMESTAMP,
        last_login TIMESTAMP
    )''')

    for col_sql2 in [
        "ALTER TABLE users ADD COLUMN hotmart_subscription TEXT",
    ]:
        try:
            conn.execute(f"DO $$ BEGIN {col_sql2}; EXCEPTION WHEN duplicate_column THEN NULL; END $$")
        except Exception:
            conn.rollback()

    admin_pw = os.environ.get('ADMIN_PASSWORD', 'admin123')
    conn.execute(
        "INSERT INTO users (email, password_hash, name, status, role) VALUES (%s, %s, %s, 'active', 'admin') ON CONFLICT (email) DO UPDATE SET password_hash=%s, role='admin'",
        (ADMIN_EMAIL, generate_password_hash(admin_pw), 'Administrador', generate_password_hash(admin_pw)))

    conn.commit()

    cur = conn.execute('SELECT COUNT(*) as n FROM email_templates')
    if cur.fetchone()['n'] == 0:
        for name, cat, subj, body in _DEFAULT_TEMPLATES:
            conn.execute(
                'INSERT INTO email_templates (name,category,subject,body_html) VALUES (%s,%s,%s,%s)',
                (name, cat, subj, body))
        conn.commit()

    conn.close()

# ── Auth Helpers ───────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Faça login para acessar a plataforma.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('user_role') != 'admin':
            flash('Acesso restrito a administradores.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if 'user_id' not in session:
        return None
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id=%s', (session['user_id'],)).fetchone()
    conn.close()
    return user

def _generate_password(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

def _send_welcome_email(to_email, to_name, password):
    if not BREVO_API_KEY:
        return
    try:
        config = sib_api_v3_sdk.Configuration()
        config.api_key['api-key'] = BREVO_API_KEY
        api = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(config))
        html = f'''<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
            <h2 style="color:#1AC78A">Bem-vindo(a) ao ConvertMail!</h2>
            <p>Olá, <strong>{to_name or "cliente"}</strong>!</p>
            <p>Sua conta foi criada com sucesso. Aqui estão seus dados de acesso:</p>
            <div style="background:#f5f5f5;padding:20px;border-radius:8px;margin:20px 0">
                <p><strong>Email:</strong> {to_email}</p>
                <p><strong>Senha:</strong> {password}</p>
            </div>
            <p>Acesse a plataforma: <a href="{APP_URL}/login" style="color:#1AC78A;font-weight:bold">{APP_URL}/login</a></p>
            <p style="color:#999;font-size:0.85rem">Recomendamos alterar sua senha no primeiro acesso.</p>
            <hr style="border:none;border-top:1px solid #eee;margin:20px 0">
            <p style="color:#999;font-size:0.8rem">ConvertMail — TFA Soluções Digitais</p>
        </div>'''
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{'email': to_email, 'name': to_name or to_email}],
            sender={'name': 'ConvertMail', 'email': 'naoresponda@convertmail.com.br'},
            subject='Bem-vindo ao ConvertMail — Seus dados de acesso',
            html_content=html
        )
        api.send_transac_email(email)
    except Exception as e:
        app.logger.warning('Erro ao enviar email de boas-vindas: %s', e)

# ── Helpers ─────────────────────────────────────────────────────────────────

campaign_progress = {}
extraction_jobs = {}

def allowed_file(f): return '.' in f and f.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def allowed_image(f): return '.' in f and f.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXT

def _col(row, *keys):
    for k in keys:
        v = row.get(k)
        if v and str(v).strip():
            return str(v).strip()
    return ''

def parse_csv(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f'Arquivo CSV não encontrado: {filepath}')
    contacts = []
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            with open(filepath, newline='', encoding=enc) as f:
                for row in csv.DictReader(f):
                    email = _col(row, 'email', 'Email', 'EMAIL', 'e-mail', 'E-mail', 'E-Mail')
                    if not email:
                        continue
                    contacts.append({
                        'email':            email,
                        'name':             _col(row, 'nome', 'Nome', 'NOME', 'name', 'Name'),
                        'phone':            _col(row, 'telefone', 'Telefone', 'phone', 'Phone', 'tel', 'Tel'),
                        'company':          _col(row, 'empresa', 'Empresa', 'company', 'Company'),
                        'position':         _col(row, 'cargo', 'Cargo', 'position', 'Position'),
                        'tags':             _col(row, 'tags', 'Tags', 'TAGS'),
                        'notes':            _col(row, 'notas', 'Notas', 'notes', 'Notes'),
                        'product_interest': _col(row, 'produto', 'Produto', 'product_interest'),
                        'source':           _col(row, 'fonte', 'Fonte', 'source', 'Source'),
                        'status':           _col(row, 'status', 'Status') or 'lead',
                        'nicho':            _col(row, 'nicho', 'Nicho', 'NICHO', 'niche', 'Niche', 'segmento', 'Segmento', 'categoria', 'Categoria'),
                        'city':             _col(row, 'cidade', 'Cidade', 'city', 'City', 'CIDADE'),
                        'state':            _col(row, 'estado', 'Estado', 'state', 'State', 'UF', 'uf'),
                        'country':          _col(row, 'pais', 'País', 'Pais', 'country', 'Country', 'PAIS'),
                    })
            return contacts
        except UnicodeDecodeError:
            continue
        except Exception:
            continue
    return contacts

def get_mailing_contacts_db(mailing_id, conn):
    rows = conn.execute(
        'SELECT email, name, tags FROM mailing_contacts WHERE mailing_id=%s ORDER BY id',
        (mailing_id,)).fetchall()
    return [{'email': r['email'], 'name': r['name'] or '', 'tags': r['tags'] or ''} for r in rows]

def upsert_contact(email, name='', tags='', conn=None, force_update=False, **extra):
    """Insere ou atualiza contato no CRM.
    extra: phone, company, position, notes, product_interest, source, status, nicho, city, state, country
    force_update=True: sobrescreve campos mesmo que já preenchidos (usado no upload CSV).
    force_update=False: só preenche campos vazios/NULL.
    Tags são sempre mescladas (nunca sobrescritas).
    """
    close = conn is None
    if close: conn = get_db()

    conn.execute(
        'INSERT INTO contacts (email,name,tags,status) VALUES (%s,%s,%s,%s) ON CONFLICT (email) DO NOTHING',
        (email, name, tags, extra.get('status') or 'lead'))

    fill_fields = ('name', 'phone', 'company', 'position', 'notes', 'product_interest', 'source', 'nicho', 'city', 'state', 'country')
    overwrite_fields = ('status', 'product_interest', 'nicho')
    for field in fill_fields:
        value = name if field == 'name' else extra.get(field, '')
        if value:
            if force_update and field in overwrite_fields:
                conn.execute(
                    f"UPDATE contacts SET {field}=%s, updated_at=NOW() WHERE email=%s",
                    (value, email))
            else:
                conn.execute(
                    f"UPDATE contacts SET {field}=%s, updated_at=NOW() "
                    f"WHERE email=%s AND ({field} IS NULL OR {field}='')",
                    (value, email))
    if force_update and extra.get('status'):
        conn.execute(
            "UPDATE contacts SET status=%s, updated_at=NOW() WHERE email=%s",
            (extra['status'], email))

    # Tags: mescla sem duplicar
    if tags:
        cur = conn.execute('SELECT tags FROM contacts WHERE email=%s', (email,))
        existing = cur.fetchone()
        if existing and existing['tags']:
            merged = ','.join(sorted(set(
                t.strip() for t in (existing['tags'] + ',' + tags).split(',') if t.strip())))
        else:
            merged = tags
        conn.execute('UPDATE contacts SET tags=%s WHERE email=%s', (merged, email))

    if close: conn.commit(); conn.close()

def is_blacklisted(email, conn=None):
    close = conn is None
    if close: conn = get_db()
    r = conn.execute('SELECT id FROM blacklist WHERE email=%s', (email,)).fetchone()
    if close: conn.close()
    return r is not None

def add_to_blacklist(email, reason, conn=None):
    close = conn is None
    if close: conn = get_db()
    try:
        conn.execute(
            'INSERT INTO blacklist (email,reason) VALUES (%s,%s) ON CONFLICT (email) DO NOTHING',
            (email, reason))
        if close: conn.commit()
    except Exception: pass
    if close: conn.close()

def update_score(email, delta, conn=None):
    close = conn is None
    if close: conn = get_db()
    cur = conn.execute('SELECT score FROM contact_scores WHERE email=%s', (email,))
    existing = cur.fetchone()
    if existing:
        new_score = max(0, existing['score'] + delta)
        conn.execute(
            'UPDATE contact_scores SET score=%s,updated_at=NOW() WHERE email=%s',
            (new_score, email))
    else:
        new_score = max(0, delta)
        conn.execute('INSERT INTO contact_scores (email,score) VALUES (%s,%s)', (email, new_score))
    conn.execute('UPDATE contacts SET score=%s WHERE email=%s', (new_score, email))
    if close: conn.commit(); conn.close()
    return new_score

def enroll_contacts_in_sequence(seq_id, contacts, conn):
    seq = conn.execute('SELECT * FROM sequences WHERE id=%s', (seq_id,)).fetchone()
    if not seq:
        return 0
    first_step = conn.execute(
        'SELECT * FROM sequence_steps WHERE sequence_id=%s ORDER BY step_number LIMIT 1',
        (seq_id,)).fetchone()
    if not first_step:
        return 0
    now = datetime.now()
    start_base = now
    sd = seq.get('start_date')
    if sd:
        try:
            sd_dt = datetime.strptime(str(sd)[:10], '%Y-%m-%d') if not isinstance(sd, datetime) else sd
            if sd_dt > now:
                start_base = sd_dt
        except Exception:
            pass
    next_dt = start_base + timedelta(days=first_step['day_offset'])
    ph = seq.get('preferred_hour')
    if ph is not None:
        next_dt = next_dt.replace(hour=int(ph), minute=0, second=0, microsecond=0)
    next_send = next_dt.strftime('%Y-%m-%d %H:%M:%S')
    added = 0
    for c in contacts:
        if is_blacklisted(c['email'], conn):
            continue
        existing = conn.execute(
            'SELECT id FROM sequence_contacts WHERE sequence_id=%s AND contact_email=%s',
            (seq_id, c['email'])).fetchone()
        if not existing:
            conn.execute(
                'INSERT INTO sequence_contacts (sequence_id,contact_email,contact_name,current_step,next_send_at) VALUES (%s,%s,%s,%s,%s)',
                (seq_id, c['email'], c.get('name', ''), first_step['step_number'], next_send))
            added += 1
    return added

def log_activity(email, type_, description, conn=None):
    close = conn is None
    if close: conn = get_db()
    conn.execute(
        'INSERT INTO contact_activities (contact_email,type,description) VALUES (%s,%s,%s)',
        (email, type_, description))
    if close: conn.commit(); conn.close()

def get_best_send_hour(email):
    conn = get_db()
    cur = conn.execute(
        'SELECT hour_of_day FROM send_analytics WHERE contact_email=%s AND hour_of_day IS NOT NULL'
        ' GROUP BY hour_of_day ORDER BY COUNT(*) DESC LIMIT 1',
        (email,))
    row = cur.fetchone()
    conn.close()
    return row['hour_of_day'] if row else None

def score_label(score):
    s = score or 0
    if s >= 100: return ('Muito Quente', '#5B2A6E', '#EDE0F2')
    if s >= 51:  return ('Quente', '#ea580c', '#ffedd5')
    if s >= 21:  return ('Morno', '#ca8a04', '#fef9c3')
    return ('Frio', '#2563eb', '#dbeafe')

app.jinja_env.globals['score_label'] = score_label

def get_sender_name():
    try:
        conn = get_db()
        row = conn.execute('SELECT sender_name FROM signature ORDER BY id DESC LIMIT 1').fetchone()
        conn.close()
        return (row['sender_name'] or 'ConvertMail') if row else 'ConvertMail'
    except Exception:
        return 'ConvertMail'

def send_email_brevo(sender, recipient_email, recipient_name, subject, body_html):
    personalized_subject = subject.replace('{nome}', recipient_name or 'Cliente')
    personalized_body = body_html.replace('{nome}', recipient_name or 'Cliente')
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    emails = [e.strip() for e in re.split(r'[;,]', recipient_email) if e.strip()]
    if not emails:
        raise ValueError(f'Email invalido: {recipient_email}')
    to_list = []
    for em in emails:
        entry = {'email': em}
        if recipient_name and recipient_name.strip() and len(emails) == 1:
            entry['name'] = recipient_name.strip()
        to_list.append(entry)
    sender_info = {'email': sender, 'name': get_sender_name()}
    email_obj = sib_api_v3_sdk.SendSmtpEmail(
        to=to_list,
        sender=sender_info,
        reply_to=sender_info,
        subject=personalized_subject,
        html_content=personalized_body
    )
    return api_instance.send_transac_email(email_obj)

# ── Prospecção / Extração de Leads ───────────────────────────────────────────

def _robots_permite(url):
    from urllib.robotparser import RobotFileParser
    from urllib.parse import urlparse
    try:
        p = urlparse(url)
        rp = RobotFileParser()
        rp.set_url(f"{p.scheme}://{p.netloc}/robots.txt")
        rp.read()
        return rp.can_fetch('*', url)
    except Exception:
        return True

def _proximas_paginas(soup, base_url, ja_vistas):
    from urllib.parse import urljoin
    candidatos = set()
    for a in soup.find_all('a', rel=lambda r: r and 'next' in r):
        h = a.get('href', '')
        if h: candidatos.add(urljoin(base_url, h))
    for a in soup.find_all('a', href=True):
        txt = a.get_text(strip=True).lower()
        if txt in ('próxima', 'próximo', 'proximo', 'next', '>>', '›', '→', 'avançar'):
            candidatos.add(urljoin(base_url, a['href']))
    return [u for u in candidatos if u not in ja_vistas]

def _enriquecer_claude(texto, url):
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key or not ANTHROPIC_OK:
        return []
    try:
        client = _anthropic.Anthropic(api_key=api_key)
        resposta = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=2048,
            messages=[{'role': 'user', 'content': (
                f"Analise o texto desta página web ({url}) e extraia TODOS os contatos/leads.\n"
                "Para cada contato retorne um objeto JSON com os campos disponíveis:\n"
                "email, nome, telefone, empresa, cargo.\n"
                "Retorne SOMENTE um array JSON válido, sem markdown. Se não houver, retorne [].\n\n"
                f"Texto:\n{texto[:6000]}"
            )}]
        )
        raw = resposta.content[0].text.strip()
        s, e = raw.find('['), raw.rfind(']') + 1
        if s >= 0 and e > s:
            import json as _json
            return _json.loads(raw[s:e])
    except Exception:
        pass
    return []

def _extrair_com_firecrawl(url, modo='html'):
    if not FIRECRAWL_OK or not FIRECRAWL_API_KEY:
        return None
    try:
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
        params = {
            'formats': ['html'] if modo == 'html' else ['markdown'],
            'onlyMainContent': True,
            'includeTags': ['a', 'button', 'input'],
        }
        resultado = app.scrape_url(url, params=params)
        if resultado:
            if modo == 'html' and 'html' in resultado:
                return resultado['html']
            elif modo == 'markdown' and 'markdown' in resultado:
                return resultado['markdown']
            elif 'content' in resultado:
                return resultado['content']
    except Exception:
        pass
    return None

def _extrair_pagina_html(url):
    html = _extrair_com_firecrawl(url, modo='html')
    if html:
        return html

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    }
    r = http_requests.get(url, headers=headers, timeout=15, allow_redirects=True)
    r.raise_for_status()
    return r.text

def _extrair_contatos_firecrawl_direto(url):
    if not FIRECRAWL_OK or not FIRECRAWL_API_KEY:
        return []
    try:
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
        resultado = app.scrape_url(url, params={
            'formats': ['markdown'],
            'onlyMainContent': True,
        })
        if resultado and 'markdown' in resultado:
            texto = resultado['markdown'][:10000]
            return _enriquecer_claude(texto, url)
    except Exception:
        pass
    return []

def _leads_da_pagina(html, url):
    """Extrai emails com regex + contexto. Retorna (lista_leads, soup_ou_None)."""
    ignore = {'example.com', 'seudominio', 'yoursite', 'wordpress.org',
              'schema.org', 'w3.org', 'wpcf7', 'googleapis'}
    if BS4_OK:
        soup = BeautifulSoup(html, 'lxml')
        for tag in soup(['script', 'style', 'meta', 'noscript']):
            tag.decompose()
        text = soup.get_text(separator=' ')
    else:
        soup = None
        text = html
    emails = {e.lower() for e in EMAIL_RE.findall(text)
              if not any(ign in e.lower() for ign in ignore)}
    leads = [{'email': e, 'nome': '', 'telefone': '', 'empresa': '', 'cargo': ''}
             for e in emails]
    return leads, soup

def _run_extracao(job_id, url, max_pages, ignorar_robots):
    job = extraction_jobs[job_id]
    try:
        if not ignorar_robots and not _robots_permite(url):
            job['status'] = 'robots_blocked'
            return

        job['status'] = 'running'
        fila = [url]
        vistas = set()
        todos = {}   # email -> lead dict

        while fila and len(vistas) < max_pages:
            cur_url = fila.pop(0)
            if cur_url in vistas:
                continue
            vistas.add(cur_url)
            job['pages_done'] = len(vistas)
            job['msg'] = f'Página {len(vistas)} — {cur_url[:60]}…'

            try:
                html = _extrair_pagina_html(cur_url)
            except Exception as ex:
                job.setdefault('erros', []).append(str(ex))
                continue

            leads_regex, soup = _leads_da_pagina(html, cur_url)
            texto = (soup.get_text(separator=' ') if soup else html)[:8000]

            # Claude enriquece
            leads_claude = _enriquecer_claude(texto, cur_url)
            for lc in leads_claude:
                em = lc.get('email', '').strip().lower()
                if em and EMAIL_RE.match(em):
                    todos[em] = {
                        'email': em,
                        'nome':     lc.get('nome') or lc.get('name', ''),
                        'telefone': lc.get('telefone') or lc.get('phone', ''),
                        'empresa':  lc.get('empresa') or lc.get('company', ''),
                        'cargo':    lc.get('cargo') or lc.get('position', ''),
                    }
            for lr in leads_regex:
                if lr['email'] not in todos:
                    todos[lr['email']] = lr

            # Paginação
            if soup:
                for prox in _proximas_paginas(soup, cur_url, vistas):
                    if prox not in fila:
                        fila.append(prox)
            job['total_pages'] = min(len(vistas) + len(fila), max_pages)

        job['leads'] = list(todos.values())
        job['status'] = 'done'
        job['msg'] = f'{len(job["leads"])} lead(s) em {len(vistas)} página(s)'
    except Exception as ex:
        job['status'] = 'error'
        job['msg'] = str(ex)

# ── Campanha ─────────────────────────────────────────────────────────────────

def run_campaign(campaign_id, contacts, sender, subject, body_html, sequence_id=None):
    conn = get_db()
    campaign_progress[campaign_id] = {'total': len(contacts), 'sent': 0, 'errors': 0, 'status': 'running', 'logs': []}
    conn.execute("UPDATE campaigns SET status='running',total_contacts=%s WHERE id=%s", (len(contacts), campaign_id))
    conn.commit()

    blacklisted_count = 0
    for contact in contacts:
        email = contact['email']
        name = contact.get('name', '')

        if is_blacklisted(email, conn):
            blacklisted_count += 1
            continue

        upsert_contact(email, name, contact.get('tags', ''), conn)

        pixel_url = f"{APP_URL}/track/open?email={quote(email)}&campaign={campaign_id}"
        unsub_url = f"{APP_URL}/descadastrar?email={quote(email)}"
        print(f"[CAMPAIGN] Pixel URL: {pixel_url[:80]}...", flush=True)
        body_with_tracking = (body_html
            + f'<img src="{pixel_url}" width="1" height="1" style="display:none;border:0" />'
            + f'<div style="text-align:center;margin-top:24px;font-size:11px;color:#aaa"><a href="{unsub_url}" style="color:#aaa">Descadastrar</a></div>')

        try:
            send_email_brevo(sender, email, name, subject, body_with_tracking)
            status = 'sent'
            campaign_progress[campaign_id]['sent'] += 1
            campaign_progress[campaign_id]['logs'].append({'email': email, 'name': name, 'status': 'sent', 'error': None})
            conn.execute("UPDATE campaigns SET sent=sent+1 WHERE id=%s", (campaign_id,))
            log_activity(email, 'email_sent', f'Campanha: {campaign_id}', conn)
        except Exception as e:
            err_msg = str(e)
            status = 'error'
            campaign_progress[campaign_id]['errors'] += 1
            campaign_progress[campaign_id]['logs'].append({'email': email, 'name': name, 'status': 'error', 'error': err_msg})
            conn.execute("UPDATE campaigns SET errors=errors+1 WHERE id=%s", (campaign_id,))

        conn.execute(
            "INSERT INTO campaign_logs (campaign_id,contact_email,contact_name,status,error_message) VALUES (%s,%s,%s,%s,%s)",
            (campaign_id, email, name, status, campaign_progress[campaign_id]['logs'][-1]['error']))
        conn.commit()

    if sequence_id:
        enroll_contacts_in_sequence(int(sequence_id), contacts, conn)
        conn.commit()

    campaign_progress[campaign_id]['status'] = 'done'
    conn.execute("UPDATE campaigns SET status='done',finished_at=NOW() WHERE id=%s", (campaign_id,))
    conn.commit()
    conn.close()

# ── Agendador de cadências ────────────────────────────────────────────────────

def processar_cadencias():
    conn = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cur = conn.execute('''
        SELECT sc.*, s.sender_email AS seq_sender, s.preferred_hour AS seq_preferred_hour
        FROM sequence_contacts sc
        JOIN sequences s ON s.id = sc.sequence_id
        WHERE sc.status = 'active' AND sc.next_send_at <= %s
    ''', (now,))
    pending = cur.fetchall()

    if not pending:
        conn.close()
        return

    if not BREVO_API_KEY:
        print(f"[processar_cadencias] ERRO: BREVO_API_KEY não configurada — {len(pending)} envio(s) pendente(s) não processado(s).", flush=True)
        conn.close()
        return

    for c in pending:
        seq_id = c['sequence_id']
        step_num = c['current_step']
        email = c['contact_email']
        name = c['contact_name'] or 'Cliente'
        sender = c['seq_sender']
        contact_id = c['id']

        if is_blacklisted(email, conn):
            conn.execute("UPDATE sequence_contacts SET status='stopped' WHERE id=%s", (contact_id,))
            conn.commit()
            continue

        cur2 = conn.execute(
            'SELECT * FROM sequence_steps WHERE sequence_id=%s AND step_number=%s',
            (seq_id, step_num))
        step = cur2.fetchone()
        if not step:
            conn.execute(
                "UPDATE sequence_contacts SET status='finished',finished_at=NOW() WHERE id=%s",
                (contact_id,))
            conn.commit()
            continue

        should_send = True
        cond = step['condition']
        if cond in ('only_if_opened', 'only_if_not_opened'):
            cur3 = conn.execute(
                'SELECT COUNT(*) as n FROM email_opens WHERE sequence_id=%s AND contact_email=%s AND step_number<%s',
                (seq_id, email, step_num))
            opens = cur3.fetchone()['n']
            if cond == 'only_if_opened' and opens == 0: should_send = False
            elif cond == 'only_if_not_opened' and opens > 0: should_send = False

        if should_send:
            ab_version = 'A'
            ab_ratio = step['ab_ratio'] if step['ab_ratio'] is not None else 50
            if step['ab_subject_b']:
                ab_version = 'A' if (hash(email) % 100) < ab_ratio else 'B'

            if ab_version == 'B' and step['ab_subject_b']:
                use_subject = step['ab_subject_b']
                use_body = step['ab_body_b'] or step['body_html']
            else:
                use_subject = step['subject']
                use_body = step['body_html']

            pixel_url = f"{APP_URL}/track/open?email={quote(email)}&seq={seq_id}&step={step_num}"
            unsub_url = f"{APP_URL}/descadastrar?email={quote(email)}&seq={seq_id}"
            body = (use_body
                    + f'<img src="{pixel_url}" width="1" height="1" style="display:none;border:0" />'
                    + f'<div style="text-align:center;margin-top:24px;font-size:11px;color:#aaa"><a href="{unsub_url}" style="color:#aaa">Descadastrar</a></div>')

            try:
                send_email_brevo(sender, email, name, use_subject, body)
                conn.execute(
                    'INSERT INTO sequence_logs (sequence_id,contact_email,step_number,status,ab_version) VALUES (%s,%s,%s,%s,%s)',
                    (seq_id, email, step_num, 'sent', ab_version))
                conn.execute(
                    'INSERT INTO send_analytics (contact_email,sent_at) VALUES (%s,%s)',
                    (email, now))
                log_activity(email, 'email_sent', f'Cadência {seq_id}, passo {step_num} (versão {ab_version})', conn)
            except Exception as e:
                conn.execute(
                    'INSERT INTO sequence_logs (sequence_id,contact_email,step_number,status,error_message,ab_version) VALUES (%s,%s,%s,%s,%s,%s)',
                    (seq_id, email, step_num, 'error', str(e), ab_version))
        else:
            conn.execute(
                'INSERT INTO sequence_logs (sequence_id,contact_email,step_number,status) VALUES (%s,%s,%s,%s)',
                (seq_id, email, step_num, 'skipped'))

        cur4 = conn.execute(
            'SELECT * FROM sequence_steps WHERE sequence_id=%s AND step_number=%s',
            (seq_id, step_num + 1))
        next_step = cur4.fetchone()
        if next_step:
            started_at = c['started_at']
            if isinstance(started_at, str):
                try: started_at = datetime.strptime(started_at, '%Y-%m-%d %H:%M:%S')
                except: started_at = datetime.now()
            elif started_at is None:
                started_at = datetime.now()
            next_dt = started_at + timedelta(days=next_step['day_offset'])
            best_hour = get_best_send_hour(email)
            seq_preferred_hour = c.get('seq_preferred_hour')
            if best_hour is not None:
                next_dt = next_dt.replace(hour=best_hour, minute=0, second=0)
            elif seq_preferred_hour is not None:
                next_dt = next_dt.replace(hour=int(seq_preferred_hour), minute=0, second=0)
            next_send = next_dt.strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                'UPDATE sequence_contacts SET current_step=%s,next_send_at=%s WHERE id=%s',
                (step_num + 1, next_send, contact_id))
        else:
            conn.execute(
                "UPDATE sequence_contacts SET status='finished',finished_at=NOW() WHERE id=%s",
                (contact_id,))

        conn.commit()
    conn.close()

def calcular_scores_inativos():
    conn = get_db()
    sete_dias_atras = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    cur = conn.execute('''
        SELECT DISTINCT cs.email FROM contact_scores cs
        WHERE cs.score > 0
        AND cs.email NOT IN (
            SELECT DISTINCT contact_email FROM email_opens WHERE opened_at >= %s
        )
    ''', (sete_dias_atras,))
    inativos = cur.fetchall()
    for row in inativos:
        update_score(row['email'], -5, conn)
    conn.commit()
    conn.close()

def processar_campanhas_agendadas():
    conn = get_db()
    now = datetime.now()
    cur = conn.execute(
        "SELECT * FROM campaigns WHERE status='scheduled' AND scheduled_at <= %s",
        (now,))
    scheduled = cur.fetchall()
    conn.close()
    for campaign in scheduled:
        campaign_id = campaign['id']
        sender = campaign['sender_email']
        subject = campaign['subject']
        body_html = campaign['body']
        csv_filename = campaign.get('csv_filename')
        mailing_id = campaign.get('mailing_id')
        sequence_id = campaign.get('sequence_id')
        contacts = []
        if csv_filename:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], csv_filename)
            contacts = parse_csv(filepath)
        elif mailing_id:
            conn_m = get_db()
            contacts = get_mailing_contacts_db(int(mailing_id), conn_m)
            if not contacts:
                ml = conn_m.execute('SELECT * FROM mailings WHERE id=%s', (mailing_id,)).fetchone()
                if ml:
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], ml['filename'])
                    if os.path.exists(filepath):
                        contacts = parse_csv(filepath)
            conn_m.close()
        if not contacts:
            conn2 = get_db()
            conn2.execute("UPDATE campaigns SET status='error' WHERE id=%s", (campaign_id,))
            conn2.commit()
            conn2.close()
            continue
        conn2 = get_db()
        conn2.execute("UPDATE campaigns SET total_contacts=%s WHERE id=%s", (len(contacts), campaign_id))
        conn2.commit()
        conn2.close()
        t = threading.Thread(
            target=run_campaign,
            args=(campaign_id, contacts, sender, subject, body_html, sequence_id),
            daemon=True)
        t.start()

# ── Guard: redireciona para setup se banco não estiver pronto + auth ────────

_PUBLIC_ENDPOINTS = {
    'health', 'setup_page', 'static', 'landing', 'login', 'logout',
    'webhook_hotmart', 'track_open', 'track_click', 'descadastrar',
    'api_captura', 'ia_chat_landing', 'img_proxy', 'serve_upload',
    'conta_suspensa', 'alterar_senha', 'esqueci_senha',
}

@app.before_request
def require_db_and_auth():
    if not _db_ready and request.endpoint not in _PUBLIC_ENDPOINTS:
        return render_template('setup.html',
                               db_url_set=bool(DATABASE_URL),
                               brevo_set=bool(BREVO_API_KEY),
                               db_error=_db_error), 503
    if request.endpoint and request.endpoint not in _PUBLIC_ENDPOINTS:
        if 'user_id' not in session:
            if request.path.startswith('/api/') or request.path.startswith('/ia/'):
                return jsonify({'erro': 'Autenticação necessária'}), 401
            return redirect(url_for('login'))
        user_status = session.get('user_status')
        if user_status != 'active':
            if request.endpoint not in ('conta_suspensa', 'logout'):
                return redirect(url_for('conta_suspensa'))

@app.context_processor
def inject_user():
    ctx = {}
    if 'user_id' in session:
        ctx['current_user'] = {'id': session.get('user_id'), 'email': session.get('user_email'), 'name': session.get('user_name'), 'role': session.get('user_role')}
    else:
        ctx['current_user'] = None
    try:
        conn = get_db()
        ctx['nichos_list'] = [r['name'] for r in conn.execute('SELECT name FROM nichos ORDER BY name').fetchall()]
        conn.close()
    except Exception:
        ctx['nichos_list'] = []
    return ctx

@app.route('/setup')
def setup_page():
    return render_template('setup.html',
                           db_url_set=bool(DATABASE_URL),
                           brevo_set=bool(BREVO_API_KEY),
                           db_error=_db_error), 503

# ── Autenticação ─────────────────────────────────────────────────────────────

@app.route('/')
def landing():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        if not email or not password:
            flash('Preencha email e senha.', 'danger')
            return render_template('login.html')
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email=%s', (email,)).fetchone()
        conn.close()
        if not user or not check_password_hash(user['password_hash'], password):
            flash('Email ou senha incorretos.', 'danger')
            return render_template('login.html')
        if user['status'] != 'active':
            flash('Sua conta está suspensa. Entre em contato com o suporte.', 'warning')
            return render_template('login.html')
        session.permanent = True
        session['user_id'] = user['id']
        session['user_email'] = user['email']
        session['user_name'] = user['name']
        session['user_role'] = user['role']
        session['user_status'] = user['status']
        conn = get_db()
        conn.execute('UPDATE users SET last_login=NOW() WHERE id=%s', (user['id'],))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu da plataforma.', 'info')
    return redirect(url_for('login'))

@app.route('/conta-suspensa')
def conta_suspensa():
    return render_template('conta_suspensa.html')

@app.route('/alterar-senha', methods=['GET', 'POST'])
def alterar_senha():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        atual = request.form.get('senha_atual', '')
        nova = request.form.get('nova_senha', '')
        confirma = request.form.get('confirma_senha', '')
        if not all([atual, nova, confirma]):
            flash('Preencha todos os campos.', 'danger')
            return redirect(url_for('alterar_senha'))
        if nova != confirma:
            flash('As senhas não conferem.', 'danger')
            return redirect(url_for('alterar_senha'))
        if len(nova) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
            return redirect(url_for('alterar_senha'))
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id=%s', (session['user_id'],)).fetchone()
        if not check_password_hash(user['password_hash'], atual):
            flash('Senha atual incorreta.', 'danger')
            conn.close()
            return redirect(url_for('alterar_senha'))
        conn.execute('UPDATE users SET password_hash=%s WHERE id=%s',
                     (generate_password_hash(nova), session['user_id']))
        conn.commit()
        conn.close()
        flash('Senha alterada com sucesso!', 'success')
        return redirect(url_for('configuracoes'))
    return render_template('alterar_senha.html')

@app.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash('Informe seu email.', 'danger')
            return render_template('esqueci_senha.html')
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email=%s', (email,)).fetchone()
        if not user:
            flash('Se esse email estiver cadastrado, você receberá uma nova senha.', 'info')
            conn.close()
            return render_template('esqueci_senha.html')
        password = _generate_password()
        conn.execute('UPDATE users SET password_hash=%s WHERE id=%s',
                     (generate_password_hash(password), user['id']))
        conn.commit()
        conn.close()
        if BREVO_API_KEY:
            try:
                config = sib_api_v3_sdk.Configuration()
                config.api_key['api-key'] = BREVO_API_KEY
                api = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(config))
                html = f'''<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
                    <h2 style="color:#1AC78A">Recuperação de Senha</h2>
                    <p>Olá, <strong>{user["name"] or "cliente"}</strong>!</p>
                    <p>Sua senha do ConvertMail foi redefinida. Aqui está sua nova senha:</p>
                    <div style="background:#f5f5f5;padding:20px;border-radius:8px;margin:20px 0">
                        <p><strong>Nova senha:</strong> {password}</p>
                    </div>
                    <p>Acesse a plataforma: <a href="{APP_URL}/login" style="color:#1AC78A;font-weight:bold">{APP_URL}/login</a></p>
                    <p style="color:#999;font-size:0.85rem">Recomendamos alterar sua senha após o login.</p>
                    <hr style="border:none;border-top:1px solid #eee;margin:20px 0">
                    <p style="color:#999;font-size:0.8rem">ConvertMail — Email Marketing com IA</p>
                </div>'''
                smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                    to=[{'email': user['email'], 'name': user['name'] or user['email']}],
                    sender={'name': 'ConvertMail', 'email': 'naoresponda@convertmail.com.br'},
                    subject='ConvertMail — Sua nova senha',
                    html_content=html
                )
                api.send_transac_email(smtp_email)
            except Exception as e:
                app.logger.warning('Erro ao enviar email de recuperação: %s', e)
        flash('Se esse email estiver cadastrado, você receberá uma nova senha.', 'info')
        return render_template('esqueci_senha.html')
    return render_template('esqueci_senha.html')

# ── Webhook Hotmart ──────────────────────────────────────────────────────────

@app.route('/webhook/hotmart', methods=['POST'])
def webhook_hotmart():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'error': 'no data'}), 400

    hottok = request.headers.get('X-Hotmart-Hottok', '')
    if HOTMART_TOKEN and hottok != HOTMART_TOKEN:
        return jsonify({'error': 'invalid token'}), 403

    event = data.get('event', '')
    buyer = data.get('data', {}).get('buyer', {})
    buyer_email = buyer.get('email', '').strip().lower()
    buyer_name = buyer.get('name', '').strip()
    subscription = data.get('data', {}).get('subscription', {})
    subscription_code = subscription.get('subscriber', {}).get('code', '') or data.get('data', {}).get('subscription', {}).get('code', '')
    transaction = data.get('data', {}).get('purchase', {}).get('transaction', '')

    if not buyer_email:
        return jsonify({'error': 'no buyer email'}), 400

    conn = get_db()
    existing = conn.execute('SELECT * FROM users WHERE email=%s', (buyer_email,)).fetchone()

    if event in ('PURCHASE_APPROVED', 'PURCHASE_COMPLETE'):
        if existing:
            conn.execute("UPDATE users SET status='active', hotmart_transaction=%s, hotmart_subscription=%s WHERE email=%s",
                         (transaction, subscription_code, buyer_email))
            conn.commit()
            conn.close()
        else:
            password = _generate_password()
            conn.execute(
                "INSERT INTO users (email, password_hash, name, status, hotmart_transaction, hotmart_subscription) VALUES (%s, %s, %s, 'active', %s, %s)",
                (buyer_email, generate_password_hash(password), buyer_name, transaction, subscription_code))
            conn.commit()
            conn.close()
            _send_welcome_email(buyer_email, buyer_name, password)

    elif event in ('PURCHASE_CANCELED', 'SUBSCRIPTION_CANCELLATION', 'PURCHASE_REFUNDED', 'PURCHASE_CHARGEBACK'):
        if existing:
            conn.execute("UPDATE users SET status='suspended' WHERE email=%s", (buyer_email,))
            conn.commit()
        conn.close()

    elif event in ('PURCHASE_DELAYED', 'PURCHASE_OVERDUE'):
        if existing:
            conn.execute("UPDATE users SET status='overdue' WHERE email=%s", (buyer_email,))
            conn.commit()
        conn.close()

    elif event == 'PURCHASE_PROTEST':
        if existing:
            conn.execute("UPDATE users SET status='suspended' WHERE email=%s", (buyer_email,))
            conn.commit()
        conn.close()

    elif event == 'SUBSCRIPTION_REACTIVATION':
        if existing:
            conn.execute("UPDATE users SET status='active' WHERE email=%s", (buyer_email,))
            conn.commit()
        conn.close()

    else:
        conn.close()

    return jsonify({'ok': True}), 200

# ── Admin: Gestão de Usuários ────────────────────────────────────────────────

@app.route('/admin/usuarios')
@admin_required
def admin_usuarios():
    conn = get_db()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('admin_usuarios.html', users=users, app_url=APP_URL)

@app.route('/admin/usuarios/criar', methods=['POST'])
@admin_required
def admin_criar_usuario():
    email = request.form.get('email', '').strip().lower()
    name = request.form.get('name', '').strip()
    role = request.form.get('role', 'user')
    if not email:
        flash('Email obrigatório.', 'danger')
        return redirect(url_for('admin_usuarios'))
    conn = get_db()
    existing = conn.execute('SELECT id FROM users WHERE email=%s', (email,)).fetchone()
    if existing:
        flash('Usuário já existe.', 'warning')
        conn.close()
        return redirect(url_for('admin_usuarios'))
    password = _generate_password()
    conn.execute(
        "INSERT INTO users (email, password_hash, name, status, role) VALUES (%s, %s, %s, 'active', %s)",
        (email, generate_password_hash(password), name, role))
    conn.commit()
    conn.close()
    _send_welcome_email(email, name, password)
    flash(f'Usuário {email} criado. Senha: {password}', 'success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuarios/<int:user_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_usuario(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id=%s', (user_id,)).fetchone()
    if not user:
        flash('Usuário não encontrado.', 'danger')
        conn.close()
        return redirect(url_for('admin_usuarios'))
    new_status = 'suspended' if user['status'] == 'active' else 'active'
    conn.execute('UPDATE users SET status=%s WHERE id=%s', (new_status, user_id))
    conn.commit()
    conn.close()
    flash(f'Usuário {"suspenso" if new_status == "suspended" else "reativado"}.', 'success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuarios/<int:user_id>/resetar-senha', methods=['POST'])
@admin_required
def admin_resetar_senha(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id=%s', (user_id,)).fetchone()
    if not user:
        flash('Usuário não encontrado.', 'danger')
        conn.close()
        return redirect(url_for('admin_usuarios'))
    password = _generate_password()
    conn.execute('UPDATE users SET password_hash=%s WHERE id=%s',
                 (generate_password_hash(password), user_id))
    conn.commit()
    conn.close()
    _send_welcome_email(user['email'], user['name'], password)
    flash(f'Nova senha enviada para {user["email"]}: {password}', 'success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuarios/<int:user_id>/deletar', methods=['POST'])
@admin_required
def admin_deletar_usuario(user_id):
    conn = get_db()
    conn.execute('DELETE FROM users WHERE id=%s AND role != %s', (user_id, 'admin'))
    conn.commit()
    conn.close()
    flash('Usuário removido.', 'success')
    return redirect(url_for('admin_usuarios'))

# ── Rotas de campanhas ────────────────────────────────────────────────────────

@app.route('/dashboard')
def index():
    conn = get_db()
    campaigns = conn.execute("SELECT * FROM campaigns ORDER BY created_at DESC LIMIT 20").fetchall()
    total_contacts = conn.execute('SELECT COUNT(*) as n FROM contacts').fetchone()['n']
    blacklist_count = conn.execute('SELECT COUNT(*) as n FROM blacklist').fetchone()['n']
    hot_leads = conn.execute('SELECT COUNT(*) as n FROM contact_scores WHERE score > 50').fetchone()['n']
    sent_cadencias = conn.execute("SELECT COUNT(*) as n FROM sequence_logs WHERE status='sent'").fetchone()['n']
    sent_campanhas = conn.execute("SELECT COALESCE(SUM(sent),0) as n FROM campaigns").fetchone()['n']
    sent_total = sent_cadencias + sent_campanhas
    opens_total = conn.execute('SELECT COUNT(DISTINCT contact_email) as n FROM email_opens').fetchone()['n']
    open_rate = round(opens_total / sent_total * 100, 1) if sent_total > 0 else 0
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    sent_campanhas_mes = conn.execute(
        "SELECT COALESCE(SUM(sent),0) as n FROM campaigns WHERE created_at >= %s", (month_start,)
    ).fetchone()['n']
    sent_cadencias_mes = conn.execute(
        "SELECT COUNT(*) as n FROM sequence_logs WHERE status='sent' AND sent_at >= %s", (month_start,)
    ).fetchone()['n']
    sent_mes = sent_campanhas_mes + sent_cadencias_mes
    conn.close()
    return render_template('index.html', campaigns=campaigns,
                           total_contacts=total_contacts, blacklist_count=blacklist_count,
                           hot_leads=hot_leads, open_rate=open_rate,
                           sent_total=sent_total, sent_mes=sent_mes)

@app.route('/nova-campanha', methods=['GET', 'POST'])
def nova_campanha():
    if request.method == 'POST':
        name = request.form.get('campaign_name', '').strip()
        sender = request.form.get('sender_email', '').strip()
        subject = request.form.get('subject', '').strip()
        body_html = request.form.get('body_html', '').strip()
        send_mode = request.form.get('send_mode', 'csv')
        mailing_ids_raw = request.form.get('mailing_ids', '').strip()
        mailing_id = mailing_ids_raw.split(',')[0] if mailing_ids_raw else None
        sequence_id = request.form.get('sequence_id', '').strip() or None
        schedule_mode = request.form.get('schedule_mode', 'now')
        scheduled_at_raw = request.form.get('scheduled_at', '').strip()

        if not all([name, sender, subject, body_html]):
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('nova_campanha'))

        csv_filename = None
        contacts = []

        if send_mode == 'individual':
            import json as _json
            raw = request.form.get('ind_recipients', '').strip()
            try:
                recipients = _json.loads(raw) if raw else []
            except Exception:
                recipients = []
            # fallback para campo legado de destinatário único
            if not recipients:
                ind_email = request.form.get('ind_email', '').strip()
                ind_name = request.form.get('ind_name', '').strip()
                if ind_email:
                    recipients = [{'email': ind_email, 'name': ind_name}]
            recipients = [r for r in recipients if r.get('email', '').strip()]
            if not recipients:
                flash('Adicione pelo menos um destinatário.', 'danger')
                return redirect(url_for('nova_campanha'))
            contacts = [{'name': r.get('name', ''), 'email': r['email'], 'tags': ''} for r in recipients]
            temp_filename = f"campaign_{uuid.uuid4().hex}.csv"
            temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
            with open(temp_filepath, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['nome', 'email'])
                for r in recipients:
                    w.writerow([r.get('name', ''), r['email']])
            csv_filename = temp_filename
        elif send_mode == 'mailing':
            if not mailing_ids_raw:
                flash('Selecione pelo menos um mailing.', 'danger')
                return redirect(url_for('nova_campanha'))
            mailing_id_list = [mid.strip() for mid in mailing_ids_raw.split(',') if mid.strip()]
            if not mailing_id_list:
                flash('Selecione pelo menos um mailing.', 'danger')
                return redirect(url_for('nova_campanha'))
            emails_vistos = set()
            for mid in mailing_id_list:
                conn_m = get_db()
                ml = conn_m.execute('SELECT * FROM mailings WHERE id=%s', (mid,)).fetchone()
                if not ml:
                    conn_m.close()
                    continue
                ml_contacts = get_mailing_contacts_db(int(mid), conn_m)
                conn_m.close()
                if not ml_contacts:
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], ml['filename'])
                    if os.path.exists(filepath):
                        ml_contacts = parse_csv(filepath)
                for c in ml_contacts:
                    em = c.get('email', '').strip().lower()
                    if em and em not in emails_vistos:
                        emails_vistos.add(em)
                        contacts.append(c)
            if not contacts:
                flash('Nenhum contato encontrado nos mailings selecionados.', 'danger')
                return redirect(url_for('nova_campanha'))
        else:
            if 'csv_file' not in request.files or request.files['csv_file'].filename == '':
                flash('Selecione um arquivo CSV.', 'danger')
                return redirect(url_for('nova_campanha'))
            file = request.files['csv_file']
            if not allowed_file(file.filename):
                flash('Arquivo deve ser .csv', 'danger')
                return redirect(url_for('nova_campanha'))
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            contacts = parse_csv(filepath)
            if not contacts:
                flash('Nenhum contato válido encontrado no CSV.', 'danger')
                return redirect(url_for('nova_campanha'))
            csv_filename = filename

        is_scheduled = schedule_mode == 'scheduled' and scheduled_at_raw
        parsed_scheduled_at = None
        campaign_status = 'pending'
        if is_scheduled:
            try:
                parsed_scheduled_at = datetime.strptime(scheduled_at_raw, '%Y-%m-%dT%H:%M')
                campaign_status = 'scheduled'
            except ValueError:
                flash('Data/hora de agendamento inválida.', 'danger')
                return redirect(url_for('nova_campanha'))

        conn = get_db()
        draft_id = request.form.get('draft_id', '').strip() or None
        if draft_id:
            existing = conn.execute("SELECT id FROM campaigns WHERE id=%s AND status='draft'", (draft_id,)).fetchone()
            if existing:
                conn.execute(
                    "UPDATE campaigns SET name=%s,subject=%s,body=%s,sender_email=%s,"
                    "total_contacts=%s,status=%s,mailing_id=%s,sequence_id=%s,"
                    "scheduled_at=%s,csv_filename=%s WHERE id=%s",
                    (name, subject, body_html, sender,
                     0 if is_scheduled else len(contacts),
                     campaign_status, mailing_id, sequence_id, parsed_scheduled_at, csv_filename, draft_id))
                campaign_id = int(draft_id)
                conn.commit()
            else:
                draft_id = None
        if not draft_id:
            cur = conn.execute(
                "INSERT INTO campaigns (name,subject,body,sender_email,total_contacts,status,mailing_id,sequence_id,scheduled_at,csv_filename) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (name, subject, body_html, sender,
                 0 if is_scheduled else len(contacts),
                 campaign_status, mailing_id, sequence_id, parsed_scheduled_at, csv_filename))
            campaign_id = cur.fetchone()['id']
            conn.commit()
        conn.close()

        if is_scheduled:
            flash(f'Campanha agendada para {parsed_scheduled_at.strftime("%d/%m/%Y às %H:%M")}!', 'success')
            return redirect(url_for('campanha_detalhe', campaign_id=campaign_id))

        t = threading.Thread(target=run_campaign, args=(campaign_id, contacts, sender, subject, body_html, sequence_id), daemon=True)
        t.start()
        flash(f'Campanha iniciada! Enviando para {len(contacts)} contato(s).', 'success')
        return redirect(url_for('campanha_detalhe', campaign_id=campaign_id))

    conn = get_db()
    mailings = conn.execute('SELECT * FROM mailings ORDER BY created_at DESC').fetchall()
    sequences = conn.execute("SELECT id, name FROM sequences WHERE status='active' ORDER BY name").fetchall()
    conn.close()
    return render_template('nova_campanha.html', mailings=mailings, sequences=sequences, reutilizar=None, editar=None)

@app.route('/campanha/<int:campaign_id>')
def campanha_detalhe(campaign_id):
    conn = get_db()
    campaign = conn.execute(
        "SELECT c.*, s.name AS sequence_name FROM campaigns c "
        "LEFT JOIN sequences s ON s.id = c.sequence_id WHERE c.id=%s",
        (campaign_id,)).fetchone()
    logs = conn.execute(
        "SELECT * FROM campaign_logs WHERE campaign_id=%s ORDER BY id DESC LIMIT 200",
        (campaign_id,)).fetchall()
    camp_opens = conn.execute(
        'SELECT COUNT(DISTINCT contact_email) as n FROM email_opens WHERE campaign_id=%s', (campaign_id,)).fetchone()['n']
    camp_open_rate = round(camp_opens / campaign['sent'] * 100, 1) if campaign and campaign['sent'] > 0 else 0
    blacklisted_in_campaign = 0
    if campaign:
        log_emails = [l['contact_email'] for l in logs if l['status'] == 'sent']
        if log_emails:
            placeholders = ','.join(['%s'] * len(log_emails))
            blacklisted_in_campaign = conn.execute(
                f'SELECT COUNT(*) as n FROM blacklist WHERE email IN ({placeholders})', tuple(log_emails)
            ).fetchone()['n']
    conn.close()
    if not campaign:
        flash('Campanha não encontrada.', 'danger')
        return redirect(url_for('index'))
    return render_template('campanha_detalhe.html', campaign=campaign, logs=logs,
                           camp_open_rate=camp_open_rate, camp_opens=camp_opens,
                           blacklisted_in_campaign=blacklisted_in_campaign)

@app.route('/campanha/<int:campaign_id>/reutilizar')
def campanha_reutilizar(campaign_id):
    conn = get_db()
    campaign = conn.execute('SELECT * FROM campaigns WHERE id=%s', (campaign_id,)).fetchone()
    if not campaign:
        conn.close()
        flash('Campanha não encontrada.', 'danger')
        return redirect(url_for('index'))
    mailings = conn.execute('SELECT * FROM mailings ORDER BY created_at DESC').fetchall()
    sequences = conn.execute("SELECT id, name FROM sequences WHERE status='active' ORDER BY name").fetchall()
    conn.close()
    return render_template('nova_campanha.html', mailings=mailings, sequences=sequences, reutilizar=campaign, editar=None)

@app.route('/campanha/<int:campaign_id>/editar')
def campanha_editar(campaign_id):
    conn = get_db()
    campaign = conn.execute("SELECT * FROM campaigns WHERE id=%s AND status='draft'", (campaign_id,)).fetchone()
    if not campaign:
        conn.close()
        flash('Rascunho não encontrado ou já foi enviado.', 'danger')
        return redirect(url_for('index'))
    mailings = conn.execute('SELECT * FROM mailings ORDER BY created_at DESC').fetchall()
    sequences = conn.execute("SELECT id, name FROM sequences WHERE status='active' ORDER BY name").fetchall()
    conn.close()
    return render_template('nova_campanha.html', mailings=mailings, sequences=sequences, reutilizar=None, editar=campaign)

@app.route('/nichos')
def pagina_nichos():
    conn = get_db()
    nichos_crm = conn.execute("""
        SELECT nicho, COUNT(*) as qtd
        FROM contacts WHERE nicho IS NOT NULL AND nicho != ''
        GROUP BY nicho ORDER BY qtd DESC
    """).fetchall()
    total_com_nicho = sum(r['qtd'] for r in nichos_crm)
    total_sem_nicho = conn.execute(
        "SELECT COUNT(*) as qtd FROM contacts WHERE nicho IS NULL OR nicho=''"
    ).fetchone()['qtd']
    total_contatos = total_com_nicho + total_sem_nicho

    nichos_mailing = conn.execute("""
        SELECT COALESCE(NULLIF(c.nicho,''), NULLIF(mc.nicho,'')) as nicho,
               COUNT(DISTINCT mc.email) as qtd,
               STRING_AGG(DISTINCT m.name, ', ') as mailings
        FROM mailing_contacts mc
        LEFT JOIN contacts c ON LOWER(c.email) = LOWER(mc.email)
        LEFT JOIN mailings m ON m.id = mc.mailing_id
        WHERE COALESCE(NULLIF(c.nicho,''), NULLIF(mc.nicho,'')) IS NOT NULL
          AND COALESCE(NULLIF(c.nicho,''), NULLIF(mc.nicho,'')) != ''
        GROUP BY COALESCE(NULLIF(c.nicho,''), NULLIF(mc.nicho,''))
        ORDER BY qtd DESC
    """).fetchall()

    nichos_db = conn.execute('SELECT id, name FROM nichos ORDER BY name').fetchall()
    conn.close()
    return render_template('nichos.html',
                           nichos_crm=nichos_crm,
                           nichos_mailing=nichos_mailing,
                           nichos_db=nichos_db,
                           total_com_nicho=total_com_nicho,
                           total_sem_nicho=total_sem_nicho,
                           total_contatos=total_contatos)


@app.route('/nichos/adicionar', methods=['POST'])
@login_required
def adicionar_nicho():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Informe o nome do nicho.', 'danger')
        return redirect(url_for('pagina_nichos'))
    conn = get_db()
    existing = conn.execute('SELECT id FROM nichos WHERE name=%s', (name,)).fetchone()
    if existing:
        flash(f'Nicho "{name}" já existe.', 'warning')
    else:
        conn.execute('INSERT INTO nichos (name) VALUES (%s)', (name,))
        conn.commit()
        flash(f'Nicho "{name}" adicionado!', 'success')
    conn.close()
    return redirect(url_for('pagina_nichos'))


@app.route('/nichos/<int:nicho_id>/remover', methods=['POST'])
@login_required
def remover_nicho(nicho_id):
    conn = get_db()
    nicho = conn.execute('SELECT name FROM nichos WHERE id=%s', (nicho_id,)).fetchone()
    if nicho:
        conn.execute('DELETE FROM nichos WHERE id=%s', (nicho_id,))
        conn.commit()
        flash(f'Nicho "{nicho["name"]}" removido da lista.', 'info')
    conn.close()
    return redirect(url_for('pagina_nichos'))


@app.route('/api/nichos')
def api_nichos():
    mailing_ids = request.args.get('mailing_ids', '').strip()
    conn = get_db()

    if mailing_ids:
        id_list = [m.strip() for m in mailing_ids.split(',') if m.strip()]
        if not id_list:
            conn.close()
            return jsonify([])
        placeholders = ','.join(['%s'] * len(id_list))
        rows = conn.execute(f"""
            SELECT nicho, COUNT(DISTINCT email) as qtd FROM (
                SELECT mc.email,
                       COALESCE(NULLIF(c.nicho,''), NULLIF(mc.nicho,'')) as nicho
                FROM mailing_contacts mc
                LEFT JOIN contacts c ON LOWER(c.email) = LOWER(mc.email)
                WHERE mc.mailing_id IN ({placeholders})
            ) sub
            WHERE nicho IS NOT NULL AND nicho != ''
            GROUP BY nicho ORDER BY qtd DESC
        """, id_list).fetchall()
        total_sem_nicho = conn.execute(f"""
            SELECT COUNT(DISTINCT mc.email) as qtd
            FROM mailing_contacts mc
            LEFT JOIN contacts c ON LOWER(c.email) = LOWER(mc.email)
            WHERE mc.mailing_id IN ({placeholders})
              AND (COALESCE(NULLIF(c.nicho,''), NULLIF(mc.nicho,'')) IS NULL
                   OR COALESCE(NULLIF(c.nicho,''), NULLIF(mc.nicho,'')) = '')
        """, id_list).fetchone()
        conn.close()
        result = [{'nicho': r['nicho'], 'qtd': r['qtd']} for r in rows]
        sem_nicho = total_sem_nicho['qtd'] if total_sem_nicho else 0
        return jsonify({'nichos': result, 'sem_nicho': sem_nicho})

    rows = conn.execute(
        "SELECT nicho, COUNT(*) as qtd FROM contacts WHERE nicho IS NOT NULL AND nicho != '' "
        "GROUP BY nicho ORDER BY qtd DESC"
    ).fetchall()
    conn.close()
    return jsonify([{'nicho': r['nicho'], 'qtd': r['qtd']} for r in rows])

@app.route('/campanha/rascunho', methods=['POST'])
def campanha_rascunho():
    data = request.get_json() or {}
    nome = data.get('campaign_name', '').strip()
    sender = data.get('sender_email', '').strip()
    subject = data.get('subject', '').strip()
    body_html = data.get('body_html', '')
    mailing_ids_raw = data.get('mailing_ids', '')
    sequence_id = data.get('sequence_id') or None
    draft_id = data.get('draft_id') or None

    if not nome:
        return jsonify({'error': 'Preencha o nome da campanha.'}), 400

    conn = get_db()
    mailing_id_list = [m.strip() for m in mailing_ids_raw.split(',') if m.strip()] if mailing_ids_raw else []
    mailing_id = int(mailing_id_list[0]) if mailing_id_list else None

    total_contacts = 0
    if mailing_id_list:
        placeholders = ','.join(['%s'] * len(mailing_id_list))
        row = conn.execute(f"SELECT COUNT(DISTINCT email) as cnt FROM mailing_contacts WHERE mailing_id IN ({placeholders})", mailing_id_list).fetchone()
        total_contacts = row['cnt'] if row else 0

    if draft_id:
        existing = conn.execute("SELECT id FROM campaigns WHERE id=%s AND status='draft'", (draft_id,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE campaigns SET name=%s,subject=%s,body=%s,sender_email=%s,"
                "total_contacts=%s,mailing_id=%s,sequence_id=%s WHERE id=%s",
                (nome, subject, body_html, sender or '', total_contacts, mailing_id, sequence_id, draft_id))
            campaign_id = int(draft_id)
        else:
            draft_id = None

    if not draft_id:
        cur = conn.execute(
            "INSERT INTO campaigns (name,subject,body,sender_email,total_contacts,status,mailing_id,sequence_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (nome, subject, body_html, sender or '', total_contacts, 'draft', mailing_id, sequence_id))
        campaign_id = cur.fetchone()['id']

    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'campaign_id': campaign_id, 'url': url_for('campanha_detalhe', campaign_id=campaign_id)})

@app.route('/campanha/segmentada', methods=['POST'])
def campanha_segmentada():
    data = request.get_json() or {}
    nome_base = data.get('campaign_name', '').strip()
    sender = data.get('sender_email', '').strip()
    subject_template = data.get('subject', '').strip()
    nichos = data.get('nichos', [])
    mailing_ids_raw = data.get('mailing_ids', '')
    sequence_id = data.get('sequence_id') or None
    ia_config = data.get('ia_config', {})

    if not all([nome_base, sender, subject_template]):
        return jsonify({'error': 'Preencha nome, remetente e assunto.'}), 400
    if not nichos:
        return jsonify({'error': 'Selecione pelo menos um nicho.'}), 400

    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key or not ANTHROPIC_OK:
        return jsonify({'error': 'ANTHROPIC_API_KEY não configurada.'}), 500

    conn = get_db()

    mailing_id_list = [m.strip() for m in mailing_ids_raw.split(',') if m.strip()] if mailing_ids_raw else []

    resultados = []
    for nicho in nichos:
        contacts = []
        emails_vistos = set()

        if mailing_id_list:
            placeholders = ','.join(['%s'] * len(mailing_id_list))
            rows = conn.execute(f"""
                SELECT mc.email, mc.name, mc.tags
                FROM mailing_contacts mc
                LEFT JOIN contacts c ON LOWER(c.email) = LOWER(mc.email)
                WHERE mc.mailing_id IN ({placeholders})
                  AND LOWER(COALESCE(NULLIF(c.nicho,''), NULLIF(mc.nicho,''))) = LOWER(%s)
            """, mailing_id_list + [nicho]).fetchall()
            for r in rows:
                em = r['email'].strip().lower()
                if em and em not in emails_vistos:
                    emails_vistos.add(em)
                    contacts.append({'email': r['email'], 'name': r['name'] or '', 'tags': r['tags'] or ''})

        crm_rows = conn.execute(
            "SELECT email, name, tags FROM contacts WHERE LOWER(nicho)=LOWER(%s)", (nicho,)
        ).fetchall()
        for r in crm_rows:
            em = r['email'].strip().lower()
            if em and em not in emails_vistos:
                emails_vistos.add(em)
                contacts.append({'email': r['email'], 'name': r['name'] or '', 'tags': r['tags'] or ''})

        if not contacts:
            resultados.append({'nicho': nicho, 'status': 'sem_contatos', 'count': 0})
            continue

        subject = subject_template.replace('{nicho}', nicho)
        body_html = _gerar_email_por_nicho(api_key, nicho, ia_config, sender)

        campaign_name = f"{nome_base} — {nicho}"
        cur = conn.execute(
            "INSERT INTO campaigns (name,subject,body,sender_email,total_contacts,status,sequence_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (campaign_name, subject, body_html, sender, len(contacts), 'pending', sequence_id))
        campaign_id = cur.fetchone()['id']
        conn.commit()

        t = threading.Thread(
            target=run_campaign,
            args=(campaign_id, contacts, sender, subject, body_html, sequence_id),
            daemon=True)
        t.start()

        resultados.append({
            'nicho': nicho, 'status': 'iniciada',
            'count': len(contacts), 'campaign_id': campaign_id,
            'url': url_for('campanha_detalhe', campaign_id=campaign_id),
        })

    conn.close()
    return jsonify({'ok': True, 'campanhas': resultados})


def _gerar_email_por_nicho(api_key, nicho, ia_config, sender):
    conn_kit = get_db()
    kit_info = ''
    primary_color = '#1a3a6b'
    kit_id = ia_config.get('kit_id')
    if kit_id:
        kit = conn_kit.execute('SELECT * FROM brand_kits WHERE id=%s', (kit_id,)).fetchone()
        if kit:
            primary_color = kit['primary_color'] or '#1a3a6b'
            kit_info = f"\nKit de Marca — {kit['name']}: Tom de voz: {kit['tone_of_voice'] or 'Profissional'}, Cores: {kit['primary_color']}, {kit['secondary_color']}"
    conn_kit.close()

    publico = ia_config.get('publico', '')
    objetivo = ia_config.get('objetivo', '')
    tema = ia_config.get('tema', '')
    contexto = ia_config.get('contexto', '')

    prompt = f"""Crie um email profissional de marketing em HTML, personalizado para o nicho "{nicho}".

Público-alvo: {publico} — especificamente do nicho {nicho}
Objetivo: {objetivo}
Tema: {tema}
Contexto: {contexto}
{kit_info}

IMPORTANTE: O conteúdo deve ser 100% relevante e específico para profissionais/empresas do nicho "{nicho}".
- Use exemplos, dores e linguagem própria deste nicho
- Adapte os benefícios para a realidade do nicho
- Use terminologia que profissionais deste nicho reconheçam

Estrutura obrigatória:
1. Cabeçalho colorido ({primary_color}) com o tema
2. Saudação com {{nome}}
3. 2+ parágrafos com conteúdo específico do nicho "{nicho}"
4. Lista com 3-5 benefícios/dicas adaptados ao nicho
5. Botão CTA com href="#LINK_CTA"
6. Assinatura

Instruções:
- Retorne APENAS HTML, sem markdown, sem ```
- Email responsivo, máx 600px, inline CSS
- Use {{nome}} para personalização
- 250-400 palavras de conteúdo específico para o nicho
"""
    try:
        client = _anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=8000,
            messages=[{'role': 'user', 'content': prompt}]
        )
        html = resp.content[0].text.strip()
        html = re.sub(r'^```[a-z]*\n?', '', html)
        html = re.sub(r'\n?```$', '', html).strip()
        return html
    except Exception:
        return f'<p>Olá {{nome}},</p><p>Conteúdo para o nicho {nicho}.</p>'

@app.route('/campanha/log/<int:log_id>/deletar', methods=['POST'])
def deletar_log_campanha(log_id):
    conn = get_db()
    log = conn.execute('SELECT campaign_id FROM campaign_logs WHERE id=%s', (log_id,)).fetchone()
    campaign_id = log['campaign_id'] if log else None
    conn.execute('DELETE FROM campaign_logs WHERE id=%s', (log_id,))
    conn.commit()
    conn.close()
    flash('Registro removido do log.', 'success')
    return redirect(url_for('campanha_detalhe', campaign_id=campaign_id) if campaign_id else url_for('index'))

@app.route('/api/progresso/<int:campaign_id>')
def api_progresso(campaign_id):
    prog = campaign_progress.get(campaign_id)
    if prog: return jsonify(prog)
    conn = get_db()
    c = conn.execute("SELECT * FROM campaigns WHERE id=%s", (campaign_id,)).fetchone()
    conn.close()
    if c:
        return jsonify({'total': c['total_contacts'], 'sent': c['sent'], 'errors': c['errors'], 'status': c['status'], 'logs': []})
    return jsonify({'error': 'não encontrado'}), 404

@app.route('/api/verificar-ses')
def api_verificar_ses():
    if not BREVO_API_KEY:
        return jsonify({'ok': False, 'erro': 'BREVO_API_KEY não configurada. Adicione no Railway em Variables.'}), 500
    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = BREVO_API_KEY
        account_api = sib_api_v3_sdk.AccountApi(sib_api_v3_sdk.ApiClient(configuration))
        account = account_api.get_account()
        plan = account.plan[0] if account.plan else None
        quota_diaria = plan.credits if plan and hasattr(plan, 'credits') else 0
        return jsonify({'ok': True,
            'emails_verificados': [account.email],
            'dominios': [],
            'quota_diaria': quota_diaria,
            'enviados_hoje': 0,
            'taxa_por_segundo': 0,
            'provedor': 'Brevo',
            'conta': account.email})
    except ApiException as e:
        return jsonify({'ok': False, 'erro': f'Erro Brevo: {e.status} — {e.reason}'}), 500
    except Exception as e:
        return jsonify({'ok': False, 'erro': f'Brevo não configurado: {str(e)}'}), 500

@app.route('/configuracoes')
def configuracoes():
    conn = get_db()
    sig = conn.execute('SELECT * FROM signature ORDER BY id DESC LIMIT 1').fetchone()
    email_accounts = conn.execute('SELECT * FROM email_accounts ORDER BY id').fetchall()
    conn.close()
    return render_template('configuracoes.html', signature=sig, email_accounts=email_accounts)

@app.route('/configuracoes/assinatura', methods=['POST'])
def salvar_assinatura():
    body_html = request.form.get('sig_body', '').strip()
    name = request.form.get('sig_name', '').strip()
    sender_name = request.form.get('sender_name', '').strip() or 'ConvertMail'
    conn = get_db()
    existing = conn.execute('SELECT id FROM signature LIMIT 1').fetchone()
    if existing:
        conn.execute(
            "UPDATE signature SET name=%s,body_html=%s,sender_name=%s,updated_at=NOW() WHERE id=%s",
            (name, body_html, sender_name, existing['id']))
    else:
        conn.execute('INSERT INTO signature (name,body_html,sender_name) VALUES (%s,%s,%s)', (name, body_html, sender_name))
    conn.commit()
    conn.close()
    flash('Configuracoes salvas com sucesso!', 'success')
    return redirect(url_for('configuracoes'))

# ── Email Client (IMAP/SMTP) ──────────────────────────────────────────────────

def _get_email_account():
    conn = get_db()
    acc = conn.execute('SELECT * FROM email_accounts WHERE active=TRUE ORDER BY id LIMIT 1').fetchone()
    conn.close()
    return acc

@app.route('/configuracoes/email-account', methods=['POST'])
def salvar_email_account():
    label = request.form.get('label', 'Principal').strip()
    imap_server = request.form.get('imap_server', '').strip()
    imap_port = int(request.form.get('imap_port', 993))
    smtp_server = request.form.get('smtp_server', '').strip()
    smtp_port = int(request.form.get('smtp_port', 587))
    email_addr = request.form.get('email_addr', '').strip()
    password = request.form.get('password', '').strip()
    use_ssl = request.form.get('use_ssl') == 'on'
    account_id = request.form.get('account_id', '').strip()

    if not all([imap_server, smtp_server, email_addr, password]):
        flash('Preencha todos os campos obrigatorios.', 'danger')
        return redirect(url_for('configuracoes'))

    try:
        imap_conn = ec.imap_connect(imap_server, imap_port, email_addr, password, use_ssl)
        sent_folder = ec.detect_sent_folder(imap_conn)
        imap_conn.logout()
    except Exception as e:
        flash(f'Erro ao conectar IMAP: {e}', 'danger')
        return redirect(url_for('configuracoes'))

    conn = get_db()
    if account_id:
        conn.execute("""UPDATE email_accounts SET label=%s,imap_server=%s,imap_port=%s,
            smtp_server=%s,smtp_port=%s,email=%s,password=%s,use_ssl=%s,sent_folder=%s WHERE id=%s""",
            (label, imap_server, imap_port, smtp_server, smtp_port, email_addr, password, use_ssl, sent_folder, account_id))
    else:
        conn.execute("""INSERT INTO email_accounts (label,imap_server,imap_port,smtp_server,smtp_port,email,password,use_ssl,sent_folder)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (label, imap_server, imap_port, smtp_server, smtp_port, email_addr, password, use_ssl, sent_folder))
    conn.commit()
    conn.close()
    flash('Conta de email configurada com sucesso!', 'success')
    return redirect(url_for('configuracoes'))

@app.route('/configuracoes/email-account/<int:account_id>/deletar', methods=['POST'])
def deletar_email_account(account_id):
    conn = get_db()
    conn.execute('DELETE FROM email_accounts WHERE id=%s', (account_id,))
    conn.commit()
    conn.close()
    flash('Conta removida.', 'success')
    return redirect(url_for('configuracoes'))

@app.route('/configuracoes/email-account/testar', methods=['POST'])
def testar_email_account():
    data = request.get_json()
    try:
        imap_conn = ec.imap_connect(data['imap_server'], int(data['imap_port']),
                                     data['email'], data['password'], data.get('use_ssl', True))
        folders = ec.list_folders(imap_conn)
        imap_conn.logout()
        return jsonify({'ok': True, 'folders': folders})
    except Exception as e:
        return jsonify({'ok': False, 'erro': str(e)})

@app.route('/email/diagnostico')
def email_diagnostico():
    acc = _get_email_account()
    if not acc:
        return jsonify({'ok': False, 'erro': 'Nenhuma conta configurada'})
    try:
        imap_conn = ec.imap_connect(acc['imap_server'], acc['imap_port'],
                                     acc['email'], acc['password'], acc['use_ssl'])
        folders = ec.list_folders(imap_conn)
        folder_info = []
        for f in folders:
            try:
                status, data = imap_conn.select(f, readonly=True)
                count = int(data[0]) if status == 'OK' else 0
                folder_info.append({'name': f, 'messages': count})
            except Exception:
                folder_info.append({'name': f, 'messages': '?'})
        imap_conn.logout()
        return jsonify({'ok': True, 'email': acc['email'], 'folders': folder_info})
    except Exception as e:
        return jsonify({'ok': False, 'erro': str(e)})

@app.route('/email')
def email_hub():
    acc = _get_email_account()
    if not acc:
        flash('Configure sua conta de email em Configuracoes primeiro.', 'warning')
        return redirect(url_for('configuracoes'))
    return render_template('email_hub.html', account=acc)

@app.route('/email/inbox')
def email_inbox():
    acc = _get_email_account()
    if not acc:
        flash('Configure sua conta de email em Configuracoes primeiro.', 'warning')
        return redirect(url_for('configuracoes'))
    page = int(request.args.get('page', 1))
    order = request.args.get('order', 'desc')
    per_page = 25
    try:
        imap_conn = ec.imap_connect(acc['imap_server'], acc['imap_port'],
                                     acc['email'], acc['password'], acc['use_ssl'])
        messages, total = ec.fetch_mailbox(imap_conn, 'INBOX', page, per_page, order)
        imap_conn.logout()
    except Exception as e:
        flash(f'Erro ao conectar: {e}', 'danger')
        return redirect(url_for('configuracoes'))
    total_pages = math.ceil(total / per_page) if total else 1
    return render_template('email_inbox.html', messages=messages, page=page,
                           total_pages=total_pages, total=total, folder='INBOX',
                           account=acc, order=order)

@app.route('/email/enviados')
def email_enviados():
    acc = _get_email_account()
    if not acc:
        flash('Configure sua conta de email em Configuracoes primeiro.', 'warning')
        return redirect(url_for('configuracoes'))
    page = int(request.args.get('page', 1))
    order = request.args.get('order', 'desc')
    per_page = 25
    sent_folder = acc.get('sent_folder') or 'Sent'
    try:
        imap_conn = ec.imap_connect(acc['imap_server'], acc['imap_port'],
                                     acc['email'], acc['password'], acc['use_ssl'])
        messages, total = ec.fetch_mailbox(imap_conn, sent_folder, page, per_page, order)
        imap_conn.logout()
    except Exception as e:
        flash(f'Erro ao conectar: {e}', 'danger')
        return redirect(url_for('configuracoes'))
    total_pages = math.ceil(total / per_page) if total else 1
    return render_template('email_enviados.html', messages=messages, page=page,
                           total_pages=total_pages, total=total, folder=sent_folder,
                           account=acc, order=order)

@app.route('/email/spam')
def email_spam():
    acc = _get_email_account()
    if not acc:
        flash('Configure sua conta de email em Configuracoes primeiro.', 'warning')
        return redirect(url_for('configuracoes'))
    page = int(request.args.get('page', 1))
    order = request.args.get('order', 'desc')
    per_page = 25
    try:
        imap_conn = ec.imap_connect(acc['imap_server'], acc['imap_port'],
                                     acc['email'], acc['password'], acc['use_ssl'])
        spam_folder = ec.detect_spam_folder(imap_conn)
        messages, total = ec.fetch_mailbox(imap_conn, spam_folder, page, per_page, order)
        imap_conn.logout()
    except Exception as e:
        flash(f'Erro ao conectar: {e}', 'danger')
        return redirect(url_for('email_hub'))
    total_pages = math.ceil(total / per_page) if total else 1
    return render_template('email_spam.html', messages=messages, page=page,
                           total_pages=total_pages, total=total, folder=spam_folder,
                           account=acc, order=order)

@app.route('/email/ler/<folder>/<uid>')
def email_ler(folder, uid):
    acc = _get_email_account()
    if not acc:
        return redirect(url_for('configuracoes'))
    try:
        imap_conn = ec.imap_connect(acc['imap_server'], acc['imap_port'],
                                     acc['email'], acc['password'], acc['use_ssl'])
        msg = ec.fetch_email(imap_conn, uid, folder)
        imap_conn.logout()
    except Exception as e:
        flash(f'Erro ao ler email: {e}', 'danger')
        return redirect(url_for('email_inbox'))
    if not msg:
        flash('Email nao encontrado.', 'warning')
        return redirect(url_for('email_inbox'))
    msg['attachments'] = [dict(a, size_fmt=ec.format_size(a['size'])) for a in msg.get('attachments', [])]
    return render_template('email_ler.html', msg=msg, folder=folder, account=acc)

@app.route('/email/anexo/<folder>/<uid>/<int:index>')
def email_anexo(folder, uid, index):
    acc = _get_email_account()
    if not acc:
        return redirect(url_for('configuracoes'))
    try:
        imap_conn = ec.imap_connect(acc['imap_server'], acc['imap_port'],
                                     acc['email'], acc['password'], acc['use_ssl'])
        filename, content_type, data = ec.fetch_attachment(imap_conn, uid, index, folder)
        imap_conn.logout()
    except Exception as e:
        flash(f'Erro ao baixar anexo: {e}', 'danger')
        return redirect(url_for('email_inbox'))
    if not data:
        flash('Anexo nao encontrado.', 'warning')
        return redirect(url_for('email_inbox'))
    return Response(data, mimetype=content_type,
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'})

@app.route('/email/compor')
def email_compor():
    acc = _get_email_account()
    if not acc:
        flash('Configure sua conta de email primeiro.', 'warning')
        return redirect(url_for('configuracoes'))
    reply_uid = request.args.get('reply')
    forward_uid = request.args.get('forward')
    folder = request.args.get('folder', 'INBOX')
    prefill = {}
    if reply_uid or forward_uid:
        try:
            imap_conn = ec.imap_connect(acc['imap_server'], acc['imap_port'],
                                         acc['email'], acc['password'], acc['use_ssl'])
            orig = ec.fetch_email(imap_conn, reply_uid or forward_uid, folder)
            imap_conn.logout()
            if orig:
                body_content = orig['html_body'] or orig['text_body'].replace('\n', '<br>')
                if reply_uid:
                    prefill['to'] = orig['from_email']
                    prefill['subject'] = ('Re: ' + orig['subject']) if not orig['subject'].startswith('Re:') else orig['subject']
                    prefill['body'] = f'<br><br><blockquote style="border-left:3px solid #ccc;padding-left:12px;margin-left:0;color:#666">Em {orig["date"].strftime("%d/%m/%Y %H:%M")}, {orig["from_name"] or orig["from_email"]} escreveu:<br><br>{body_content}</blockquote>'
                    prefill['reply_to_msg_id'] = orig.get('message_id', '')
                    prefill['references'] = orig.get('references', '')
                else:
                    prefill['subject'] = ('Fwd: ' + orig['subject']) if not orig['subject'].startswith('Fwd:') else orig['subject']
                    prefill['body'] = f'<br><br>---------- Mensagem encaminhada ----------<br>De: {orig["from_name"]} &lt;{orig["from_email"]}&gt;<br>Data: {orig["date"].strftime("%d/%m/%Y %H:%M")}<br>Assunto: {orig["subject"]}<br><br>{body_content}'
        except Exception:
            pass
    return render_template('email_compor.html', account=acc, prefill=prefill)

@app.route('/email/enviar', methods=['POST'])
def email_enviar():
    acc = _get_email_account()
    if not acc:
        return redirect(url_for('configuracoes'))
    to = request.form.get('to', '').strip()
    cc = request.form.get('cc', '').strip() or None
    bcc = request.form.get('bcc', '').strip() or None
    subject = request.form.get('subject', '').strip()
    body_html = request.form.get('body_html', '')
    reply_to_msg_id = request.form.get('reply_to_msg_id', '').strip() or None
    references = request.form.get('references', '').strip() or None

    if not to or not subject:
        flash('Preencha destinatario e assunto.', 'danger')
        return redirect(url_for('email_compor'))

    attachments = request.files.getlist('attachments')
    attachments = [f for f in attachments if f.filename]

    try:
        if BREVO_API_KEY:
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = BREVO_API_KEY
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
            to_list = [{'email': addr.strip()} for addr in to.split(',')]
            params = {
                'to': to_list,
                'sender': {'email': acc['email'], 'name': get_sender_name()},
                'subject': subject,
                'html_content': body_html,
            }
            if cc:
                params['cc'] = [{'email': addr.strip()} for addr in cc.split(',')]
            if bcc:
                params['bcc'] = [{'email': addr.strip()} for addr in bcc.split(',')]
            if reply_to_msg_id:
                params['headers'] = {'In-Reply-To': reply_to_msg_id}
            email_obj = sib_api_v3_sdk.SendSmtpEmail(**params)
            api_instance.send_transac_email(email_obj)
        else:
            ec.send_email(acc['smtp_server'], acc['smtp_port'], acc['email'], acc['password'],
                          to, subject, body_html, cc=cc, bcc=bcc,
                          reply_to_msg_id=reply_to_msg_id, references=references,
                          attachments=attachments if attachments else None)
        flash('Email enviado com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao enviar: {e}', 'danger')
        return redirect(url_for('email_compor'))
    return redirect(url_for('email_enviados'))

@app.route('/email/deletar/<folder>/<uid>', methods=['POST'])
def email_deletar(folder, uid):
    acc = _get_email_account()
    if not acc:
        return jsonify({'ok': False})
    try:
        imap_conn = ec.imap_connect(acc['imap_server'], acc['imap_port'],
                                     acc['email'], acc['password'], acc['use_ssl'])
        trash_folder = ec.detect_trash_folder(imap_conn)
        folders = ec.list_folders(imap_conn)
        print(f"[EMAIL] Pastas IMAP: {folders}", flush=True)
        print(f"[EMAIL] Trash detectado: '{trash_folder}', Pasta atual: '{folder}', UID: {uid}", flush=True)
        if folder == trash_folder:
            ec.delete_email(imap_conn, uid, folder)
        else:
            ec.move_to_trash(imap_conn, uid, folder, trash_folder)
        imap_conn.logout()
        return jsonify({'ok': True})
    except Exception as e:
        print(f"[EMAIL] Erro ao deletar: {e}", flush=True)
        return jsonify({'ok': False, 'erro': str(e)})

@app.route('/email/deletar-bulk', methods=['POST'])
def email_deletar_bulk():
    acc = _get_email_account()
    if not acc:
        return jsonify({'ok': False})
    data = request.get_json()
    uids = data.get('uids', [])
    folder = data.get('folder', 'INBOX')
    if not uids:
        return jsonify({'ok': False, 'erro': 'Nenhum email selecionado'})
    try:
        imap_conn = ec.imap_connect(acc['imap_server'], acc['imap_port'],
                                     acc['email'], acc['password'], acc['use_ssl'])
        trash_folder = ec.detect_trash_folder(imap_conn)
        if folder == trash_folder:
            for uid in uids:
                ec.delete_email(imap_conn, uid, folder)
        else:
            ec.move_to_trash_bulk(imap_conn, uids, folder, trash_folder)
        imap_conn.logout()
        return jsonify({'ok': True, 'count': len(uids)})
    except Exception as e:
        return jsonify({'ok': False, 'erro': str(e)})

@app.route('/email/marcar', methods=['POST'])
def email_marcar():
    acc = _get_email_account()
    if not acc:
        return jsonify({'ok': False})
    data = request.get_json()
    uid = data.get('uid')
    folder = data.get('folder', 'INBOX')
    action = data.get('action', 'read')
    if not uid:
        return jsonify({'ok': False, 'erro': 'UID ausente'})
    try:
        imap_conn = ec.imap_connect(acc['imap_server'], acc['imap_port'],
                                     acc['email'], acc['password'], acc['use_ssl'])
        if action == 'unread':
            ec.mark_unread(imap_conn, uid, folder)
        else:
            ec.mark_read(imap_conn, uid, folder)
        imap_conn.logout()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'erro': str(e)})

@app.route('/email/unread-count')
def email_unread_count():
    acc = _get_email_account()
    if not acc:
        return jsonify({'count': 0})
    try:
        imap_conn = ec.imap_connect(acc['imap_server'], acc['imap_port'],
                                     acc['email'], acc['password'], acc['use_ssl'])
        count = ec.get_unread_count(imap_conn)
        imap_conn.logout()
        return jsonify({'count': count})
    except Exception:
        return jsonify({'count': 0})

@app.route('/email/busca')
def email_busca():
    acc = _get_email_account()
    if not acc:
        flash('Configure sua conta de email em Configuracoes primeiro.', 'warning')
        return redirect(url_for('configuracoes'))
    q = request.args.get('q', '').strip()
    field = request.args.get('field', 'all')
    folder = request.args.get('folder', 'INBOX')
    page = int(request.args.get('page', 1))
    order = request.args.get('order', 'desc')
    per_page = 25
    messages = []
    total = 0
    if q:
        try:
            imap_conn = ec.imap_connect(acc['imap_server'], acc['imap_port'],
                                         acc['email'], acc['password'], acc['use_ssl'])
            messages, total = ec.search_mailbox(imap_conn, folder, q, field, page, per_page, order)
            imap_conn.logout()
        except Exception as e:
            flash(f'Erro na busca: {e}', 'danger')
    total_pages = math.ceil(total / per_page) if total else 1
    return render_template('email_busca.html', messages=messages, page=page,
                           total_pages=total_pages, total=total, folder=folder,
                           account=acc, order=order, q=q, field=field)

@app.route('/email/lixeira')
def email_lixeira():
    acc = _get_email_account()
    if not acc:
        flash('Configure sua conta de email em Configuracoes primeiro.', 'warning')
        return redirect(url_for('configuracoes'))
    page = int(request.args.get('page', 1))
    order = request.args.get('order', 'desc')
    per_page = 25
    try:
        imap_conn = ec.imap_connect(acc['imap_server'], acc['imap_port'],
                                     acc['email'], acc['password'], acc['use_ssl'])
        trash_folder = ec.detect_trash_folder(imap_conn)
        messages, total = ec.fetch_mailbox(imap_conn, trash_folder, page, per_page, order)
        imap_conn.logout()
    except Exception as e:
        flash(f'Erro ao conectar: {e}', 'danger')
        return redirect(url_for('email_inbox'))
    total_pages = math.ceil(total / per_page) if total else 1
    return render_template('email_lixeira.html', messages=messages, page=page,
                           total_pages=total_pages, total=total, folder=trash_folder,
                           account=acc, order=order)

@app.route('/email/esvaziar-lixeira', methods=['POST'])
def email_esvaziar_lixeira():
    acc = _get_email_account()
    if not acc:
        return jsonify({'ok': False})
    try:
        imap_conn = ec.imap_connect(acc['imap_server'], acc['imap_port'],
                                     acc['email'], acc['password'], acc['use_ssl'])
        trash_folder = ec.detect_trash_folder(imap_conn)
        imap_conn.select(trash_folder)
        imap_conn.uid('store', '1:*', '+FLAGS', '\\Deleted')
        imap_conn.expunge()
        imap_conn.logout()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'erro': str(e)})

@app.route('/email/salvar-rascunho', methods=['POST'])
def email_salvar_rascunho():
    acc = _get_email_account()
    if not acc:
        return jsonify({'ok': False, 'erro': 'Conta nao configurada'})
    to = request.form.get('to', '').strip()
    subject = request.form.get('subject', '').strip()
    body_html = request.form.get('body_html', '')
    try:
        imap_conn = ec.imap_connect(acc['imap_server'], acc['imap_port'],
                                     acc['email'], acc['password'], acc['use_ssl'])
        drafts_folder = ec.detect_drafts_folder(imap_conn)
        ec.save_draft(imap_conn, acc['email'], to, subject, body_html, drafts_folder)
        imap_conn.logout()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'erro': str(e)})

@app.route('/api/contatos/buscar')
def api_contatos_buscar():
    q = request.args.get('q', '').strip().lower()
    if not q or len(q) < 2:
        return jsonify([])
    conn = get_db()
    rows = conn.execute(
        "SELECT email, name FROM contacts WHERE LOWER(email) LIKE %s OR LOWER(name) LIKE %s LIMIT 10",
        (f'%{q}%', f'%{q}%')).fetchall()
    conn.close()
    return jsonify([{'email': r['email'], 'name': r['name'] or ''} for r in rows])

@app.route('/api/assinatura')
def api_assinatura():
    conn = get_db()
    sig = conn.execute('SELECT * FROM signature ORDER BY id DESC LIMIT 1').fetchone()
    conn.close()
    return jsonify({'body_html': sig['body_html'] if sig else '', 'name': sig['name'] if sig else ''})

@app.route('/api/templates', methods=['GET', 'POST'])
def api_templates():
    conn = get_db()
    if request.method == 'POST':
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        if not name:
            conn.close()
            return jsonify({'error': 'Nome obrigatório'}), 400
        conn.execute(
            'INSERT INTO email_templates (name,category,subject,body_html) VALUES (%s,%s,%s,%s)',
            (name, data.get('category', 'Geral'), data.get('subject', ''), data.get('body_html', '')))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
    tpls = conn.execute('SELECT * FROM email_templates ORDER BY category, name').fetchall()
    conn.close()
    return jsonify([dict(t) for t in tpls])

@app.route('/upload/imagem', methods=['POST'])
def upload_imagem():
    import base64 as b64mod
    if 'imagem' not in request.files:
        return jsonify({'erro': 'Nenhum arquivo enviado'}), 400
    file = request.files['imagem']
    if file.filename == '' or not allowed_image(file.filename):
        return jsonify({'erro': 'Tipo não permitido'}), 400
    ext = file.filename.rsplit('.', 1)[1].lower()
    mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp'}
    mime = mime_map.get(ext, 'image/png')
    data = file.read()
    b64 = b64mod.b64encode(data).decode('utf-8')
    img_id = uuid.uuid4().hex
    conn = get_db()
    conn.execute('INSERT INTO uploaded_images (id, mime_type, data) VALUES (%s, %s, %s)',
                 (img_id, mime, b64))
    conn.commit()
    conn.close()
    return jsonify({'url': f'/img/{img_id}'})

@app.route('/img/<img_id>')
def serve_db_imagem(img_id):
    import base64 as b64mod
    conn = get_db()
    row = conn.execute('SELECT mime_type, data FROM uploaded_images WHERE id=%s', (img_id,)).fetchone()
    conn.close()
    if not row:
        from flask import abort
        abort(404)
    raw = b64mod.b64decode(row['data'])
    return Response(raw, mimetype=row['mime_type'],
                    headers={'Cache-Control': 'public, max-age=31536000'})

@app.route('/uploads/imagens/<path:filename>')
def serve_imagem(filename):
    return send_from_directory(IMAGES_FOLDER, filename)

# ── Tracking ──────────────────────────────────────────────────────────────────

@app.route('/track/open')
def track_open():
    email = request.args.get('email', '')
    seq_id = request.args.get('seq', type=int)
    step_num = request.args.get('step', type=int)
    camp_id = request.args.get('campaign', type=int)
    if email and (seq_id or camp_id):
        try:
            conn = get_db()
            conn.execute(
                'INSERT INTO email_opens (sequence_id,contact_email,step_number,campaign_id) VALUES (%s,%s,%s,%s)',
                (seq_id, email, step_num, camp_id))
            now = datetime.now()
            conn.execute(
                'UPDATE send_analytics SET opened_at=%s,hour_of_day=%s,day_of_week=%s'
                ' WHERE id=(SELECT id FROM send_analytics WHERE contact_email=%s AND opened_at IS NULL ORDER BY sent_at DESC LIMIT 1)',
                (now.strftime('%Y-%m-%d %H:%M:%S'), now.hour, now.weekday(), email))
            opens_count = conn.execute(
                'SELECT COUNT(*) as n FROM email_opens WHERE contact_email=%s', (email,)
            ).fetchone()['n']
            update_score(email, 5 if opens_count == 1 else 2, conn)
            if seq_id:
                log_activity(email, 'email_opened', f'Cadência {seq_id}, passo {step_num}', conn)
            else:
                log_activity(email, 'email_opened', f'Campanha {camp_id}', conn)
            score_row = conn.execute('SELECT score FROM contact_scores WHERE email=%s', (email,)).fetchone()
            if score_row and score_row['score'] >= 51:
                criar_notificacao('abertura_quente', f'{email} abriu seu email',
                                  f'Lead quente (score {score_row["score"]}) abriu {"campanha " + str(camp_id) if camp_id else "cadência " + str(seq_id)}',
                                  contact_email=email, campaign_id=camp_id)
            conn.commit()
            conn.close()
            print(f"[TRACK] Abertura registrada: {email} campaign={camp_id} seq={seq_id}", flush=True)
        except Exception as e:
            print(f"[TRACK] Erro ao registrar abertura: {e}", flush=True)
    return Response(PIXEL_GIF, mimetype='image/gif',
                    headers={'Cache-Control': 'no-cache,no-store,must-revalidate'})

@app.route('/track/click')
def track_click():
    email = request.args.get('email', '')
    seq_id = request.args.get('seq', type=int)
    step_num = request.args.get('step', type=int)
    dest_url = request.args.get('url', '')
    if email:
        try:
            conn = get_db()
            update_score(email, 10, conn)
            log_activity(email, 'link_clicked', f'Cadência {seq_id}, passo {step_num}', conn)
            criar_notificacao('clique', f'{email} clicou no seu email',
                              f'Clicou em: {dest_url[:80]}', contact_email=email)
            conn.commit()
            conn.close()
        except Exception:
            pass
    return redirect(dest_url or '/')

@app.route('/descadastrar')
def descadastrar():
    email = request.args.get('email', '')
    seq_id = request.args.get('seq', type=int)
    if email and seq_id:
        try:
            conn = get_db()
            conn.execute(
                "UPDATE sequence_contacts SET status='unsubscribed' WHERE sequence_id=%s AND contact_email=%s",
                (seq_id, email))
            add_to_blacklist(email, 'Descadastro voluntário', conn)
            update_score(email, -50, conn)
            log_activity(email, 'unsubscribed', f'Cadência {seq_id}', conn)
            conn.commit()
            conn.close()
        except Exception:
            pass
    return render_template('descadastrar.html', email=email)

# ── Cadências ─────────────────────────────────────────────────────────────────

@app.route('/cadencias')
def cadencias():
    conn = get_db()
    seqs = conn.execute('SELECT * FROM sequences ORDER BY created_at DESC').fetchall()
    result = []
    for s in seqs:
        sid = s['id']
        total = conn.execute('SELECT COUNT(*) as n FROM sequence_contacts WHERE sequence_id=%s', (sid,)).fetchone()['n']
        active = conn.execute("SELECT COUNT(*) as n FROM sequence_contacts WHERE sequence_id=%s AND status='active'", (sid,)).fetchone()['n']
        finished = conn.execute("SELECT COUNT(*) as n FROM sequence_contacts WHERE sequence_id=%s AND status='finished'", (sid,)).fetchone()['n']
        sent = conn.execute("SELECT COUNT(*) as n FROM sequence_logs WHERE sequence_id=%s AND status='sent'", (sid,)).fetchone()['n']
        opens = conn.execute('SELECT COUNT(*) as n FROM email_opens WHERE sequence_id=%s', (sid,)).fetchone()['n']
        result.append({'seq': s, 'total': total, 'active': active, 'finished': finished,
                       'open_rate': round(opens / sent * 100, 1) if sent > 0 else 0})
    conn.close()
    return render_template('cadencias.html', sequences=result)

@app.route('/cadencias/nova', methods=['GET', 'POST'])
def nova_cadencia():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        sender = request.form.get('sender_email', '').strip()
        days = request.form.getlist('step_day[]')
        subjects = request.form.getlist('step_subject[]')
        bodies = request.form.getlist('step_body[]')
        conditions = request.form.getlist('step_condition[]')
        ab_subjects_b = request.form.getlist('ab_subject_b[]')
        ab_bodies_b = request.form.getlist('ab_body_b[]')
        ab_ratios = request.form.getlist('ab_ratio[]')

        start_date = request.form.get('start_date', '').strip() or None
        ph_str = request.form.get('preferred_hour', '').strip()
        preferred_hour = int(ph_str) if ph_str.isdigit() and 0 <= int(ph_str) <= 23 else None

        if not name or not sender or not days:
            flash('Preencha nome, remetente e pelo menos um passo.', 'danger')
            return redirect(url_for('nova_cadencia'))

        conn = get_db()
        cur = conn.execute(
            'INSERT INTO sequences (name,description,sender_email,start_date,preferred_hour) VALUES (%s,%s,%s,%s,%s) RETURNING id',
            (name, description, sender, start_date, preferred_hour))
        seq_id = cur.fetchone()['id']
        for i, (day, subj, body, cond) in enumerate(zip(days, subjects, bodies, conditions), start=1):
            ab_b = ab_subjects_b[i-1] if i <= len(ab_subjects_b) else ''
            ab_bdy = ab_bodies_b[i-1] if i <= len(ab_bodies_b) else ''
            ab_r = int(ab_ratios[i-1]) if i <= len(ab_ratios) and ab_ratios[i-1].isdigit() else 50
            conn.execute(
                'INSERT INTO sequence_steps (sequence_id,step_number,day_offset,subject,body_html,condition,ab_subject_b,ab_body_b,ab_ratio) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (seq_id, i, int(day or 0), subj, body, cond or 'always', ab_b or None, ab_bdy or None, ab_r))
        conn.commit()
        conn.close()
        flash('Cadência criada!', 'success')
        return redirect(url_for('cadencia_detalhe', seq_id=seq_id))
    return render_template('nova_cadencia.html', seq=None, steps=[], editing=False)

@app.route('/cadencias/<int:seq_id>')
def cadencia_detalhe(seq_id):
    conn = get_db()
    seq = conn.execute('SELECT * FROM sequences WHERE id=%s', (seq_id,)).fetchone()
    if not seq:
        flash('Cadência não encontrada.', 'danger'); conn.close(); return redirect(url_for('cadencias'))

    steps = conn.execute('SELECT * FROM sequence_steps WHERE sequence_id=%s ORDER BY step_number', (seq_id,)).fetchall()
    raw_contacts = conn.execute(
        'SELECT sc.*, cs.score FROM sequence_contacts sc LEFT JOIN contact_scores cs ON cs.email=sc.contact_email WHERE sc.sequence_id=%s ORDER BY sc.started_at DESC LIMIT 300',
        (seq_id,)).fetchall()

    # Bulk pre-load last logs and opens to avoid N+1 queries
    _all_last_logs = conn.execute(
        'SELECT DISTINCT ON (contact_email) contact_email, step_number, status, sent_at, error_message'
        ' FROM sequence_logs WHERE sequence_id=%s ORDER BY contact_email, sent_at DESC',
        (seq_id,)).fetchall()
    last_log_by_email = {r['contact_email']: r for r in _all_last_logs}

    _all_opens = conn.execute(
        'SELECT contact_email, step_number, COUNT(*) as cnt FROM email_opens WHERE sequence_id=%s GROUP BY contact_email, step_number',
        (seq_id,)).fetchall()
    opens_by_email_step = {(r['contact_email'], r['step_number']): r['cnt'] for r in _all_opens}

    _step_fires = conn.execute(
        "SELECT current_step, MIN(next_send_at) as min_next FROM sequence_contacts"
        " WHERE sequence_id=%s AND status='active' AND next_send_at > NOW() GROUP BY current_step",
        (seq_id,)).fetchall()
    step_next_fire_map = {r['current_step']: r['min_next'] for r in _step_fires}

    total = conn.execute('SELECT COUNT(*) as n FROM sequence_contacts WHERE sequence_id=%s', (seq_id,)).fetchone()['n']
    active = conn.execute("SELECT COUNT(*) as n FROM sequence_contacts WHERE sequence_id=%s AND status='active'", (seq_id,)).fetchone()['n']
    finished = conn.execute("SELECT COUNT(*) as n FROM sequence_contacts WHERE sequence_id=%s AND status='finished'", (seq_id,)).fetchone()['n']
    sent_total = conn.execute("SELECT COUNT(*) as n FROM sequence_logs WHERE sequence_id=%s AND status='sent'", (seq_id,)).fetchone()['n']
    opens_total = conn.execute('SELECT COUNT(*) as n FROM email_opens WHERE sequence_id=%s', (seq_id,)).fetchone()['n']
    open_rate = round(opens_total / sent_total * 100, 1) if sent_total > 0 else 0

    paused_count = conn.execute(
        "SELECT COUNT(*) as n FROM sequence_contacts WHERE sequence_id=%s AND status='paused'",
        (seq_id,)).fetchone()['n']
    sent_today = conn.execute(
        "SELECT COUNT(*) as n FROM sequence_logs WHERE sequence_id=%s AND status='sent' AND sent_at >= CURRENT_DATE",
        (seq_id,)).fetchone()['n']
    _nf = conn.execute(
        """SELECT current_step, MIN(next_send_at) as next_at, COUNT(*) as cnt
           FROM sequence_contacts
           WHERE sequence_id=%s AND status='active' AND next_send_at IS NOT NULL
           GROUP BY current_step ORDER BY MIN(next_send_at) ASC LIMIT 1""",
        (seq_id,)).fetchone()
    next_fire_step = _nf['current_step'] if _nf and _nf['next_at'] else None
    _nft = _nf['next_at'] if _nf and _nf['next_at'] else None
    if _nft:
        next_fire_time = _nft.strftime('%d/%m/%Y às %H:%M') if isinstance(_nft, datetime) else str(_nft)[:16].replace('T', ' ')
    else:
        next_fire_time = None
    next_fire_count = int(_nf['cnt']) if _nf and _nf['next_at'] else 0

    # Data de referência para prever quando cada passo vai disparar
    seq_start = None
    if seq.get('start_date'):
        try:
            sd = seq['start_date']
            seq_start = (datetime.strptime(str(sd)[:10], '%Y-%m-%d')
                         if not isinstance(sd, datetime)
                         else sd.replace(hour=0, minute=0, second=0, microsecond=0))
        except Exception:
            pass
    if not seq_start:
        earliest = conn.execute(
            'SELECT MIN(started_at) as d FROM sequence_contacts WHERE sequence_id=%s',
            (seq_id,)).fetchone()
        if earliest and earliest['d']:
            d = earliest['d']
            seq_start = d if isinstance(d, datetime) else datetime.strptime(str(d)[:19], '%Y-%m-%d %H:%M:%S')
            seq_start = seq_start.replace(hour=0, minute=0, second=0, microsecond=0)
    ph = seq.get('preferred_hour')

    step_metrics = []
    for st in steps:
        sn = st['step_number']
        s_a = conn.execute(
            "SELECT COUNT(*) as n FROM sequence_logs WHERE sequence_id=%s AND step_number=%s AND status='sent' AND (ab_version='A' OR ab_version IS NULL)",
            (seq_id, sn)).fetchone()['n']
        s_b = conn.execute(
            "SELECT COUNT(*) as n FROM sequence_logs WHERE sequence_id=%s AND step_number=%s AND status='sent' AND ab_version='B'",
            (seq_id, sn)).fetchone()['n']
        o_a = conn.execute(
            'SELECT COUNT(*) as n FROM email_opens WHERE sequence_id=%s AND step_number=%s',
            (seq_id, sn)).fetchone()['n']

        predicted_date = None
        if seq_start:
            pred_dt = seq_start + timedelta(days=st['day_offset'])
            if ph is not None:
                pred_dt = pred_dt.replace(hour=int(ph), minute=0, second=0, microsecond=0)
            predicted_date = pred_dt.strftime('%d/%m/%Y às %H:%M')

        at_step = conn.execute(
            "SELECT COUNT(*) as n FROM sequence_contacts WHERE sequence_id=%s AND current_step=%s AND status='active'",
            (seq_id, sn)).fetchone()['n']
        total_sent = s_a + s_b
        if total_sent > 0 and at_step == 0:
            step_status = 'Concluído'
        elif at_step > 0:
            step_status = 'Em andamento'
        else:
            step_status = 'Aguardando'

        _fs = conn.execute(
            "SELECT MIN(sent_at) as d FROM sequence_logs WHERE sequence_id=%s AND step_number=%s AND status='sent'",
            (seq_id, sn)).fetchone()
        first_sent_date = None
        if _fs and _fs['d']:
            _fd = _fs['d']
            first_sent_date = (_fd.strftime('%d/%m/%Y') if isinstance(_fd, datetime)
                               else datetime.strptime(str(_fd)[:10], '%Y-%m-%d').strftime('%d/%m/%Y'))

        _snf = step_next_fire_map.get(sn)
        step_next_fire = ((_snf.strftime('%d/%m/%Y às %H:%M') if isinstance(_snf, datetime)
                           else str(_snf)[:16].replace('T', ' ')) if _snf else None)

        step_metrics.append({'step': st, 'sent_a': s_a, 'sent_b': s_b, 'sent_total': s_a + s_b,
                              'opens': o_a,
                              'open_rate': round(o_a / (s_a + s_b) * 100, 1) if (s_a + s_b) > 0 else 0,
                              'predicted_date': predicted_date, 'step_status': step_status,
                              'first_sent_date': first_sent_date, 'step_next_fire': step_next_fire})

    now_dt = datetime.now()
    delayed_count = 0
    contact_details = []
    for c in raw_contacts:
        email = c['contact_email']
        ll = last_log_by_email.get(email)

        ns = c['next_send_at']
        if ns:
            next_send_fmt = (ns.strftime('%d/%m/%Y às %H:%M') if isinstance(ns, datetime)
                             else str(ns)[:16].replace('T', ' '))
        else:
            next_send_fmt = None

        last_email_date = None
        last_email_status = None
        if ll:
            ld = ll['sent_at']
            last_email_date = ld.strftime('%d/%m/%Y') if isinstance(ld, datetime) else str(ld)[:10]
            if ll['status'] == 'sent':
                was_opened = opens_by_email_step.get((email, ll['step_number']), 0)
                last_email_status = 'opened' if was_opened > 0 else 'sent'
            else:
                last_email_status = 'error'

        is_delayed = False
        if c['status'] == 'active' and ns:
            ns_dt = ns if isinstance(ns, datetime) else datetime.strptime(str(ns)[:19], '%Y-%m-%d %H:%M:%S')
            if ns_dt < now_dt:
                ll_step = ll['step_number'] if ll and ll['status'] == 'sent' else 0
                if ll_step < c['current_step']:
                    is_delayed = True
                    delayed_count += 1

        contact_details.append({
            'contact': c, 'last_email_date': last_email_date,
            'last_email_status': last_email_status, 'next_send_fmt': next_send_fmt,
            'is_delayed': is_delayed,
        })

    mailings = conn.execute('SELECT * FROM mailings ORDER BY created_at DESC').fetchall()
    nd = conn.execute(
        "SELECT MIN(next_send_at) as next_dt, COUNT(*) as pending"
        " FROM sequence_contacts WHERE sequence_id=%s AND status='active' AND next_send_at > NOW()",
        (seq_id,)).fetchone()
    next_dispatch = nd['next_dt'] if nd and nd['next_dt'] else None
    pending_count = nd['pending'] if nd else 0
    next_fire_subject = next(
        (s['subject'] for s in steps if next_fire_step and s['step_number'] == next_fire_step), None)
    conn.close()
    return render_template('cadencia_detalhe.html', seq=seq, steps=steps,
                           contact_details=contact_details, delayed_count=delayed_count,
                           total=total, active=active, finished=finished,
                           sent_total=sent_total, open_rate=open_rate, step_metrics=step_metrics,
                           mailings=mailings, next_dispatch=next_dispatch, pending_count=pending_count,
                           paused_count=paused_count, sent_today=sent_today,
                           next_fire_step=next_fire_step, next_fire_time=next_fire_time,
                           next_fire_count=next_fire_count, next_fire_subject=next_fire_subject)


@app.route('/api/cadencias/<int:seq_id>/contato/<path:email>/historico')
def api_contato_historico(seq_id, email):
    conn = get_db()
    logs = conn.execute(
        'SELECT sl.*, ss.subject as step_subject FROM sequence_logs sl'
        ' LEFT JOIN sequence_steps ss ON ss.sequence_id=sl.sequence_id AND ss.step_number=sl.step_number'
        ' WHERE sl.sequence_id=%s AND sl.contact_email=%s ORDER BY sl.sent_at ASC',
        (seq_id, email)).fetchall()
    opens = conn.execute(
        'SELECT step_number, opened_at FROM email_opens WHERE sequence_id=%s AND contact_email=%s ORDER BY opened_at ASC',
        (seq_id, email)).fetchall()
    opens_by_step = {}
    for o in opens:
        oa = o['opened_at']
        opens_by_step.setdefault(o['step_number'], []).append(
            oa.isoformat() if isinstance(oa, datetime) else str(oa))
    timeline = []
    for lg in logs:
        sa = lg['sent_at']
        timeline.append({
            'step': lg['step_number'],
            'subject': lg.get('step_subject') or '',
            'status': lg['status'],
            'ab_version': lg.get('ab_version') or 'A',
            'sent_at': sa.isoformat() if isinstance(sa, datetime) else str(sa),
            'opened_at': opens_by_step.get(lg['step_number'], []),
            'error': lg.get('error_message') or '',
        })
    conn.close()
    return jsonify({'email': email, 'timeline': timeline})


@app.route('/diagnostico/cadencia/<int:seq_id>')
def diagnostico_cadencia(seq_id):
    conn = get_db()
    seq = conn.execute('SELECT * FROM sequences WHERE id=%s', (seq_id,)).fetchone()
    if not seq:
        conn.close()
        return jsonify({'error': 'Cadência não encontrada'}), 404
    now_dt = datetime.now()
    contacts = conn.execute(
        "SELECT * FROM sequence_contacts WHERE sequence_id=%s AND status='active' ORDER BY next_send_at ASC",
        (seq_id,)).fetchall()
    _last_logs = conn.execute(
        'SELECT DISTINCT ON (contact_email) contact_email, step_number, status'
        ' FROM sequence_logs WHERE sequence_id=%s ORDER BY contact_email, sent_at DESC',
        (seq_id,)).fetchall()
    last_log_map = {r['contact_email']: r for r in _last_logs}
    result = []
    for c in contacts:
        ns = c['next_send_at']
        ns_str = ns.isoformat() if isinstance(ns, datetime) else (str(ns) if ns else None)
        is_delayed = False
        overdue_h = 0
        if ns:
            ns_dt = ns if isinstance(ns, datetime) else datetime.strptime(str(ns)[:19], '%Y-%m-%d %H:%M:%S')
            if ns_dt < now_dt:
                ll = last_log_map.get(c['contact_email'])
                ll_step = ll['step_number'] if ll and ll['status'] == 'sent' else 0
                if ll_step < c['current_step']:
                    is_delayed = True
                    overdue_h = round((now_dt - ns_dt).total_seconds() / 3600, 1)
        result.append({
            'email': c['contact_email'], 'name': c['contact_name'] or '',
            'current_step': c['current_step'], 'next_send_at': ns_str,
            'is_delayed': is_delayed, 'overdue_hours': overdue_h,
        })
    conn.close()
    return jsonify({
        'seq_id': seq_id, 'name': seq['name'],
        'total_active': len(contacts),
        'delayed': sum(1 for r in result if r['is_delayed']),
        'contacts': result,
        'checked_at': now_dt.isoformat(),
    })


@app.route('/cadencias/<int:seq_id>/editar', methods=['GET', 'POST'])
def editar_cadencia(seq_id):
    conn = get_db()
    seq = conn.execute('SELECT * FROM sequences WHERE id=%s', (seq_id,)).fetchone()
    if not seq:
        flash('Cadência não encontrada.', 'danger'); conn.close(); return redirect(url_for('cadencias'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        sender = request.form.get('sender_email', '').strip()
        start_date = request.form.get('start_date', '').strip() or None
        ph_str = request.form.get('preferred_hour', '').strip()
        preferred_hour = int(ph_str) if ph_str.isdigit() and 0 <= int(ph_str) <= 23 else None
        days = request.form.getlist('step_day[]')
        subjects = request.form.getlist('step_subject[]')
        bodies = request.form.getlist('step_body[]')
        conditions = request.form.getlist('step_condition[]')
        ab_subjects_b = request.form.getlist('ab_subject_b[]')
        ab_bodies_b = request.form.getlist('ab_body_b[]')
        ab_ratios = request.form.getlist('ab_ratio[]')

        conn.execute('UPDATE sequences SET name=%s,description=%s,sender_email=%s,start_date=%s,preferred_hour=%s WHERE id=%s',
                     (name, description, sender, start_date, preferred_hour, seq_id))
        conn.execute('DELETE FROM sequence_steps WHERE sequence_id=%s', (seq_id,))
        for i, (day, subj, body, cond) in enumerate(zip(days, subjects, bodies, conditions), start=1):
            ab_b = ab_subjects_b[i-1] if i <= len(ab_subjects_b) else ''
            ab_bdy = ab_bodies_b[i-1] if i <= len(ab_bodies_b) else ''
            ab_r = int(ab_ratios[i-1]) if i <= len(ab_ratios) and ab_ratios[i-1].isdigit() else 50
            conn.execute(
                'INSERT INTO sequence_steps (sequence_id,step_number,day_offset,subject,body_html,condition,ab_subject_b,ab_body_b,ab_ratio) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (seq_id, i, int(day or 0), subj, body, cond or 'always', ab_b or None, ab_bdy or None, ab_r))
        conn.commit()
        conn.close()
        flash('Cadência atualizada!', 'success')
        return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

    steps = conn.execute('SELECT * FROM sequence_steps WHERE sequence_id=%s ORDER BY step_number', (seq_id,)).fetchall()
    conn.close()
    return render_template('nova_cadencia.html', seq=seq, steps=steps, editing=True)

@app.route('/cadencias/<int:seq_id>/adicionar-contatos', methods=['POST'])
def adicionar_contatos_cadencia(seq_id):
    conn = get_db()
    seq = conn.execute('SELECT * FROM sequences WHERE id=%s', (seq_id,)).fetchone()
    if not seq:
        conn.close(); return redirect(url_for('cadencias'))

    source = request.form.get('source', 'csv')
    tag_filter = request.form.get('tag_filter', '').strip()
    start_mode = request.form.get('start_mode', 'now')
    scheduled_at_raw = request.form.get('scheduled_at', '').strip()

    all_contacts = []
    if source == 'mailing':
        mailing_id = request.form.get('mailing_id', '').strip()
        if not mailing_id:
            flash('Selecione um mailing.', 'danger'); conn.close()
            return redirect(url_for('cadencia_detalhe', seq_id=seq_id))
        ml = conn.execute('SELECT * FROM mailings WHERE id=%s', (mailing_id,)).fetchone()
        if not ml:
            flash('Mailing não encontrado.', 'danger'); conn.close()
            return redirect(url_for('cadencia_detalhe', seq_id=seq_id))
        all_contacts = get_mailing_contacts_db(int(mailing_id), conn)
        if not all_contacts:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], ml['filename'])
            if os.path.exists(filepath):
                all_contacts = parse_csv(filepath)
        if not all_contacts:
            flash(f'Mailing "{ml["name"]}" não tem contatos. Faça o re-upload em Mailings.', 'danger')
            conn.close()
            return redirect(url_for('cadencia_detalhe', seq_id=seq_id))
    else:
        if 'csv_file' not in request.files or request.files['csv_file'].filename == '':
            flash('Selecione um arquivo CSV.', 'danger'); conn.close()
            return redirect(url_for('cadencia_detalhe', seq_id=seq_id))
        file = request.files['csv_file']
        if not allowed_file(file.filename):
            flash('Arquivo deve ser .csv', 'danger'); conn.close()
            return redirect(url_for('cadencia_detalhe', seq_id=seq_id))
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        all_contacts = parse_csv(filepath)

    if tag_filter:
        all_contacts = [c for c in all_contacts if tag_filter.lower() in (c.get('tags') or '').lower()]

    first_step = conn.execute(
        'SELECT * FROM sequence_steps WHERE sequence_id=%s ORDER BY step_number LIMIT 1',
        (seq_id,)).fetchone()
    if not first_step:
        flash('Adicione pelo menos um passo antes de importar.', 'danger'); conn.close()
        return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

    now = datetime.now()
    if start_mode == 'scheduled' and scheduled_at_raw:
        try:
            start_base = datetime.strptime(scheduled_at_raw, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Data/hora de agendamento inválida.', 'danger'); conn.close()
            return redirect(url_for('cadencia_detalhe', seq_id=seq_id))
    else:
        start_base = now
        sd = seq.get('start_date')
        if sd:
            try:
                sd_dt = datetime.strptime(str(sd)[:10], '%Y-%m-%d') if not isinstance(sd, datetime) else sd
                if sd_dt > now:
                    start_base = sd_dt
            except Exception:
                pass

    next_dt = start_base + timedelta(days=first_step['day_offset'])
    ph = seq.get('preferred_hour')
    if ph is not None:
        next_dt = next_dt.replace(hour=int(ph), minute=0, second=0, microsecond=0)
    next_send = next_dt.strftime('%Y-%m-%d %H:%M:%S')

    added = 0
    skipped_existing = 0
    skipped_blacklist = 0
    for c in all_contacts:
        if is_blacklisted(c['email'], conn):
            skipped_blacklist += 1
            continue
        existing = conn.execute(
            'SELECT id FROM sequence_contacts WHERE sequence_id=%s AND contact_email=%s',
            (seq_id, c['email'])).fetchone()
        if not existing:
            conn.execute(
                'INSERT INTO sequence_contacts (sequence_id,contact_email,contact_name,current_step,next_send_at) VALUES (%s,%s,%s,%s,%s)',
                (seq_id, c['email'], c.get('name', ''), first_step['step_number'], next_send))
            upsert_contact(c['email'], c.get('name', ''), c.get('tags', ''), conn)
            added += 1
        else:
            skipped_existing += 1

    conn.commit(); conn.close()
    extras = []
    if skipped_existing: extras.append(f'{skipped_existing} já estavam na cadência')
    if skipped_blacklist: extras.append(f'{skipped_blacklist} na blacklist')
    detail = f' ({", ".join(extras)})' if extras else ''
    if start_mode == 'scheduled' and scheduled_at_raw:
        flash(f'{added} contato(s) adicionado(s) — primeiro envio agendado para {start_base.strftime("%d/%m/%Y às %H:%M")}.{detail}',
              'success' if added > 0 else 'warning')
    else:
        flash(f'{added} contato(s) adicionado(s) à cadência.{detail}',
              'success' if added > 0 else 'warning')
    return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

@app.route('/cadencias/<int:seq_id>/processar-agora', methods=['POST'])
def processar_cadencia_agora(seq_id):
    t = threading.Thread(target=processar_cadencias, daemon=True)
    t.start()
    flash('Processamento de emails disparado — aguarde alguns segundos e recarregue.', 'info')
    return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

@app.route('/cadencias/<int:seq_id>/pausar', methods=['POST'])
def pausar_cadencia(seq_id):
    conn = get_db()
    conn.execute("UPDATE sequence_contacts SET status='paused' WHERE sequence_id=%s AND status='active'", (seq_id,))
    conn.execute("UPDATE sequences SET status='paused' WHERE id=%s", (seq_id,))
    conn.commit(); conn.close()
    flash('Cadência pausada.', 'warning')
    return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

@app.route('/cadencias/<int:seq_id>/retomar', methods=['POST'])
def retomar_cadencia(seq_id):
    conn = get_db()
    conn.execute("UPDATE sequence_contacts SET status='active' WHERE sequence_id=%s AND status='paused'", (seq_id,))
    conn.execute("UPDATE sequences SET status='active' WHERE id=%s", (seq_id,))
    conn.commit(); conn.close()
    flash('Cadência retomada.', 'success')
    return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

@app.route('/cadencias/<int:seq_id>/enviar-teste', methods=['POST'])
def enviar_teste_cadencia(seq_id):
    conn = get_db()
    seq = conn.execute('SELECT * FROM sequences WHERE id=%s', (seq_id,)).fetchone()
    if not seq:
        conn.close()
        flash('Cadência não encontrada.', 'danger')
        return redirect(url_for('cadencias'))
    step_number = int(request.form.get('step_number', 1))
    step = conn.execute(
        'SELECT * FROM sequence_steps WHERE sequence_id=%s AND step_number=%s',
        (seq_id, step_number)).fetchone()
    conn.close()
    if not step:
        flash('Passo não encontrado.', 'danger')
        return redirect(url_for('cadencia_detalhe', seq_id=seq_id))
    test_email = request.form.get('test_email', '').strip()
    test_name = request.form.get('test_name', 'Teste').strip() or 'Teste'
    if not test_email:
        flash('Informe o email de destino do teste.', 'danger')
        return redirect(url_for('cadencia_detalhe', seq_id=seq_id))
    if not BREVO_API_KEY:
        flash('BREVO_API_KEY não configurada.', 'danger')
        return redirect(url_for('cadencia_detalhe', seq_id=seq_id))
    try:
        send_email_brevo(seq['sender_email'], test_email, test_name, step['subject'], step['body_html'])
        flash(f'Teste enviado para {test_email} — Passo {step_number}: "{step["subject"]}"', 'success')
    except Exception as e:
        flash(f'Erro ao enviar teste: {e}', 'danger')
    return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

@app.route('/cadencias/<int:seq_id>/reiniciar', methods=['POST'])
def reiniciar_cadencia(seq_id):
    conn = get_db()
    seq = conn.execute('SELECT * FROM sequences WHERE id=%s', (seq_id,)).fetchone()
    if not seq:
        conn.close()
        flash('Cadência não encontrada.', 'danger')
        return redirect(url_for('cadencias'))
    first_step = conn.execute(
        'SELECT * FROM sequence_steps WHERE sequence_id=%s ORDER BY step_number ASC LIMIT 1',
        (seq_id,)).fetchone()
    if not first_step:
        conn.close()
        flash('Cadência não tem passos configurados.', 'danger')
        return redirect(url_for('cadencia_detalhe', seq_id=seq_id))
    now = datetime.now()
    next_dt = now + timedelta(days=first_step['day_offset'])
    ph = seq.get('preferred_hour') if hasattr(seq, 'get') else seq['preferred_hour'] if 'preferred_hour' in seq.keys() else None
    if ph is not None:
        next_dt = next_dt.replace(hour=int(ph), minute=0, second=0, microsecond=0)
    next_send = next_dt.strftime('%Y-%m-%d %H:%M:%S')
    conn.execute('DELETE FROM sequence_logs WHERE sequence_id=%s', (seq_id,))
    conn.execute('DELETE FROM email_opens WHERE sequence_id=%s', (seq_id,))
    conn.execute(
        "UPDATE sequence_contacts SET current_step=%s, status='active', started_at=NOW(), next_send_at=%s, finished_at=NULL WHERE sequence_id=%s",
        (first_step['step_number'], next_send, seq_id))
    conn.execute("UPDATE sequences SET status='active' WHERE id=%s", (seq_id,))
    conn.commit(); conn.close()
    flash('Cadência reiniciada do zero. Todos os contatos voltaram ao passo 1 e o histórico de envios foi limpo.', 'success')
    return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

@app.route('/cadencias/<int:seq_id>/contato/<path:email>/parar', methods=['POST'])
def parar_contato_cadencia(seq_id, email):
    conn = get_db()
    conn.execute("UPDATE sequence_contacts SET status='stopped' WHERE sequence_id=%s AND contact_email=%s", (seq_id, email))
    conn.commit(); conn.close()
    flash(f'Cadência parada para {email}.', 'info')
    return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

@app.route('/api/cadencias/<int:seq_id>/metricas')
def api_cadencia_metricas(seq_id):
    conn = get_db()
    steps = conn.execute('SELECT * FROM sequence_steps WHERE sequence_id=%s ORDER BY step_number', (seq_id,)).fetchall()
    result = []
    for st in steps:
        sn = st['step_number']
        sent = conn.execute("SELECT COUNT(*) as n FROM sequence_logs WHERE sequence_id=%s AND step_number=%s AND status='sent'", (seq_id, sn)).fetchone()['n']
        opens = conn.execute('SELECT COUNT(*) as n FROM email_opens WHERE sequence_id=%s AND step_number=%s', (seq_id, sn)).fetchone()['n']
        result.append({'step': sn, 'day_offset': st['day_offset'], 'subject': st['subject'],
                       'sent': sent, 'opens': opens,
                       'open_rate': round(opens / sent * 100, 1) if sent > 0 else 0})
    conn.close()
    return jsonify(result)

# ── CRM — Contatos ────────────────────────────────────────────────────────────

@app.route('/contatos/adicionar', methods=['POST'])
def adicionar_contato_manual():
    email = request.form.get('email', '').strip()
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    company = request.form.get('company', '').strip()
    whatsapp = request.form.get('whatsapp', '').strip()
    status = request.form.get('status', 'lead').strip()
    tags = request.form.get('tags', '').strip()
    product_interest = request.form.get('product_interest', '').strip()
    source = request.form.get('source', '').strip()
    nicho = request.form.get('nicho', '').strip()
    city = request.form.get('city', '').strip()
    state = request.form.get('state', '').strip()
    country = request.form.get('country', '').strip()
    if not email:
        flash('Email é obrigatório.', 'danger')
        return redirect(url_for('lista_contatos'))
    conn = get_db()
    existing = conn.execute('SELECT id FROM contacts WHERE email=%s', (email,)).fetchone()
    if existing:
        flash(f'{email} já existe na base.', 'warning')
        conn.close()
        return redirect(url_for('contato_perfil', email=email))
    conn.execute(
        'INSERT INTO contacts (email,name,phone,company,whatsapp,status,tags,product_interest,source,nicho,city,state,country) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        (email, name, phone, company, whatsapp or None, status or 'lead', tags, product_interest or None, source or None, nicho or None, city or None, state or None, country or None))
    conn.commit()
    conn.close()
    flash(f'Contato {email} adicionado!', 'success')
    return redirect(url_for('contato_perfil', email=email))

@app.route('/contatos')
def lista_contatos():
    conn = get_db()
    status_filter = request.args.get('status', '')
    tag_filter = request.args.get('tag', '')
    search = request.args.get('q', '')
    sort = request.args.get('sort', 'score')

    query = '''SELECT c.*, COALESCE(cs.score,0) as current_score
               FROM contacts c LEFT JOIN contact_scores cs ON cs.email=c.email WHERE 1=1'''
    params = []
    if status_filter: query += ' AND c.status=%s'; params.append(status_filter)
    if tag_filter: query += ' AND c.tags ILIKE %s'; params.append(f'%{tag_filter}%')
    if search:
        query += ' AND (c.email ILIKE %s OR c.name ILIKE %s OR c.company ILIKE %s)'
        params += [f'%{search}%', f'%{search}%', f'%{search}%']
    if sort == 'score': query += ' ORDER BY current_score DESC'
    elif sort == 'name': query += ' ORDER BY c.name ASC'
    else: query += ' ORDER BY c.created_at DESC'

    contatos = conn.execute(query, params).fetchall()
    all_tags = set()
    for c in conn.execute("SELECT tags FROM contacts WHERE tags IS NOT NULL AND tags != ''").fetchall():
        for t in c['tags'].split(','):
            if t.strip(): all_tags.add(t.strip())
    conn.close()
    return render_template('contatos.html', contatos=contatos, all_tags=sorted(all_tags),
                           status_filter=status_filter, tag_filter=tag_filter, search=search, sort=sort)

@app.route('/contatos/<path:email>', methods=['GET', 'POST'])
def contato_perfil(email):
    conn = get_db()
    contact = conn.execute(
        'SELECT c.*, COALESCE(cs.score,0) as current_score FROM contacts c LEFT JOIN contact_scores cs ON cs.email=c.email WHERE c.email=%s',
        (email,)).fetchone()
    if not contact:
        flash('Contato não encontrado.', 'danger'); conn.close(); return redirect(url_for('lista_contatos'))

    if request.method == 'POST':
        fields = ['name', 'phone', 'company', 'position', 'whatsapp', 'status', 'tags', 'notes', 'whatsapp_notes', 'product_interest', 'source', 'nicho', 'city', 'state', 'country']
        updates = {f: request.form.get(f, '').strip() for f in fields}
        conn.execute(
            "UPDATE contacts SET name=%s,phone=%s,company=%s,position=%s,whatsapp=%s,status=%s,tags=%s,notes=%s,whatsapp_notes=%s,product_interest=%s,source=%s,nicho=%s,city=%s,state=%s,country=%s,updated_at=NOW() WHERE email=%s",
            (*updates.values(), email))
        # Salva produtos adquiridos
        conn.execute('DELETE FROM contact_purchases WHERE contact_email=%s', (email,))
        for prod, dt in zip(request.form.getlist('purchase_product[]'), request.form.getlist('purchase_date[]')):
            if prod:
                conn.execute(
                    'INSERT INTO contact_purchases (contact_email,product,purchased_at) VALUES (%s,%s,%s)',
                    (email, prod, dt if dt else None))
        conn.commit()
        log_activity(email, 'contact_updated', 'Dados atualizados pelo usuário', conn)
        conn.commit()
        conn.close()
        flash('Contato atualizado!', 'success')
        return redirect(url_for('contato_perfil', email=email))

    activities = conn.execute(
        'SELECT * FROM contact_activities WHERE contact_email=%s ORDER BY created_at DESC LIMIT 50',
        (email,)).fetchall()
    cadencias_do_contato = conn.execute('''
        SELECT sc.*, s.name as seq_name FROM sequence_contacts sc
        JOIN sequences s ON s.id=sc.sequence_id WHERE sc.contact_email=%s ORDER BY sc.started_at DESC
    ''', (email,)).fetchall()
    purchases = conn.execute(
        'SELECT * FROM contact_purchases WHERE contact_email=%s ORDER BY created_at DESC',
        (email,)).fetchall()
    all_mailings = conn.execute('SELECT id, name, contact_count FROM mailings ORDER BY name').fetchall()
    contact_mailings = conn.execute(
        'SELECT m.id, m.name, m.contact_count FROM mailing_contacts mc JOIN mailings m ON m.id=mc.mailing_id WHERE mc.email=%s ORDER BY m.name',
        (email,)).fetchall()
    best_hour = get_best_send_hour(email)
    is_bl = is_blacklisted(email, conn)
    conn.close()
    return render_template('contato_perfil.html', contact=contact, activities=activities,
                           cadencias=cadencias_do_contato, purchases=purchases,
                           all_mailings=all_mailings, contact_mailings=contact_mailings,
                           best_hour=best_hour, is_blacklisted=is_bl)


@app.route('/contatos/<path:email>/mailing', methods=['POST'])
@login_required
def contato_add_mailing(email):
    mailing_id = request.form.get('mailing_id', '').strip()
    if not mailing_id:
        flash('Selecione um mailing.', 'danger')
        return redirect(url_for('contato_perfil', email=email))
    conn = get_db()
    contact = conn.execute('SELECT name, tags FROM contacts WHERE email=%s', (email,)).fetchone()
    if not contact:
        conn.close()
        flash('Contato não encontrado.', 'danger')
        return redirect(url_for('lista_contatos'))
    try:
        conn.execute(
            'INSERT INTO mailing_contacts (mailing_id, email, name, tags) VALUES (%s, %s, %s, %s) ON CONFLICT (mailing_id, email) DO NOTHING',
            (int(mailing_id), email, contact['name'] or '', contact['tags'] or ''))
        conn.execute('UPDATE mailings SET contact_count = (SELECT COUNT(*) FROM mailing_contacts WHERE mailing_id=%s) WHERE id=%s',
                     (int(mailing_id), int(mailing_id)))
        conn.commit()
        mailing = conn.execute('SELECT name FROM mailings WHERE id=%s', (int(mailing_id),)).fetchone()
        flash(f'Contato adicionado ao mailing "{mailing["name"]}"!', 'success')
        log_activity(email, 'added_to_mailing', f'Adicionado ao mailing: {mailing["name"]}', conn)
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f'Erro ao adicionar ao mailing: {e}', 'danger')
    conn.close()
    return redirect(url_for('contato_perfil', email=email))


@app.route('/contatos/<path:email>/mailing/<int:mailing_id>/remover', methods=['POST'])
@login_required
def contato_remove_mailing(email, mailing_id):
    conn = get_db()
    conn.execute('DELETE FROM mailing_contacts WHERE mailing_id=%s AND email=%s', (mailing_id, email))
    conn.execute('UPDATE mailings SET contact_count = (SELECT COUNT(*) FROM mailing_contacts WHERE mailing_id=%s) WHERE id=%s',
                 (mailing_id, mailing_id))
    conn.commit()
    mailing = conn.execute('SELECT name FROM mailings WHERE id=%s', (mailing_id,)).fetchone()
    if mailing:
        flash(f'Contato removido do mailing "{mailing["name"]}".', 'info')
        log_activity(email, 'removed_from_mailing', f'Removido do mailing: {mailing["name"]}', conn)
        conn.commit()
    conn.close()
    return redirect(url_for('contato_perfil', email=email))


# ── Tags ──────────────────────────────────────────────────────────────────────

@app.route('/tags')
def lista_tags():
    conn = get_db()
    contacts_with_tags = conn.execute("SELECT tags FROM contacts WHERE tags IS NOT NULL AND tags != ''").fetchall()
    tag_counts = {}
    for row in contacts_with_tags:
        for t in row['tags'].split(','):
            t = t.strip()
            if t: tag_counts[t] = tag_counts.get(t, 0) + 1
    conn.close()
    tags = sorted(tag_counts.items(), key=lambda x: -x[1])
    return render_template('tags.html', tags=tags)

@app.route('/tags/<path:tag>')
def contatos_por_tag(tag):
    conn = get_db()
    contatos = conn.execute(
        'SELECT c.*, COALESCE(cs.score,0) as current_score FROM contacts c LEFT JOIN contact_scores cs ON cs.email=c.email WHERE c.tags ILIKE %s',
        (f'%{tag}%',)).fetchall()
    conn.close()
    return render_template('contatos.html', contatos=contatos, all_tags=[], status_filter='',
                           tag_filter=tag, search='', sort='score', page_title=f'Tag: {tag}')

# ── Blacklist ─────────────────────────────────────────────────────────────────

@app.route('/blacklist')
def lista_blacklist():
    conn = get_db()
    entries = conn.execute('SELECT * FROM blacklist ORDER BY added_at DESC').fetchall()
    conn.close()
    return render_template('blacklist.html', entries=entries)

@app.route('/blacklist/remover/<path:email>', methods=['POST'])
def remover_blacklist(email):
    conn = get_db()
    conn.execute('DELETE FROM blacklist WHERE email=%s', (email,))
    conn.commit(); conn.close()
    flash(f'{email} removido da blacklist.', 'success')
    return redirect(url_for('lista_blacklist'))

@app.route('/blacklist/adicionar', methods=['POST'])
def adicionar_blacklist_manual():
    email = request.form.get('email', '').strip()
    reason = request.form.get('reason', 'Adicionado manualmente').strip()
    if email:
        add_to_blacklist(email, reason)
        flash(f'{email} adicionado à blacklist.', 'warning')
    return redirect(url_for('lista_blacklist'))

# ── Mailings ─────────────────────────────────────────────────────────────────

@app.route('/mailings')
def lista_mailings():
    conn = get_db()
    mailings_raw = conn.execute('SELECT * FROM mailings ORDER BY created_at DESC').fetchall()
    mailings = []
    for m in mailings_raw:
        nichos_rows = conn.execute("""
            SELECT DISTINCT COALESCE(NULLIF(c.nicho,''), NULLIF(mc.nicho,'')) as nicho
            FROM mailing_contacts mc
            LEFT JOIN contacts c ON LOWER(c.email) = LOWER(mc.email)
            WHERE mc.mailing_id=%s
              AND COALESCE(NULLIF(c.nicho,''), NULLIF(mc.nicho,'')) IS NOT NULL
              AND COALESCE(NULLIF(c.nicho,''), NULLIF(mc.nicho,'')) != ''
        """, (m['id'],)).fetchall()
        nichos_resumo = '|'.join(r['nicho'] for r in nichos_rows) if nichos_rows else ''
        row = dict(m)
        row['nichos_resumo'] = nichos_resumo
        mailings.append(row)
    conn.close()
    return render_template('mailings.html', mailings=mailings)

@app.route('/mailings/upload', methods=['POST'])
def upload_mailing():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Informe um nome para o mailing.', 'danger')
        return redirect(url_for('lista_mailings'))
    if 'csv_file' not in request.files or request.files['csv_file'].filename == '':
        flash('Selecione um arquivo CSV.', 'danger')
        return redirect(url_for('lista_mailings'))
    file = request.files['csv_file']
    if not allowed_file(file.filename):
        flash('Arquivo deve ser .csv', 'danger')
        return redirect(url_for('lista_mailings'))
    filename = f"mailing_{uuid.uuid4().hex}.csv"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    nicho_padrao = request.form.get('nicho_padrao', '').strip()
    contacts = parse_csv(filepath)
    conn = get_db()
    cur = conn.execute(
        'INSERT INTO mailings (name,filename,contact_count) VALUES (%s,%s,%s) RETURNING id',
        (name, filename, len(contacts)))
    mailing_id = cur.fetchone()['id']
    novos_no_crm = 0
    for c in contacts:
        nicho_contato = c.get('nicho', '').strip() or nicho_padrao
        conn.execute(
            'INSERT INTO mailing_contacts (mailing_id,email,name,tags,nicho) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (mailing_id,email) DO NOTHING',
            (mailing_id, c['email'], c['name'], c['tags'], nicho_contato))
        existia = conn.execute('SELECT id FROM contacts WHERE email=%s', (c['email'],)).fetchone()
        upsert_contact(c['email'], c['name'], c['tags'], conn, force_update=True,
                       phone=c.get('phone'), company=c.get('company'),
                       position=c.get('position'), notes=c.get('notes'),
                       product_interest=c.get('product_interest'),
                       source=c.get('source'), status=c.get('status'),
                       nicho=nicho_contato, city=c.get('city'),
                       state=c.get('state'), country=c.get('country'))
        if not existia:
            novos_no_crm += 1
    conn.commit()
    conn.close()
    crm_msg = f' ({novos_no_crm} novo(s) adicionado(s) ao CRM)' if novos_no_crm else ' (todos já estavam no CRM)'
    flash(f'Mailing "{name}" salvo com {len(contacts)} contatos!{crm_msg}', 'success')
    return redirect(url_for('lista_mailings'))

@app.route('/mailings/atribuir-nicho', methods=['POST'])
def atribuir_nicho_mailing():
    mailing_id = request.form.get('mailing_id')
    nicho = request.form.get('nicho', '').strip()
    sobrescrever = request.form.get('sobrescrever') == 'on'
    if not mailing_id or not nicho:
        flash('Selecione um mailing e um nicho.', 'danger')
        return redirect(url_for('lista_mailings'))
    conn = get_db()
    if sobrescrever:
        updated_mc = conn.execute(
            "UPDATE mailing_contacts SET nicho=%s WHERE mailing_id=%s RETURNING email",
            (nicho, mailing_id)).fetchall()
    else:
        updated_mc = conn.execute(
            "UPDATE mailing_contacts SET nicho=%s WHERE mailing_id=%s AND (nicho IS NULL OR nicho='') RETURNING email",
            (nicho, mailing_id)).fetchall()
    for row in updated_mc:
        if sobrescrever:
            conn.execute("UPDATE contacts SET nicho=%s WHERE email=%s", (nicho, row['email']))
        else:
            conn.execute("UPDATE contacts SET nicho=%s WHERE email=%s AND (nicho IS NULL OR nicho='')", (nicho, row['email']))
    conn.commit()
    conn.close()
    flash(f'Nicho "{nicho}" atribuído a {len(updated_mc)} contato(s).', 'success')
    return redirect(url_for('lista_mailings'))

@app.route('/mailings/<int:mailing_id>/deletar', methods=['POST'])
def deletar_mailing(mailing_id):
    conn = get_db()
    ml = conn.execute('SELECT * FROM mailings WHERE id=%s', (mailing_id,)).fetchone()
    if ml:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], ml['filename'])
        if os.path.exists(filepath):
            os.remove(filepath)
        conn.execute('DELETE FROM mailing_contacts WHERE mailing_id=%s', (mailing_id,))
        conn.execute('DELETE FROM mailings WHERE id=%s', (mailing_id,))
        conn.commit()
        flash(f'Mailing "{ml["name"]}" removido.', 'success')
    conn.close()
    return redirect(url_for('lista_mailings'))

# ── Exportar ──────────────────────────────────────────────────────────────────

def _csv_response(rows, headers, filename):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(headers)
    w.writerows(rows)
    return Response(out.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment;filename={filename}'})

@app.route('/exportar/campanhas')
def exportar_campanhas():
    conn = get_db()
    camps = conn.execute('SELECT * FROM campaigns ORDER BY created_at DESC').fetchall()
    conn.close()
    rows = [(c['id'], c['name'], c['subject'], c['sender_email'], c['total_contacts'],
             c['sent'], c['errors'], c['status'], c['created_at']) for c in camps]
    return _csv_response(rows, ['ID','Nome','Assunto','Remetente','Total','Enviados','Erros','Status','Criado em'], 'campanhas.csv')

@app.route('/exportar/cadencia/<int:seq_id>')
def exportar_cadencia(seq_id):
    conn = get_db()
    contacts = conn.execute('''
        SELECT sc.contact_email, sc.contact_name, sc.current_step, sc.status,
               sc.next_send_at, sc.started_at, sc.finished_at, COALESCE(cs.score,0) as score
        FROM sequence_contacts sc LEFT JOIN contact_scores cs ON cs.email=sc.contact_email
        WHERE sc.sequence_id=%s
    ''', (seq_id,)).fetchall()
    conn.close()
    rows = [(c['contact_email'], c['contact_name'], c['current_step'], c['status'],
             c['next_send_at'], c['started_at'], c['finished_at'], c['score']) for c in contacts]
    return _csv_response(rows, ['Email','Nome','Passo Atual','Status','Próximo Envio','Iniciado em','Finalizado em','Score'], f'cadencia_{seq_id}.csv')

@app.route('/exportar/contatos')
def exportar_contatos():
    conn = get_db()
    contatos = conn.execute(
        'SELECT c.*, COALESCE(cs.score,0) as current_score FROM contacts c LEFT JOIN contact_scores cs ON cs.email=c.email ORDER BY c.name'
    ).fetchall()
    conn.close()
    rows = [(c['email'], c['name'], c['phone'], c['company'], c['position'],
             c['status'], c['current_score'], c['tags'], c['created_at']) for c in contatos]
    return _csv_response(rows, ['Email','Nome','Telefone','Empresa','Cargo','Status','Score','Tags','Criado em'], 'contatos.csv')

# ── Dashboard analytics ────────────────────────────────────────────────────────

@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    conn = get_db()

    rows = conn.execute('''
        SELECT DATE(sent_at) as d, COUNT(*) as c FROM (
            SELECT sent_at FROM campaign_logs WHERE status='sent'
            UNION ALL
            SELECT sent_at FROM sequence_logs WHERE status='sent'
        ) AS combined
        WHERE DATE(sent_at) >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY d ORDER BY d
    ''').fetchall()
    sends_by_day = [{'date': str(r['d']), 'count': r['c']} for r in rows]

    seqs = conn.execute('''
        SELECT s.name,
            COUNT(DISTINCT sl.contact_email) as sent,
            COUNT(DISTINCT eo.contact_email) as opened
        FROM sequences s
        LEFT JOIN sequence_logs sl ON sl.sequence_id=s.id AND sl.status='sent'
        LEFT JOIN email_opens eo ON eo.sequence_id=s.id
        GROUP BY s.id, s.name ORDER BY sent DESC LIMIT 8
    ''').fetchall()
    seq_stats = [{'name': s['name'], 'sent': s['sent'], 'opened': s['opened'],
                  'rate': round(s['opened']/s['sent']*100, 1) if s['sent'] > 0 else 0} for s in seqs]

    heatmap_rows = conn.execute('''
        SELECT hour_of_day, day_of_week, COUNT(*) as cnt
        FROM send_analytics WHERE hour_of_day IS NOT NULL GROUP BY hour_of_day, day_of_week
    ''').fetchall()
    heatmap = {}
    for r in heatmap_rows:
        heatmap[f"{r['day_of_week']}-{r['hour_of_day']}"] = r['cnt']

    conn.close()
    return jsonify({'sends_by_day': sends_by_day, 'seq_stats': seq_stats, 'heatmap': heatmap})

@app.route('/calendario')
def calendario():
    return render_template('calendario.html')

@app.route('/api/calendario/eventos')
def api_calendario_eventos():
    year = request.args.get('year', type=int) or datetime.now().year
    month = request.args.get('month', type=int) or datetime.now().month
    _, days_in_month = cal_module.monthrange(year, month)
    start = datetime(year, month, 1)
    end = datetime(year, month, days_in_month, 23, 59, 59)
    conn = get_db()
    events = []
    camps = conn.execute(
        "SELECT id, name, scheduled_at, total_contacts, status FROM campaigns "
        "WHERE scheduled_at BETWEEN %s AND %s",
        (start, end)).fetchall()
    for c in camps:
        dt = c['scheduled_at']
        if dt:
            date_str = dt.strftime('%Y-%m-%d') if hasattr(dt, 'strftime') else str(dt)[:10]
            time_str = dt.strftime('%H:%M') if hasattr(dt, 'strftime') else ''
            events.append({
                'type': 'campanha',
                'title': c['name'],
                'date': date_str,
                'time': time_str,
                'count': c['total_contacts'] or 0,
                'status': c['status'],
                'id': c['id'],
                'url': url_for('campanha_detalhe', campaign_id=c['id'])
            })
    rows = conn.execute('''
        SELECT sc.sequence_id, s.name AS seq_name,
               DATE(sc.next_send_at) AS send_date, COUNT(*) AS contact_count
        FROM sequence_contacts sc
        JOIN sequences s ON s.id = sc.sequence_id
        WHERE sc.status = 'active' AND sc.next_send_at BETWEEN %s AND %s
        GROUP BY sc.sequence_id, s.name, DATE(sc.next_send_at)
    ''', (start, end)).fetchall()
    for r in rows:
        sd = r['send_date']
        date_str = sd.strftime('%Y-%m-%d') if hasattr(sd, 'strftime') else str(sd)
        events.append({
            'type': 'cadencia',
            'title': r['seq_name'],
            'date': date_str,
            'count': r['contact_count'],
            'id': r['sequence_id'],
            'url': url_for('cadencia_detalhe', seq_id=r['sequence_id'])
        })
    conn.close()
    return jsonify(events)

# ── Rotas de Prospecção ───────────────────────────────────────────────────────

@app.route('/prospeccao')
def prospeccao():
    return render_template('prospeccao.html')

@app.route('/prospeccao/extrair', methods=['POST'])
def prospeccao_extrair():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL obrigatória'}), 400
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    max_pages = max(1, min(int(data.get('max_pages', 1)), 50))
    ignorar = bool(data.get('ignorar_robots', False))
    job_id = uuid.uuid4().hex
    extraction_jobs[job_id] = {
        'status': 'starting', 'pages_done': 0,
        'total_pages': max_pages, 'leads': [],
        'msg': 'Iniciando…', 'robots_blocked': False,
    }
    threading.Thread(target=_run_extracao,
                     args=(job_id, url, max_pages, ignorar),
                     daemon=True).start()
    return jsonify({'job_id': job_id})

@app.route('/prospeccao/status/<job_id>')
def prospeccao_status(job_id):
    job = extraction_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'não encontrado'}), 404
    return jsonify(job)

@app.route('/prospeccao/info', methods=['GET'])
def prospeccao_info():
    return jsonify({
        'firecrawl_enabled': FIRECRAWL_OK and bool(FIRECRAWL_API_KEY),
        'firecrawl_ok': FIRECRAWL_OK,
        'anthropic_ok': ANTHROPIC_OK,
    })

@app.route('/prospeccao/criar-mailing', methods=['POST'])
def prospeccao_criar_mailing():
    data = request.get_json() or {}
    nome = data.get('nome', '').strip()
    leads = data.get('leads', [])
    if not nome:
        return jsonify({'error': 'Nome obrigatório'}), 400
    if not leads:
        return jsonify({'error': 'Nenhum lead selecionado'}), 400

    filename = f"mailing_{uuid.uuid4().hex}.csv"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['nome', 'email', 'telefone', 'empresa', 'cargo'])
        w.writeheader()
        for ld in leads:
            w.writerow({k: ld.get(k, '') for k in ['nome', 'email', 'telefone', 'empresa', 'cargo']})

    conn = get_db()
    cur = conn.execute(
        'INSERT INTO mailings (name,filename,contact_count) VALUES (%s,%s,%s) RETURNING id',
        (nome, filename, len(leads)))
    mid = cur.fetchone()['id']
    novos = 0
    for ld in leads:
        em = ld.get('email', '').strip().lower()
        if not em: continue
        conn.execute(
            'INSERT INTO mailing_contacts (mailing_id,email,name,tags) VALUES (%s,%s,%s,%s) ON CONFLICT (mailing_id,email) DO NOTHING',
            (mid, em, ld.get('nome', ''), ''))
        existia = conn.execute('SELECT id FROM contacts WHERE email=%s', (em,)).fetchone()
        upsert_contact(em, ld.get('nome', ''), '', conn,
                       phone=ld.get('telefone', ''),
                       company=ld.get('empresa', ''),
                       position=ld.get('cargo', ''))
        if not existia: novos += 1
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'mailing_id': mid, 'novos_crm': novos,
                    'redirect': url_for('lista_mailings')})

# ── Kit de Marca ──────────────────────────────────────────────────────────────

@app.route('/kit-marca')
def kit_marca():
    conn = get_db()
    kits = conn.execute('SELECT * FROM brand_kits ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('kit_marca.html', kits=kits)

@app.route('/kit-marca/salvar', methods=['POST'])
def salvar_kit_marca():
    kit_id = request.form.get('kit_id', '').strip()
    tone_items = request.form.getlist('tone_items')
    tone_custom = request.form.get('tone_custom', '').strip()
    tom = ', '.join(tone_items + ([tone_custom] if tone_custom else []))
    dados = (
        request.form.get('name', '').strip(),
        request.form.get('logo_url', '').strip(),
        request.form.get('slogan', '').strip(),
        request.form.get('primary_color', '#1a3a6b'),
        request.form.get('secondary_color', '#D4AF37'),
        request.form.get('accent_color', '#4361ee'),
        request.form.get('text_color', '#333333'),
        request.form.get('bg_color', '#ffffff'),
        request.form.get('font_primary', 'Arial'),
        request.form.get('font_secondary', 'Georgia'),
        tom,
        request.form.get('instagram', '').strip(),
        request.form.get('facebook', '').strip(),
        request.form.get('linkedin', '').strip(),
        request.form.get('youtube', '').strip(),
        request.form.get('whatsapp', '').strip(),
        request.form.get('website', '').strip(),
        request.form.get('signature_name', '').strip(),
        request.form.get('signature_role', '').strip(),
        request.form.get('signature_phone', '').strip(),
    )
    if not dados[0]:
        flash('Nome da empresa é obrigatório.', 'danger')
        return redirect(url_for('kit_marca'))
    conn = get_db()
    if kit_id:
        conn.execute('''UPDATE brand_kits SET name=%s,logo_url=%s,slogan=%s,primary_color=%s,
            secondary_color=%s,accent_color=%s,text_color=%s,bg_color=%s,font_primary=%s,
            font_secondary=%s,tone_of_voice=%s,instagram=%s,facebook=%s,linkedin=%s,
            youtube=%s,whatsapp=%s,website=%s,signature_name=%s,signature_role=%s,signature_phone=%s
            WHERE id=%s''', dados + (kit_id,))
        flash('Kit de marca atualizado!', 'success')
    else:
        conn.execute('''INSERT INTO brand_kits (name,logo_url,slogan,primary_color,secondary_color,
            accent_color,text_color,bg_color,font_primary,font_secondary,tone_of_voice,instagram,
            facebook,linkedin,youtube,whatsapp,website,signature_name,signature_role,signature_phone)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''', dados)
        flash('Kit de marca criado!', 'success')
    conn.commit()
    conn.close()
    return redirect(url_for('kit_marca'))

@app.route('/kit-marca/<int:kid>/deletar', methods=['POST'])
def deletar_kit_marca(kid):
    conn = get_db()
    conn.execute('DELETE FROM brand_kits WHERE id=%s', (kid,))
    conn.commit()
    conn.close()
    flash('Kit removido.', 'info')
    return redirect(url_for('kit_marca'))

@app.route('/api/brand-kits')
def api_brand_kits():
    conn = get_db()
    kits = conn.execute('SELECT * FROM brand_kits ORDER BY name').fetchall()
    conn.close()
    return jsonify([dict(k) for k in kits])

# ── Email com IA ──────────────────────────────────────────────────────────────

def _strip_base64(html):
    reps = {}
    cnt = [0]
    def _repl(m):
        key = f'__B64IMG{cnt[0]}__'
        cnt[0] += 1
        reps[key] = m.group(1)
        return f'src="{key}"'
    clean = re.sub(r'src="(data:image/[^"]+)"', _repl, html)
    return clean, reps

def _restore_base64(html, reps):
    for k, v in reps.items():
        html = html.replace(k, v)
    return html


def _extrair_cor_template(template_html):
    """Extract the primary header color from a template's HTML.
    Skips near-white/near-gray backgrounds (body, card) and returns
    the first saturated color (the header bar)."""
    if not template_html:
        return None
    for m in re.finditer(r'background:\s*(#[0-9a-fA-F]{3,8})', template_html[:2000]):
        hexc = m.group(1).lstrip('#')
        if len(hexc) == 3:
            hexc = ''.join(c * 2 for c in hexc)
        if len(hexc) < 6:
            continue
        r, g, b = int(hexc[0:2], 16), int(hexc[2:4], 16), int(hexc[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        if luminance < 0.75:
            return m.group(1)
    return None


def _texto_para_email_html(texto, template_html='', primary_color='#1a3a6b', tema='',
                           kit=None, imagem_url='', imagem_posicao='top'):
    """Convert plain text into a structured HTML email WITHOUT using AI.
    Every word of the user's text is preserved verbatim."""

    # --- Color precedence: kit > primary_color param > template extraction > default ---
    if kit and kit.get('primary_color'):
        cor = kit['primary_color']
    elif primary_color and primary_color != '#1a3a6b':
        cor = primary_color
    else:
        cor = _extrair_cor_template(template_html) or primary_color

    # Kit colors with fallbacks
    cor_texto = (kit.get('text_color') if kit else None) or '#333333'
    cor_fundo = (kit.get('bg_color') if kit else None) or '#f0f2f5'
    cor_accent = (kit.get('accent_color') if kit else None) or cor
    fonte_principal = (kit.get('font_primary') if kit else None) or 'Arial'
    fonte_stack = f'{fonte_principal},Helvetica,sans-serif'

    # Compute tinted backgrounds from the primary color
    def _tint(hex_color, factor):
        try:
            h = hex_color.lstrip('#')
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f'#{int(r+factor*(255-r)):02x}{int(g+factor*(255-g)):02x}{int(b+factor*(255-b)):02x}'
        except (ValueError, IndexError):
            return '#eeeeee'

    cor_bg = _tint(cor, 0.93)
    cor_border_light = _tint(cor, 0.70)
    cor_subtle = _tint(cor, 0.85)

    # --- Kit de marca info ---
    empresa = 'Empresa'
    assinatura_nome = ''
    assinatura_cargo = ''
    social_links = ''
    if kit:
        empresa = kit.get('name') or kit.get('signature_name') or 'Empresa'
        assinatura_nome = kit.get('signature_name', '')
        assinatura_cargo = kit.get('signature_role', '')
        links = []
        for rede, emoji in [('instagram','📸'), ('facebook','📘'), ('linkedin','💼'),
                            ('whatsapp','📱'), ('website','🌐')]:
            url = kit.get(rede, '')
            if url:
                if not url.startswith('http'):
                    url = 'https://' + url
                links.append(f'<a href="{url}" style="text-decoration:none;font-size:18px;margin:0 4px;">{emoji}</a>')
        social_links = ' '.join(links)

    # --- Strip HTML tags if content came from rich editor ---
    if '<' in texto and '>' in texto:
        texto = re.sub(r'<br\s*/?>', '\n', texto, flags=re.I)
        texto = re.sub(r'</(p|div|tr|li|h[1-6])>', '\n\n', texto, flags=re.I)
        texto = re.sub(r'<[^>]+>', '', texto)
        import html as _html_mod
        texto = _html_mod.unescape(texto)

    # --- Parse text into blocks ---
    texto = texto.strip()
    texto = texto.replace('\r\n', '\n').replace('\r', '\n')

    assunto_extraido = ''
    if texto.lower().startswith('assunto:'):
        first_nl = texto.find('\n')
        if first_nl > 0:
            assunto_extraido = texto[len('assunto:'):first_nl].strip()
            texto = texto[first_nl:].strip()
    titulo_header = tema or assunto_extraido or empresa

    raw_blocks = re.split(r'\n\s*\n', texto)
    blocks = [b.strip() for b in raw_blocks if b.strip()]

    # --- Classify and render each block ---
    content_parts = []
    found_cta = False
    heading_count = 0

    for idx, block in enumerate(blocks):
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if not lines:
            continue
        first = lines[0]

        # Detect markdown link — CTA button
        md_link = re.search(r'\[([^\]]+)\]\(([^)]+)\)', block)
        if md_link and len(block) < 300 and block.count('\n') < 2:
            link_text = md_link.group(1)
            link_url = md_link.group(2)
            before = block[:md_link.start()].strip()
            after = block[md_link.end():].strip()
            if before:
                content_parts.append(f'<p style="font-size:15px;color:{cor_texto};line-height:1.7;margin:0 0 12px;">{_esc(before)}</p>')
            content_parts.append(
                f'<div style="text-align:center;margin:28px 0;">'
                f'<a href="{_esc(link_url)}" style="background:{cor_accent};color:#fff;padding:14px 36px;'
                f'border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;'
                f'display:inline-block;box-shadow:0 3px 8px {cor_accent}44;">'
                f'{_esc(link_text)} &rarr;</a></div>')
            if after:
                content_parts.append(f'<p style="font-size:15px;color:{cor_texto};line-height:1.7;margin:12px 0 0;">{_esc(after)}</p>')
            found_cta = True
            continue

        # Detect plain URL on its own line
        if len(lines) == 1 and re.match(r'^https?://\S+$', first):
            content_parts.append(
                f'<div style="text-align:center;margin:28px 0;">'
                f'<a href="{_esc(first)}" style="background:{cor_accent};color:#fff;padding:14px 36px;'
                f'border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;'
                f'display:inline-block;box-shadow:0 3px 8px {cor_accent}44;">'
                f'Acessar &rarr;</a></div>')
            found_cta = True
            continue

        # Detect greeting (first or second block)
        if idx <= 1 and re.match(r'^(oi|olá|hey|hi|bom dia|boa tarde|boa noite)\b', first, re.I):
            content_parts.append(
                f'<p style="font-size:16px;color:{cor_texto};line-height:1.7;margin:0 0 18px;">'
                + '<br>'.join(_esc(l) for l in lines) + '</p>')
            continue

        # Detect signature block
        if re.match(r'^(um abraço|atenciosamente|abraços|cordialmente|att|com carinho|saudações)', first, re.I):
            sig_html = '<br>'.join(
                f'<strong>{_esc(l)}</strong>' if i > 0 and len(l) < 80 else _esc(l)
                for i, l in enumerate(lines))
            content_parts.append(
                f'<div style="border-top:2px solid {cor_border_light};padding-top:20px;margin-top:28px;">'
                f'<p style="font-size:15px;color:{cor_texto};line-height:1.7;margin:0;">{sig_html}</p></div>')
            continue

        # Detect list: 3+ lines, each moderate length
        is_list = False
        if len(lines) >= 3:
            bullet_chars = ('-', '•', '*', '–', '✅', '📅', '⏰', '🌐', '📸', '📘', '💼', '📱')
            has_bullets = all(any(l.startswith(b) for b in bullet_chars) for l in lines)
            if has_bullets:
                is_list = True
            elif all(20 < len(l) < 200 for l in lines):
                starts_with_verb = sum(1 for l in lines
                                       if re.match(r'^(Como|Ferramentas|Plataformas|Aplicativos|'
                                                   r'Landing|Chatbots|Calculadoras|Sistemas|Pequenos|'
                                                   r'Acesso|Trinta|O eBook|O eBook|Acesso)', l))
                if starts_with_verb >= len(lines) * 0.5:
                    is_list = True
                elif not any(l.endswith(('.', '!', '?')) for l in lines[:-1]):
                    is_list = True

        if is_list:
            list_items = []
            for l in lines:
                for b in ('-', '•', '*', '–'):
                    if l.startswith(b + ' '):
                        l = l[2:].strip()
                        break
                list_items.append(
                    f'<li style="margin-bottom:10px;padding-left:4px;">'
                    f'<span style="color:{cor};font-weight:bold;margin-right:6px;">&#10003;</span>'
                    f'{_esc(l)}</li>')
            content_parts.append(
                f'<div style="background:{cor_bg};border-left:4px solid {cor};'
                f'border-radius:0 8px 8px 0;padding:18px 18px 8px 10px;margin:16px 0 20px;">'
                f'<ul style="padding-left:16px;color:{cor_texto};font-size:15px;line-height:1.7;'
                f'margin:0;list-style:none;">'
                + ''.join(list_items) + '</ul></div>')
            continue

        # Detect heading: single short line without sentence-ending punctuation
        if (len(lines) == 1 and len(first) < 120
                and not first.endswith(('.', '!', '?', ',', ';'))
                and not re.match(r'^(oi|olá|hey)\b', first, re.I)):
            heading_count += 1
            content_parts.append(
                f'<div style="background:{cor_bg};border-left:4px solid {cor};'
                f'border-radius:0 8px 8px 0;padding:12px 18px;margin:28px 0 14px;">'
                f'<h3 style="color:{cor};font-size:17px;margin:0;font-weight:bold;">'
                f'{_esc(first)}</h3></div>')
            continue

        # Detect info block (Data: / Horário: / Formato: lines)
        if all(':' in l and len(l) < 100 for l in lines):
            info = '<br>'.join(f'<strong>{_esc(l.split(":",1)[0])}:</strong>{_esc(l.split(":",1)[1])}'
                               for l in lines)
            content_parts.append(
                f'<div style="background:{cor_subtle};border-left:4px solid {cor};'
                f'padding:18px 20px;border-radius:0 8px 8px 0;margin:16px 0;font-size:15px;'
                f'line-height:1.8;">{info}</div>')
            continue

        # Default: paragraph(s)
        for l in lines:
            content_parts.append(
                f'<p style="font-size:15px;color:{cor_texto};line-height:1.7;margin:0 0 14px;">{_esc(l)}</p>')

    img_tag = ''
    if imagem_url:
        img_tag = (f'<div style="text-align:center;margin:16px 0;">'
                   f'<img src="{_esc(imagem_url)}" alt="imagem" '
                   f'style="max-width:100%;border-radius:8px;"></div>')

    if img_tag and imagem_posicao == 'after_first' and len(content_parts) > 0:
        content_parts.insert(1, img_tag)
        img_tag = ''
    elif img_tag and imagem_posicao == 'bottom':
        content_parts.append(img_tag)
        img_tag = ''

    body_html = '\n'.join(content_parts)

    subtitle_html = ''
    if assunto_extraido and tema:
        subtitle_html = f'<p style="color:{cor_border_light};margin:8px 0 0;font-size:13px;">{_esc(assunto_extraido)}</p>'

    html = f'''<!DOCTYPE html><html><body style="margin:0;padding:20px;background:{cor_fundo};font-family:{fonte_stack};">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table cellpadding="0" cellspacing="0" style="width:100%;max-width:560px;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,.1);">
<tr><td style="background:{cor};padding:32px 32px 28px;text-align:center;">
  <h1 style="color:#fff;margin:0;font-size:22px;font-weight:bold;word-wrap:break-word;">{_esc(titulo_header)}</h1>
  {subtitle_html}
</td></tr>
<tr><td style="padding:32px 32px;color:{cor_texto};word-wrap:break-word;overflow-wrap:break-word;font-family:{fonte_stack};">
  {img_tag}
  {body_html}
</td></tr>
<tr><td style="background:{cor_bg};padding:20px 32px;text-align:center;font-size:12px;color:#888;">
  {social_links + '<br>' if social_links else ''}
  &copy; 2025 {_esc(empresa)} &middot; <a href="#" style="color:#888;">Descadastrar</a>
</td></tr>
</table></td></tr></table></body></html>'''
    return html


def _esc(text):
    """Escape HTML special characters in text."""
    return (text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                .replace('"', '&quot;'))


@app.route('/ia/gerar-email', methods=['POST'])
def ia_gerar_email():
    if not ANTHROPIC_OK:
        return jsonify({'erro': 'Anthropic SDK não instalado.'}), 500
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return jsonify({'erro': 'ANTHROPIC_API_KEY não configurada no Railway.'}), 500

    dados = request.get_json() or {}
    kit = None
    kit_info = ''
    primary_color = '#1a3a6b'
    kit_id = dados.get('kit_id')
    if kit_id:
        conn = get_db()
        kit = conn.execute('SELECT * FROM brand_kits WHERE id=%s', (kit_id,)).fetchone()
        conn.close()
        if kit:
            primary_color = kit['primary_color'] or '#1a3a6b'
            social = ', '.join(filter(None, [
                f"Instagram: {kit['instagram']}" if kit['instagram'] else '',
                f"Facebook: {kit['facebook']}" if kit['facebook'] else '',
                f"LinkedIn: {kit['linkedin']}" if kit['linkedin'] else '',
                f"WhatsApp: {kit['whatsapp']}" if kit['whatsapp'] else '',
                f"Site: {kit['website']}" if kit['website'] else '',
            ]))
            kit_info = f"""
Kit de Marca — {kit['name']}:
- Slogan: {kit['slogan'] or ''}
- Cores: primária {kit['primary_color']}, secundária {kit['secondary_color']}, destaque {kit['accent_color']}, texto {kit['text_color']}, fundo {kit['bg_color']}
- Fontes: {kit['font_primary']} (principal), {kit['font_secondary']} (secundária)
- Tom de voz: {kit['tone_of_voice'] or 'Profissional'}
- Redes sociais: {social or 'não informado'}
- Assinatura: {kit['signature_name'] or ''} — {kit['signature_role'] or ''} | {kit['signature_phone'] or ''}
"""

    imagem_info = ''
    imagem_url = dados.get('imagem_url', '').strip()
    imagem_posicao = dados.get('imagem_posicao', 'top')
    if imagem_url:
        pos_label = {'top': 'no topo, antes do texto', 'after_first': 'após o primeiro parágrafo', 'bottom': 'no final, após o texto'}.get(imagem_posicao, 'no topo')
        imagem_info = f'\nInserir uma imagem {pos_label} do email usando exatamente esta tag: <img src="__IMAGEM_PLACEHOLDER__" alt="imagem" style="max-width:100%;border-radius:8px;margin:16px 0;">'

    modo = dados.get('modo_texto', 'reescrever')
    template_ref = dados.get('template_ref_html', '').strip()

    if modo == 'manter':
        conteudo_usuario = dados.get('contexto', '').strip()
        if not conteudo_usuario:
            return jsonify({'erro': 'Cole seu conteúdo no campo de texto.'}), 400
        html = _texto_para_email_html(
            conteudo_usuario,
            template_html=template_ref,
            primary_color=primary_color,
            tema=dados.get('tema', ''),
            kit=dict(kit) if kit else None,
            imagem_url=imagem_url,
            imagem_posicao=dados.get('imagem_posicao', 'top'),
        )
        return jsonify({'html': html})
    else:
        prompt = f"""Crie um email profissional de marketing em HTML, com conteúdo RICO, ESPECÍFICO e APROFUNDADO — nada de texto genérico ou raso.

Público-alvo: {dados.get('publico', '')}
Faixa etária: {dados.get('faixa_etaria', '')}
Nível de conhecimento: {dados.get('nivel', '')}
Objetivo: {dados.get('objetivo', '')}
Tema: {dados.get('tema', '')}
Contexto: {dados.get('contexto', '')}
Resultado esperado: {dados.get('resultado', '')}
Formato: {dados.get('formato', '')}
{kit_info}{imagem_info}

Estrutura de conteúdo obrigatória (adapte a redação ao tema e ao tom de voz, mas siga esta profundidade):
1. Cabeçalho colorido com o nome da marca/tema do email
2. Saudação personalizada com {{nome}} + abertura que conecte imediatamente com a dor, desejo ou contexto do público
3. Parágrafo(s) de desenvolvimento (pelo menos 2) explicando o "porquê" e o "como" do tema, com exemplos concretos, dados ou cenários — não apenas afirmações genéricas
4. Uma lista (<ul>/<ol>) com 3 a 5 itens (benefícios, passos, dicas ou erros comuns) relacionados ao tema, cada item com uma frase explicativa, não só um título
5. Quando o objetivo permitir, inclua um bloco de prova social/autoridade (depoimento, dado numérico ou resultado) coerente com o tema
6. Botão CTA em destaque, com texto persuasivo específico ao objetivo, href="#LINK_CTA"
7. Pós-CTA: um parágrafo de reforço (P.S. ou observação extra) com senso de urgência, benefício extra ou convite à resposta
8. Assinatura pessoal (nome + cargo) coerente com o kit de marca, se houver
9. Rodapé com nome da empresa e redes sociais como emojis clicáveis

Instruções obrigatórias:
- Retorne APENAS o código HTML, sem explicações, sem markdown, sem blocos ```
- Email responsivo, largura 100%% com max-width 560px, centralizado (use style="width:100%%;max-width:560px" em vez de width="560")
- Use SOMENTE inline CSS (style="...") — nenhuma tag <style> ou <link>
- Cabeçalho colorido com a cor primária {primary_color}
- Use {{nome}} onde o destinatário deve ser personalizado
- O corpo do email deve ter o equivalente a 250-400 palavras de texto corrido, com profundidade real — evite frases genéricas como "Temos uma novidade incrível para você"
- Varie a formatação visual (parágrafos, lista, bloco de destaque) para facilitar a leitura
"""

    try:
        client = _anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=8000,
            messages=[{'role': 'user', 'content': prompt}]
        )
        html = resp.content[0].text.strip()
        html = re.sub(r'^```[a-z]*\n?', '', html)
        html = re.sub(r'\n?```$', '', html).strip()
        if imagem_url:
            html = html.replace('__IMAGEM_PLACEHOLDER__', imagem_url)
        return jsonify({'html': html})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/ia/melhorar-texto', methods=['POST'])
def ia_melhorar_texto():
    if not ANTHROPIC_OK:
        return jsonify({'erro': 'Anthropic SDK não instalado.'}), 500
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return jsonify({'erro': 'ANTHROPIC_API_KEY não configurada no Railway.'}), 500

    dados = request.get_json() or {}
    html = dados.get('html', '').strip()
    if not html:
        return jsonify({'erro': 'Conteúdo vazio.'}), 400
    instrucoes = dados.get('instrucoes', '').strip()

    html, b64_reps = _strip_base64(html)

    prompt = f"""Você vai melhorar o TEXTO de um e-mail de marketing escrito por um usuário, mantendo a estrutura HTML, imagens, links, botões e formatação existentes.

HTML atual do e-mail:
{html}

Instruções:
- Reescreva e aprimore os textos (parágrafos, títulos, botões) para ficarem mais claros, persuasivos, profissionais e com mais profundidade — adicione contexto, exemplos ou argumentos quando o texto original for muito raso{f'. Siga também esta orientação adicional do usuário: {instrucoes}' if instrucoes else ''}.
- NÃO remova nem altere imagens (tags <img>), links (atributos href) ou a estrutura/tags HTML existentes — melhore apenas o conteúdo de texto.
- Mantenha {{nome}} onde já estiver presente para personalização.
- Retorne APENAS o HTML completo resultante, sem explicações, sem markdown, sem blocos ```.
"""
    try:
        client = _anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=8000,
            messages=[{'role': 'user', 'content': prompt}]
        )
        out = resp.content[0].text.strip()
        out = re.sub(r'^```[a-z]*\n?', '', out)
        out = re.sub(r'\n?```$', '', out).strip()
        out = _restore_base64(out, b64_reps)
        return jsonify({'html': out})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/ia/formatar-conteudo', methods=['POST'])
def ia_formatar_conteudo():
    if not ANTHROPIC_OK:
        return jsonify({'erro': 'Anthropic SDK não instalado.'}), 500
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return jsonify({'erro': 'ANTHROPIC_API_KEY não configurada no Railway.'}), 500

    dados = request.get_json() or {}
    conteudo = dados.get('conteudo', '').strip()
    if not conteudo:
        return jsonify({'erro': 'Conteúdo vazio.'}), 400

    conteudo, b64_reps = _strip_base64(conteudo)

    prompt = f"""Você vai transformar o conteúdo de um e-mail escrito por um usuário em um e-mail HTML visualmente bem formatado.

Conteúdo original do usuário:
{conteudo}

Instruções obrigatórias:
- MANTENHA TODO O CONTEÚDO ORIGINAL ÍNTEGRO. Não remova, resuma ou altere informações. Apenas formate visualmente adicionando títulos grandes, subtítulos, checklists onde apropriado, negritos em pontos importantes e espaçamento adequado.
- Não invente informações novas, não acrescente parágrafos de conteúdo que o usuário não escreveu.
- Organize o texto existente em uma estrutura HTML clara: títulos (<h1>/<h2>), subtítulos, parágrafos, listas (<ul>/<ol>) e <strong> em pontos importantes, conforme fizer sentido para o conteúdo.
- Email responsivo, máximo 600px de largura, centralizado, com cabeçalho simples.
- Use SOMENTE inline CSS (style="...") — nenhuma tag <style> ou <link>.
- Mantenha {{nome}} onde já estiver presente no texto original para personalização.
- Retorne APENAS o código HTML completo, sem explicações, sem markdown, sem blocos ```.
"""
    try:
        client = _anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=8000,
            messages=[{'role': 'user', 'content': prompt}]
        )
        html = resp.content[0].text.strip()
        html = re.sub(r'^```[a-z]*\n?', '', html)
        html = re.sub(r'\n?```$', '', html).strip()
        html = _restore_base64(html, b64_reps)
        return jsonify({'html': html})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/ia/aplicar-template', methods=['POST'])
def ia_aplicar_template():
    if not ANTHROPIC_OK:
        return jsonify({'erro': 'Anthropic SDK não instalado.'}), 500
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return jsonify({'erro': 'ANTHROPIC_API_KEY não configurada no Railway.'}), 500

    dados = request.get_json() or {}
    conteudo = dados.get('conteudo_html', '').strip()
    template = dados.get('template_html', '').strip()
    if not conteudo or not template:
        return jsonify({'erro': 'Conteúdo e template são obrigatórios.'}), 400

    conteudo, b64_reps_c = _strip_base64(conteudo)
    template, b64_reps_t = _strip_base64(template)

    prompt = f"""Você vai aplicar um TEMPLATE VISUAL a um conteúdo de e-mail já escrito por um usuário.

Conteúdo do usuário (texto, imagens e links a preservar):
{conteudo}

Template visual de referência (use o layout, cores, fontes, estrutura e seções deste template):
{template}

Instruções:
- Gere um novo HTML de e-mail usando o layout/cores/estilo/estrutura visual do TEMPLATE acima (cabeçalho, cores, tipografia, blocos, rodapé).
- NÃO resuma, corte, reduza ou encurte o texto do usuário. TODO o conteúdo de texto do usuário deve aparecer no resultado final, na íntegra — palavra por palavra. É proibido remover frases ou parágrafos para "caber" no template.
- Substitua os textos de EXEMPLO/placeholder do template (títulos genéricos, parágrafos de demonstração) pelo conteúdo real do usuário. Se o conteúdo do usuário for mais longo que o espaço do template, ADAPTE/EXPANDA a estrutura do template (adicione mais parágrafos, itens de lista ou seções repetindo o mesmo estilo visual) em vez de cortar texto.
- Preserve TODAS as imagens (tags <img src="...">) e links (atributos href) que o usuário já tinha no conteúdo original, posicionando-os nos lugares apropriados do template.
- Mantenha {{nome}} para personalização.
- Retorne APENAS o HTML completo resultante, sem explicações, sem markdown, sem blocos ```.
"""
    try:
        client = _anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=8000,
            messages=[{'role': 'user', 'content': prompt}]
        )
        out = resp.content[0].text.strip()
        out = re.sub(r'^```[a-z]*\n?', '', out)
        out = re.sub(r'\n?```$', '', out).strip()
        out = _restore_base64(out, b64_reps_c)
        out = _restore_base64(out, b64_reps_t)
        return jsonify({'html': out})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/ia/ajustar-visual', methods=['POST'])
def ia_ajustar_visual():
    if not ANTHROPIC_OK:
        return jsonify({'erro': 'Anthropic SDK não instalado.'}), 500
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return jsonify({'erro': 'ANTHROPIC_API_KEY não configurada no Railway.'}), 500

    dados = request.get_json() or {}
    conteudo = dados.get('conteudo_html', '').strip()
    template = dados.get('template_html', '').strip()
    if not conteudo or not template:
        return jsonify({'erro': 'Conteúdo e template são obrigatórios.'}), 400

    conteudo, b64_reps_c = _strip_base64(conteudo)
    template, b64_reps_t = _strip_base64(template)

    prompt = f"""Você vai ajustar APENAS o visual de um e-mail, mantendo o conteúdo e a formatação de texto exatamente como estão.

Conteúdo atual do usuário (preserve textos, parágrafos, listas, negritos, links e imagens EXATAMENTE como estão, na mesma ordem):
{conteudo}

Template de referência visual (use APENAS como referência de cores, fontes, cabeçalho, rodapé e largura/layout geral):
{template}

Instruções obrigatórias:
- NÃO altere, resuma, corte ou reescreva nenhum texto do conteúdo do usuário. Mantenha cada palavra, frase, parágrafo, lista, link e imagem como estão.
- NÃO mude a estrutura/ordem do conteúdo do usuário.
- Aplique ao redor/sobre esse conteúdo apenas o estilo visual do template: cores (cabeçalho, fundos, botões, bordas), fontes, cabeçalho e rodapé do template.
- Pode envolver o conteúdo existente no cabeçalho/rodapé do template e ajustar cores de elementos (botões, títulos, fundos) para combinar com a paleta do template, mas sem alterar o texto em si.
- Use SOMENTE inline CSS (style="...") — nenhuma tag <style> ou <link>.
- Mantenha {{nome}} onde já estiver presente.
- Retorne APENAS o HTML completo resultante, sem explicações, sem markdown, sem blocos ```.
"""
    try:
        client = _anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=8000,
            messages=[{'role': 'user', 'content': prompt}]
        )
        out = resp.content[0].text.strip()
        out = re.sub(r'^```[a-z]*\n?', '', out)
        out = re.sub(r'\n?```$', '', out).strip()
        out = _restore_base64(out, b64_reps_c)
        out = _restore_base64(out, b64_reps_t)
        return jsonify({'html': out})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/ia/buscar-imagem', methods=['POST'])
def ia_buscar_imagem():
    if not UNSPLASH_ACCESS_KEY:
        return jsonify({'erro': 'UNSPLASH_ACCESS_KEY não configurada.'}), 500
    data = request.get_json() or {}
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'erro': 'Descrição obrigatória.'}), 400
    try:
        r = http_requests.get(
            'https://api.unsplash.com/search/photos',
            params={'query': query, 'per_page': 6, 'orientation': 'landscape'},
            headers={'Authorization': f'Client-ID {UNSPLASH_ACCESS_KEY}'},
            timeout=10
        )
        r.raise_for_status()
        results = r.json().get('results', [])
        imagens = [{
            'thumb': img['urls']['small'],
            'full': img['urls']['regular'],
            'desc': img.get('alt_description') or img.get('description') or query,
            'autor': img['user']['name']
        } for img in results]
        return jsonify({'imagens': imagens})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ── Templates Visuais ─────────────────────────────────────────────────────────

@app.route('/templates-visuais')
def templates_visuais():
    conn = get_db()
    kits = conn.execute('SELECT id, name FROM brand_kits ORDER BY name').fetchall()
    conn.close()
    return render_template('templates_visuais.html', kits=kits)

# ── Chat IA Landing Page ─────────────────────────────────────────────────────

@app.route('/ia/chat-landing', methods=['POST'])
def ia_chat_landing():
    if not ANTHROPIC_OK:
        return jsonify({'erro': 'Anthropic SDK não instalado.'}), 500
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return jsonify({'erro': 'ANTHROPIC_API_KEY não configurada.'}), 500

    dados = request.get_json() or {}
    mensagem = (dados.get('mensagem') or '').strip()
    historico = dados.get('historico') or []
    if not mensagem:
        return jsonify({'erro': 'Mensagem vazia.'}), 400

    system_prompt = """Você é o assistente virtual do ConvertMail, plataforma completa de email marketing com IA da TFA Soluções Digitais.

Responda de forma simpática, objetiva e persuasiva (máximo 3-4 frases curtas). Use português brasileiro.

O que o ConvertMail oferece:
- Geração de emails com IA (Claude) — cria emails profissionais em segundos
- Kit de Marca — salva cores, fontes, logo e tom de voz para manter identidade visual
- Gerenciador de Email (IMAP) — leia e responda emails direto na plataforma
- Campanhas com agendamento — envie imediato ou agende para data/hora ideal
- Cadências automáticas (sequências) — follow-ups automáticos com intervalos personalizados
- Templates visuais prontos — layouts profissionais editáveis
- Gestão de contatos com scoring — pontuação automática de leads (quente/morno/frio)
- Tags e segmentação — organize contatos por grupos
- Teste A/B — teste variações de assunto para melhorar aberturas
- Envio condicional — dispare emails só se o contato abriu/clicou o anterior
- Melhor horário por contato — IA aprende quando cada pessoa abre emails
- Enriquecimento de leads com IA — completa dados automaticamente
- Heatmap de cliques — veja onde as pessoas clicam nos seus emails
- Calendário de campanhas — visualize tudo que está agendado
- Múltiplas contas de email — gerencie vários remetentes
- Blacklist e descadastro automático — conformidade com LGPD
- Captura de leads (Firecrawl) — extraia contatos de sites automaticamente
- Exportação CSV — importe e exporte sua base de contatos
- Analytics completos — aberturas, cliques, bounces, timeline por contato

Preço: plano único a partir de R$97/mês, tudo incluso, sem limites de envio.

Se perguntarem algo fora do escopo, redirecione educadamente para o ConvertMail.
Sempre termine convidando a pessoa a se cadastrar ou testar gratuitamente."""

    messages = []
    for h in historico[-10:]:
        role = 'user' if h.get('role') == 'user' else 'assistant'
        messages.append({'role': role, 'content': h.get('content', '')})
    messages.append({'role': 'user', 'content': mensagem})

    try:
        client = _anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=300,
            system=system_prompt,
            messages=messages
        )
        resposta = resp.content[0].text
        return jsonify({'resposta': resposta})
    except Exception as e:
        app.logger.exception('Erro no chat landing IA')
        return jsonify({'erro': f'Erro ao processar: {e}'}), 500

# ── Chat IA Assistente (in-app) ───────────────────────────────────────────────

@app.route('/assistente')
def assistente_ia():
    conn = get_db()
    total_contacts = conn.execute('SELECT COUNT(*) as n FROM contacts').fetchone()['n']
    total_campaigns = conn.execute('SELECT COUNT(*) as n FROM campaigns').fetchone()['n']
    total_sequences = conn.execute('SELECT COUNT(*) as n FROM sequences').fetchone()['n']
    recent_campaigns = conn.execute(
        "SELECT name, status, subject, total_sent, total_opened, total_clicked FROM campaigns ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    conn.close()
    return render_template('assistente.html',
                           total_contacts=total_contacts,
                           total_campaigns=total_campaigns,
                           total_sequences=total_sequences,
                           recent_campaigns=recent_campaigns)

@app.route('/ia/chat-assistente', methods=['POST'])
def ia_chat_assistente():
    if not ANTHROPIC_OK:
        return jsonify({'erro': 'Anthropic SDK não instalado.'}), 500
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return jsonify({'erro': 'ANTHROPIC_API_KEY não configurada.'}), 500

    dados = request.get_json() or {}
    mensagem = (dados.get('mensagem') or '').strip()
    historico = dados.get('historico') or []
    contexto = dados.get('contexto') or ''
    if not mensagem:
        return jsonify({'erro': 'Mensagem vazia.'}), 400

    system_prompt = f"""Você é o assistente de IA do ConvertMail — um consultor especialista em email marketing que ajuda o usuário a melhorar suas campanhas, criar estratégias e usar a plataforma da melhor forma.

Dados atuais da conta do usuário:
{contexto}

Suas capacidades:
1. ESTRATÉGIA DE EMAIL MARKETING — sugira melhores práticas, frequência de envio, segmentação, personalização
2. ANÁLISE DE CAMPANHAS — analise métricas (aberturas, cliques, bounces), identifique problemas e sugira melhorias
3. COPYWRITING — sugira assuntos, CTAs, estrutura de email, tom de voz
4. AUTOMAÇÃO — ajude a configurar cadências/sequências, definir gatilhos, envio condicional
5. SEGMENTAÇÃO — sugira como organizar contatos com tags, scoring, e segmentos
6. DELIVERABILITY — dicas para evitar spam, melhorar entregabilidade, autenticação (SPF/DKIM/DMARC)
7. LGPD — orientações sobre conformidade, opt-in, descadastro
8. USO DA PLATAFORMA — explique como usar recursos do ConvertMail

Regras:
- Responda em português brasileiro, de forma clara e prática
- Forneça respostas acionáveis com passos concretos
- Quando relevante, referencie recursos da plataforma (ex: "vá em Cadências > Nova Cadência")
- Use dados da conta do usuário para personalizar sugestões
- Para perguntas sobre métricas, compare com benchmarks do mercado (ex: taxa de abertura média ~20-25%)
- Limite respostas a 3-5 parágrafos curtos, use listas quando apropriado
- Se perguntarem algo fora de email marketing, redirecione educadamente"""

    messages = []
    for h in historico[-20:]:
        role = 'user' if h.get('role') == 'user' else 'assistant'
        messages.append({'role': role, 'content': h.get('content', '')})
    messages.append({'role': 'user', 'content': mensagem})

    try:
        client = _anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=800,
            system=system_prompt,
            messages=messages
        )
        resposta = resp.content[0].text
        return jsonify({'resposta': resposta})
    except Exception as e:
        app.logger.exception('Erro no chat assistente IA')
        return jsonify({'erro': f'Erro ao processar: {e}'}), 500

# ── 1. Re-envio para não-abridores ────────────────────────────────────────────

@app.route('/campanha/<int:campaign_id>/reenviar-nao-abridores', methods=['POST'])
def reenviar_nao_abridores(campaign_id):
    conn = get_db()
    campaign = conn.execute('SELECT * FROM campaigns WHERE id=%s', (campaign_id,)).fetchone()
    if not campaign:
        conn.close()
        flash('Campanha não encontrada.', 'danger')
        return redirect(url_for('index'))
    novo_assunto = request.form.get('novo_assunto', '').strip()
    if not novo_assunto:
        conn.close()
        flash('Informe um novo assunto.', 'danger')
        return redirect(url_for('campanha_detalhe', campaign_id=campaign_id))

    openers = {r['contact_email'] for r in conn.execute(
        'SELECT DISTINCT contact_email FROM email_opens WHERE campaign_id=%s', (campaign_id,)).fetchall()}
    sent_contacts = conn.execute(
        "SELECT contact_email, contact_name FROM campaign_logs WHERE campaign_id=%s AND status='sent'",
        (campaign_id,)).fetchall()
    non_openers = [{'email': r['contact_email'], 'name': r['contact_name'] or ''}
                   for r in sent_contacts if r['contact_email'] not in openers]

    if not non_openers:
        conn.close()
        flash('Todos os contatos já abriram — ninguém para reenviar!', 'info')
        return redirect(url_for('campanha_detalhe', campaign_id=campaign_id))

    cur = conn.execute(
        "INSERT INTO campaigns (name,subject,body,sender_email,total_contacts,status,resent_from) "
        "VALUES (%s,%s,%s,%s,%s,'pending',%s) RETURNING id",
        (f"Re: {campaign['name']} (não-abridores)", novo_assunto, campaign['body'],
         campaign['sender_email'], len(non_openers), campaign_id))
    new_id = cur.fetchone()['id']
    conn.commit()
    conn.close()

    t = threading.Thread(target=run_campaign,
                         args=(new_id, non_openers, campaign['sender_email'], novo_assunto, campaign['body']),
                         daemon=True)
    t.start()
    flash(f'Reenvio iniciado para {len(non_openers)} contato(s) que não abriram!', 'success')
    return redirect(url_for('campanha_detalhe', campaign_id=new_id))

# ── 2. Classificação de respostas com IA ─────────────────────────────────────

@app.route('/ia/classificar-resposta', methods=['POST'])
def ia_classificar_resposta():
    if not ANTHROPIC_OK:
        return jsonify({'erro': 'Anthropic SDK não instalado.'}), 500
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return jsonify({'erro': 'ANTHROPIC_API_KEY não configurada.'}), 500
    dados = request.get_json() or {}
    corpo_email = (dados.get('corpo') or '').strip()
    if not corpo_email:
        return jsonify({'erro': 'Corpo do email vazio.'}), 400

    system_prompt = """Você é um classificador de respostas de email marketing.
Analise a resposta do lead e retorne um JSON com:
- "intencao": uma de ["interessado", "duvida", "nao_interessado", "pedido_remocao", "auto_resposta", "outro"]
- "urgencia": "alta", "media" ou "baixa"
- "resumo": resumo de 1 frase da resposta
- "sugestao_resposta": sugestão de resposta curta e profissional (2-3 frases)

Retorne APENAS o JSON, sem markdown."""

    try:
        client = _anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001', max_tokens=400,
            system=system_prompt,
            messages=[{'role': 'user', 'content': f'Classifique esta resposta de email:\n\n{corpo_email[:2000]}'}]
        )
        import json
        resultado = json.loads(resp.content[0].text)
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ── 3. Formulários de captura embutíveis ─────────────────────────────────────

@app.route('/formularios')
def formularios():
    conn = get_db()
    forms = conn.execute('SELECT * FROM capture_forms ORDER BY created_at DESC').fetchall()
    sequences = conn.execute("SELECT id, name FROM sequences ORDER BY name").fetchall()
    conn.close()
    return render_template('formularios.html', forms=forms, sequences=sequences)

@app.route('/formularios/salvar', methods=['POST'])
def formulario_salvar():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Nome obrigatório.', 'danger')
        return redirect(url_for('formularios'))
    conn = get_db()
    form_id = request.form.get('form_id')
    data = (name, request.form.get('tag', '').strip(),
            request.form.get('sequence_id') or None,
            request.form.get('heading', 'Inscreva-se').strip(),
            request.form.get('description', '').strip(),
            request.form.get('button_text', 'Cadastrar').strip(),
            request.form.get('primary_color', '#4361ee').strip())
    if form_id:
        conn.execute('UPDATE capture_forms SET name=%s,tag=%s,sequence_id=%s,heading=%s,description=%s,button_text=%s,primary_color=%s WHERE id=%s',
                     data + (form_id,))
    else:
        conn.execute('INSERT INTO capture_forms (name,tag,sequence_id,heading,description,button_text,primary_color) VALUES (%s,%s,%s,%s,%s,%s,%s)', data)
    conn.commit()
    conn.close()
    flash('Formulário salvo!', 'success')
    return redirect(url_for('formularios'))

@app.route('/formularios/<int:form_id>/deletar', methods=['POST'])
def formulario_deletar(form_id):
    conn = get_db()
    conn.execute('DELETE FROM capture_forms WHERE id=%s', (form_id,))
    conn.commit()
    conn.close()
    flash('Formulário removido.', 'success')
    return redirect(url_for('formularios'))

@app.route('/api/captura', methods=['POST', 'OPTIONS'])
def api_captura():
    if request.method == 'OPTIONS':
        resp = Response('', 204)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp
    dados = request.get_json() or {}
    email = (dados.get('email') or '').strip().lower()
    name = (dados.get('name') or '').strip()
    form_id = dados.get('form_id')
    if not email or '@' not in email:
        r = jsonify({'erro': 'Email inválido.'})
        r.headers['Access-Control-Allow-Origin'] = '*'
        return r, 400
    conn = get_db()
    tag = ''
    seq_id = None
    if form_id:
        form = conn.execute('SELECT * FROM capture_forms WHERE id=%s', (form_id,)).fetchone()
        if form:
            tag = form['tag'] or ''
            seq_id = form['sequence_id']
    upsert_contact(email, name, tag, conn)
    if seq_id:
        enroll_contacts_in_sequence(int(seq_id), [{'email': email, 'name': name, 'tags': tag}], conn)
    conn.commit()
    conn.close()
    r = jsonify({'ok': True, 'message': 'Cadastro realizado com sucesso!'})
    r.headers['Access-Control-Allow-Origin'] = '*'
    return r

# ── 4. Painel de Analytics avançado ──────────────────────────────────────────

@app.route('/analytics')
def analytics():
    conn = get_db()
    total_sent = conn.execute('SELECT COALESCE(SUM(sent),0) as n FROM campaigns').fetchone()['n']
    total_opened = conn.execute('SELECT COUNT(DISTINCT id) as n FROM email_opens').fetchone()['n']
    total_contacts = conn.execute('SELECT COUNT(*) as n FROM contacts').fetchone()['n']
    total_campaigns = conn.execute('SELECT COUNT(*) as n FROM campaigns').fetchone()['n']
    open_rate = round(total_opened / total_sent * 100, 1) if total_sent > 0 else 0

    by_hour = conn.execute(
        'SELECT hour_of_day as h, COUNT(*) as n FROM send_analytics WHERE hour_of_day IS NOT NULL '
        'GROUP BY hour_of_day ORDER BY hour_of_day').fetchall()
    by_dow = conn.execute(
        'SELECT day_of_week as d, COUNT(*) as n FROM send_analytics WHERE day_of_week IS NOT NULL '
        'GROUP BY day_of_week ORDER BY day_of_week').fetchall()

    top_campaigns = conn.execute(
        "SELECT id, name, sent, "
        "(SELECT COUNT(DISTINCT contact_email) FROM email_opens WHERE campaign_id=c.id) as opens "
        "FROM campaigns c WHERE sent > 0 ORDER BY sent DESC LIMIT 10").fetchall()

    monthly_sends = conn.execute(
        "SELECT TO_CHAR(sent_at, 'YYYY-MM') as month, COUNT(*) as n "
        "FROM send_analytics WHERE sent_at IS NOT NULL "
        "GROUP BY TO_CHAR(sent_at, 'YYYY-MM') ORDER BY month DESC LIMIT 12").fetchall()
    monthly_sends = list(reversed(monthly_sends))

    score_dist = conn.execute(
        "SELECT CASE WHEN score >= 100 THEN 'Muito Quente' WHEN score >= 51 THEN 'Quente' "
        "WHEN score >= 21 THEN 'Morno' ELSE 'Frio' END as faixa, COUNT(*) as n "
        "FROM contacts GROUP BY faixa").fetchall()

    conn.close()
    return render_template('analytics.html',
                           total_sent=total_sent, total_opened=total_opened,
                           total_contacts=total_contacts, total_campaigns=total_campaigns,
                           open_rate=open_rate, by_hour=by_hour, by_dow=by_dow,
                           top_campaigns=top_campaigns, monthly_sends=monthly_sends,
                           score_dist=score_dist)

# ── 5. Rastreamento de receita (contact_purchases) ──────────────────────────

@app.route('/contatos/<path:email>/compra', methods=['POST'])
def registrar_compra(email):
    product = request.form.get('product', '').strip()
    amount = request.form.get('amount', '0').strip()
    campaign_id = request.form.get('campaign_id') or None
    if not product:
        flash('Informe o produto.', 'danger')
        return redirect(url_for('contato_perfil', email=email))
    try:
        amount_val = float(amount.replace(',', '.'))
    except ValueError:
        amount_val = 0
    conn = get_db()
    conn.execute(
        'INSERT INTO contact_purchases (contact_email,product,amount,campaign_id,purchased_at) VALUES (%s,%s,%s,%s,NOW())',
        (email, product, amount_val, campaign_id))
    update_score(email, 20, conn)
    log_activity(email, 'purchase', f'{product} — R${amount_val:.2f}', conn)
    conn.commit()
    conn.close()
    flash('Compra registrada!', 'success')
    return redirect(url_for('contato_perfil', email=email))

@app.route('/api/receita')
def api_receita():
    conn = get_db()
    total = conn.execute('SELECT COALESCE(SUM(amount),0) as n FROM contact_purchases').fetchone()['n']
    by_month = conn.execute(
        "SELECT TO_CHAR(purchased_at, 'YYYY-MM') as month, SUM(amount) as total "
        "FROM contact_purchases WHERE purchased_at IS NOT NULL "
        "GROUP BY TO_CHAR(purchased_at, 'YYYY-MM') ORDER BY month DESC LIMIT 12").fetchall()
    top_contacts = conn.execute(
        "SELECT contact_email, SUM(amount) as total, COUNT(*) as compras "
        "FROM contact_purchases GROUP BY contact_email ORDER BY total DESC LIMIT 10").fetchall()
    conn.close()
    return jsonify({'total': float(total), 'by_month': [dict(r) for r in by_month],
                    'top_contacts': [dict(r) for r in top_contacts]})

# ── 6. Verificador de spam ───────────────────────────────────────────────────

@app.route('/ia/verificar-spam', methods=['POST'])
def verificar_spam():
    dados = request.get_json() or {}
    html = dados.get('html', '')
    subject = dados.get('subject', '')
    problemas = []
    score = 100

    spam_words = ['grátis', 'gratuito', 'urgente', 'clique aqui', 'oferta imperdível',
                  'ganhe dinheiro', 'renda extra', 'sem custo', 'promoção', 'desconto exclusivo',
                  'última chance', 'tempo limitado', 'compre agora', 'free', 'click here',
                  'act now', 'limited time', 'buy now', 'winner', 'congratulations']
    text_lower = (html + ' ' + subject).lower()
    found_spam = [w for w in spam_words if w in text_lower]
    if found_spam:
        score -= len(found_spam) * 8
        problemas.append({'tipo': 'palavras', 'severidade': 'alta',
                          'msg': f'Palavras gatilho de spam encontradas: {", ".join(found_spam)}'})

    if subject.upper() == subject and len(subject) > 5:
        score -= 15
        problemas.append({'tipo': 'assunto', 'severidade': 'alta',
                          'msg': 'Assunto todo em MAIÚSCULAS — filtros de spam penalizam isso.'})
    if subject.count('!') > 1:
        score -= 10
        problemas.append({'tipo': 'assunto', 'severidade': 'media',
                          'msg': 'Múltiplas exclamações no assunto — parecem spam.'})

    img_count = html.lower().count('<img')
    text_len = len(re.sub(r'<[^>]+>', '', html))
    if img_count > 0 and text_len < 100:
        score -= 20
        problemas.append({'tipo': 'conteudo', 'severidade': 'alta',
                          'msg': 'Pouco texto e muitas imagens — filtros penalizam emails só com imagens.'})
    if text_len < 50:
        score -= 10
        problemas.append({'tipo': 'conteudo', 'severidade': 'media',
                          'msg': 'Conteúdo muito curto — emails com pouco texto parecem suspeitos.'})

    link_count = html.lower().count('<a ')
    if link_count > 10:
        score -= 10
        problemas.append({'tipo': 'links', 'severidade': 'media',
                          'msg': f'{link_count} links encontrados — muitos links parecem spam.'})

    if 'unsubscribe' not in html.lower() and 'descadastrar' not in html.lower():
        score -= 15
        problemas.append({'tipo': 'conformidade', 'severidade': 'alta',
                          'msg': 'Sem link de descadastro — obrigatório por lei (LGPD/CAN-SPAM).'})

    score = max(0, score)
    nivel = 'excelente' if score >= 80 else 'bom' if score >= 60 else 'regular' if score >= 40 else 'ruim'
    return jsonify({'score': score, 'nivel': nivel, 'problemas': problemas})

# ── 7. Preview mobile/desktop ────────────────────────────────────────────────

@app.route('/preview-email', methods=['POST'])
def preview_email():
    html = request.form.get('html', '')
    return render_template('preview_email.html', email_html=html)

# ── 8. Assistente SPF/DKIM/DMARC ────────────────────────────────────────────

@app.route('/verificar-dominio', methods=['POST'])
def verificar_dominio():
    import subprocess
    dados = request.get_json() or {}
    dominio = (dados.get('dominio') or '').strip().lower()
    if not dominio or '.' not in dominio:
        return jsonify({'erro': 'Domínio inválido.'}), 400

    resultados = {}
    try:
        r = subprocess.run(['dig', '+short', 'TXT', dominio], capture_output=True, text=True, timeout=10)
        txts = r.stdout.strip()
        spf_found = 'v=spf1' in txts
        resultados['spf'] = {
            'ok': spf_found,
            'registro': txts if spf_found else None,
            'instrucao': None if spf_found else f'Adicione um registro TXT no DNS de {dominio}: v=spf1 include:sendinblue.com ~all'
        }
    except Exception:
        resultados['spf'] = {'ok': False, 'registro': None, 'instrucao': 'Não foi possível verificar SPF.'}

    try:
        r = subprocess.run(['dig', '+short', 'TXT', f'mail._domainkey.{dominio}'], capture_output=True, text=True, timeout=10)
        dkim_found = 'DKIM1' in r.stdout or 'v=DKIM1' in r.stdout
        if not dkim_found:
            r2 = subprocess.run(['dig', '+short', 'TXT', f'brevo._domainkey.{dominio}'], capture_output=True, text=True, timeout=10)
            dkim_found = 'DKIM1' in r2.stdout or 'v=DKIM1' in r2.stdout
        resultados['dkim'] = {
            'ok': dkim_found,
            'instrucao': None if dkim_found else f'Configure o DKIM no painel da Brevo e adicione o registro CNAME/TXT no DNS de {dominio}.'
        }
    except Exception:
        resultados['dkim'] = {'ok': False, 'instrucao': 'Não foi possível verificar DKIM.'}

    try:
        r = subprocess.run(['dig', '+short', 'TXT', f'_dmarc.{dominio}'], capture_output=True, text=True, timeout=10)
        dmarc_found = 'v=DMARC1' in r.stdout
        resultados['dmarc'] = {
            'ok': dmarc_found,
            'registro': r.stdout.strip() if dmarc_found else None,
            'instrucao': None if dmarc_found else f'Adicione um registro TXT em _dmarc.{dominio}: v=DMARC1; p=quarantine; rua=mailto:dmarc@{dominio}'
        }
    except Exception:
        resultados['dmarc'] = {'ok': False, 'instrucao': 'Não foi possível verificar DMARC.'}

    score = sum(1 for v in resultados.values() if v['ok'])
    return jsonify({'dominio': dominio, 'resultados': resultados, 'score': f'{score}/3'})

# ── 9. Warm-up de domínio ────────────────────────────────────────────────────

@app.route('/warmup')
def warmup():
    conn = get_db()
    plans = conn.execute('SELECT * FROM warmup_plans ORDER BY created_at DESC').fetchall()
    accounts = conn.execute('SELECT email FROM email_accounts WHERE active=TRUE ORDER BY email').fetchall()
    conn.close()
    return render_template('warmup.html', plans=plans, accounts=accounts)

@app.route('/warmup/criar', methods=['POST'])
def warmup_criar():
    sender = request.form.get('sender_email', '').strip()
    daily_start = int(request.form.get('daily_limit', '10'))
    total_days = int(request.form.get('total_days', '14'))
    growth = float(request.form.get('growth_rate', '1.5'))
    if not sender:
        flash('Selecione um email remetente.', 'danger')
        return redirect(url_for('warmup'))
    conn = get_db()
    conn.execute(
        'INSERT INTO warmup_plans (sender_email,daily_limit,total_days,growth_rate) VALUES (%s,%s,%s,%s)',
        (sender, daily_start, total_days, growth))
    conn.commit()
    conn.close()
    flash(f'Plano de warm-up criado para {sender}!', 'success')
    return redirect(url_for('warmup'))

@app.route('/warmup/<int:plan_id>/pausar', methods=['POST'])
def warmup_pausar(plan_id):
    conn = get_db()
    plan = conn.execute('SELECT status FROM warmup_plans WHERE id=%s', (plan_id,)).fetchone()
    new_status = 'paused' if plan and plan['status'] == 'active' else 'active'
    conn.execute('UPDATE warmup_plans SET status=%s WHERE id=%s', (new_status, plan_id))
    conn.commit()
    conn.close()
    flash(f'Warm-up {"pausado" if new_status == "paused" else "retomado"}!', 'info')
    return redirect(url_for('warmup'))

@app.route('/warmup/<int:plan_id>/deletar', methods=['POST'])
def warmup_deletar(plan_id):
    conn = get_db()
    conn.execute('DELETE FROM warmup_plans WHERE id=%s', (plan_id,))
    conn.commit()
    conn.close()
    flash('Plano de warm-up removido.', 'success')
    return redirect(url_for('warmup'))

@app.route('/api/warmup/<int:plan_id>')
def api_warmup(plan_id):
    conn = get_db()
    plan = conn.execute('SELECT * FROM warmup_plans WHERE id=%s', (plan_id,)).fetchone()
    conn.close()
    if not plan:
        return jsonify({'erro': 'Plano não encontrado.'}), 404
    schedule = []
    daily = plan['daily_limit']
    for day in range(plan['total_days']):
        limit = int(daily * (plan['growth_rate'] ** day))
        schedule.append({'dia': day + 1, 'limite': limit, 'concluido': day < plan['current_day']})
    return jsonify({'plan': dict(plan), 'schedule': schedule})

# ── 10. Notificações em tempo real ───────────────────────────────────────────

@app.route('/api/notificacoes')
def api_notificacoes():
    conn = get_db()
    notifs = conn.execute(
        'SELECT * FROM notifications ORDER BY created_at DESC LIMIT 20').fetchall()
    unread = conn.execute('SELECT COUNT(*) as n FROM notifications WHERE read=FALSE').fetchone()['n']
    conn.close()
    return jsonify({'notificacoes': [dict(n) for n in notifs], 'nao_lidas': unread})

@app.route('/api/notificacoes/ler', methods=['POST'])
def notificacoes_marcar_lidas():
    conn = get_db()
    conn.execute('UPDATE notifications SET read=TRUE WHERE read=FALSE')
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

def criar_notificacao(tipo, titulo, body='', contact_email=None, campaign_id=None):
    try:
        conn = get_db()
        conn.execute(
            'INSERT INTO notifications (type,title,body,contact_email,campaign_id) VALUES (%s,%s,%s,%s,%s)',
            (tipo, titulo, body, contact_email, campaign_id))
        conn.commit()
        conn.close()
    except Exception:
        pass

_db_ready = False
_db_error = ''
_scheduler = None

def _try_init_db():
    global _db_ready, _db_error
    if not DATABASE_URL:
        _db_error = 'DATABASE_URL não configurada. Adicione o PostgreSQL no Railway e conecte-o ao serviço.'
        print(f"ERRO: {_db_error}", flush=True)
        return
    try:
        init_db()
        _db_ready = True
        print("Banco de dados PostgreSQL inicializado com sucesso.", flush=True)
    except Exception as e:
        _db_error = str(e)
        print(f"ERRO ao inicializar banco de dados: {e}", flush=True)

_try_init_db()

def _start_scheduler():
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(processar_cadencias, 'interval', minutes=30)
    _scheduler.add_job(processar_campanhas_agendadas, 'interval', minutes=5)
    _scheduler.add_job(calcular_scores_inativos, 'interval', hours=24)
    _scheduler.start()
    print("APScheduler iniciado.", flush=True)

@app.route('/health')
def health():
    if _db_ready and (_scheduler is None or not _scheduler.running):
        _start_scheduler()
    scheduler_running = _scheduler is not None and _scheduler.running
    return jsonify({
        'status': 'ok' if _db_ready else 'error',
        'db_url_set': bool(DATABASE_URL),
        'brevo_set': bool(BREVO_API_KEY),
        'anthropic_set': bool(os.environ.get('ANTHROPIC_API_KEY', '')) and ANTHROPIC_OK,
        'unsplash_set': bool(UNSPLASH_ACCESS_KEY),
        'app_url': APP_URL,
        'db_error': _db_error if not _db_ready else None,
        'scheduler_running': scheduler_running,
    }), 200 if _db_ready else 503

if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    if _db_ready:
        _start_scheduler()

if __name__ == '__main__':
    print("\nASA Email Marketing rodando em: http://127.0.0.1:5000\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
