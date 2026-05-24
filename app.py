import os
import csv
import io
import threading
import uuid
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
from flask import (Flask, render_template, request, jsonify, redirect,
                   url_for, flash, Response, send_from_directory)
from werkzeug.utils import secure_filename
import psycopg2
import psycopg2.extras
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
IMAGES_FOLDER = os.path.join(UPLOAD_FOLDER, 'imagens')
ALLOWED_EXTENSIONS = {'csv'}
ALLOWED_IMAGE_EXT = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
APP_URL = os.environ.get('APP_URL', 'http://127.0.0.1:5000').rstrip('/')
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')
DATABASE_URL = os.environ.get('DATABASE_URL', '')
# psycopg2 exige postgresql:// mas Railway/Heroku fornecem postgres://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)

PIXEL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00'
    b'\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00'
    b'\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02'
    b'\x44\x01\x00\x3b'
)

_DEFAULT_TEMPLATES = [
    ('Boas-vindas caloroso', 'Relacionamento',
     'Bem-vindo, {nome}! Estamos felizes em te ter aqui',
     '<p>Olá, <strong>{nome}</strong>!</p><p>É um prazer tê-lo(a) conosco. Estou animado(a) para começar essa jornada juntos!</p><p>Nos próximos dias vou compartilhar conteúdos e oportunidades que podem agregar muito ao seu negócio.</p><p>Qualquer dúvida, basta responder este email.</p><p>Um abraço,<br><strong>Equipe ASA Marketing</strong></p>'),
    ('Follow-up após 3 dias', 'Follow-up',
     '{nome}, ainda pensando na nossa conversa?',
     '<p>Olá, <strong>{nome}</strong>,</p><p>Passaram alguns dias desde meu último contato e queria saber se você teve a chance de refletir sobre o que conversamos.</p><p>Fico à disposição para responder qualquer dúvida ou marcar uma conversa rápida de 15 minutos.</p><p>Me avise como posso ajudar!</p><p>Atenciosamente,<br><strong>Equipe ASA Marketing</strong></p>'),
    ('Apresentação de produto/serviço', 'Vendas',
     '{nome}, conheça nossa solução para o seu negócio',
     '<p>Olá, <strong>{nome}</strong>!</p><p>Quero aproveitar para apresentar nossa solução que tem ajudado empresas como a sua a <strong>aumentar resultados</strong>.</p><ul><li>Atendimento personalizado</li><li>Resultados comprovados</li><li>Suporte dedicado</li></ul><p>Posso preparar uma apresentação personalizada para você?</p><p>Atenciosamente,<br><strong>Equipe ASA Marketing</strong></p>'),
    ('Convite para reunião', 'Relacionamento',
     '{nome}, podemos conversar 15 minutos?',
     '<p>Olá, <strong>{nome}</strong>!</p><p>Gostaria de agendar uma conversa rápida de 15 minutos para entender melhor os desafios do seu negócio e mostrar como podemos ajudar.</p><p>Qual horário funciona melhor para você?</p><p>Aguardo seu retorno!</p><p>Atenciosamente,<br><strong>Equipe ASA Marketing</strong></p>'),
    ('Proposta comercial', 'Vendas',
     '{nome}, preparei uma proposta especial para você',
     '<p>Olá, <strong>{nome}</strong>!</p><p>Conforme conversamos, preparei uma proposta personalizada pensando nas necessidades específicas do seu negócio.</p><ul><li>Solução sob medida para o seu segmento</li><li>Condições especiais de investimento</li><li>Implementação rápida e suporte completo</li></ul><p>Podemos agendar uma chamada para detalhar tudo?</p><p>Atenciosamente,<br><strong>Equipe ASA Marketing</strong></p>'),
    ('Reengajamento de lead frio', 'Reengajamento',
     '{nome}, faz tempo que não nos falamos...',
     '<p>Olá, <strong>{nome}</strong>!</p><p>Já faz algum tempo desde nosso último contato e queria saber como você está e como vai o seu negócio.</p><p>Temos novidades que podem ser relevantes para você agora.</p><p>Posso te enviar algumas informações?</p><p>Atenciosamente,<br><strong>Equipe ASA Marketing</strong></p>'),
    ('Agradecimento pós-reunião', 'Relacionamento',
     '{nome}, obrigado pelo seu tempo hoje!',
     '<p>Olá, <strong>{nome}</strong>!</p><p>Quero agradecer pela conversa de hoje. Foi muito produtivo conhecer melhor o seu negócio e os desafios que você enfrenta.</p><p>Como combinado, vou preparar os próximos passos e enviar para você em breve.</p><p>Um abraço,<br><strong>Equipe ASA Marketing</strong></p>'),
    ('Última tentativa de contato', 'Follow-up',
     '{nome}, última mensagem minha sobre isso',
     '<p>Olá, <strong>{nome}</strong>,</p><p>Tentei entrar em contato algumas vezes e entendo que você deve estar ocupado(a).</p><p>Esta será minha última mensagem sobre este assunto.</p><p>Se em algum momento fizer sentido conversar, estarei aqui. Basta responder este email.</p><p>Sucesso no seu negócio!</p><p>Atenciosamente,<br><strong>Equipe ASA Marketing</strong></p>'),
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
    ]
    for sql in tables:
        conn.execute(sql)

    # Migrations idempotentes via bloco DO
    for col_sql in [
        "ALTER TABLE sequence_steps ADD COLUMN ab_subject_b TEXT",
        "ALTER TABLE sequence_steps ADD COLUMN ab_body_b TEXT",
        "ALTER TABLE sequence_steps ADD COLUMN ab_ratio INTEGER DEFAULT 50",
        "ALTER TABLE sequence_logs ADD COLUMN ab_version TEXT DEFAULT 'A'",
        "ALTER TABLE contacts ADD COLUMN product_interest TEXT",
    ]:
        try:
            conn.execute(f"DO $$ BEGIN {col_sql}; EXCEPTION WHEN duplicate_column THEN NULL; END $$")
        except Exception:
            pass

    conn.commit()

    cur = conn.execute('SELECT COUNT(*) as n FROM email_templates')
    if cur.fetchone()['n'] == 0:
        for name, cat, subj, body in _DEFAULT_TEMPLATES:
            conn.execute(
                'INSERT INTO email_templates (name,category,subject,body_html) VALUES (%s,%s,%s,%s)',
                (name, cat, subj, body))
        conn.commit()

    conn.close()

# ── Helpers ─────────────────────────────────────────────────────────────────

campaign_progress = {}

def allowed_file(f): return '.' in f and f.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def allowed_image(f): return '.' in f and f.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXT

def parse_csv(filepath):
    contacts = []
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            with open(filepath, newline='', encoding=enc) as f:
                for row in csv.DictReader(f):
                    name = (row.get('nome') or row.get('Nome') or row.get('name') or
                            row.get('Name') or row.get('NOME') or '').strip()
                    email = (row.get('email') or row.get('Email') or row.get('EMAIL') or
                             row.get('e-mail') or row.get('E-mail') or '').strip()
                    tags = (row.get('tags') or row.get('Tags') or row.get('TAGS') or '').strip()
                    if email:
                        contacts.append({'name': name, 'email': email, 'tags': tags})
            return contacts
        except (UnicodeDecodeError, Exception):
            continue
    return contacts

def upsert_contact(email, name='', tags='', conn=None):
    close = conn is None
    if close: conn = get_db()
    conn.execute(
        'INSERT INTO contacts (email,name,tags) VALUES (%s,%s,%s) ON CONFLICT (email) DO NOTHING',
        (email, name, tags))
    if name:
        conn.execute(
            "UPDATE contacts SET name=%s,updated_at=NOW() WHERE email=%s AND (name IS NULL OR name='')",
            (name, email))
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
    if s >= 100: return ('Muito Quente', '#dc2626', '#fee2e2')
    if s >= 51:  return ('Quente', '#ea580c', '#ffedd5')
    if s >= 21:  return ('Morno', '#ca8a04', '#fef9c3')
    return ('Frio', '#2563eb', '#dbeafe')

app.jinja_env.globals['score_label'] = score_label

def send_email_brevo(sender, recipient_email, recipient_name, subject, body_html):
    personalized_subject = subject.replace('{nome}', recipient_name or 'Cliente')
    personalized_body = body_html.replace('{nome}', recipient_name or 'Cliente')
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    email_obj = sib_api_v3_sdk.SendSmtpEmail(
        to=[{'email': recipient_email, 'name': recipient_name or ''}],
        sender={'email': sender, 'name': 'ASA Marketing'},
        subject=personalized_subject,
        html_content=personalized_body
    )
    return api_instance.send_transac_email(email_obj)

# ── Campanha ─────────────────────────────────────────────────────────────────

def run_campaign(campaign_id, contacts, sender, subject, body_html):
    conn = get_db()
    campaign_progress[campaign_id] = {'total': len(contacts), 'sent': 0, 'errors': 0, 'status': 'running', 'logs': []}
    conn.execute("UPDATE campaigns SET status='running',total_contacts=%s WHERE id=%s", (len(contacts), campaign_id))
    conn.commit()

    for contact in contacts:
        email = contact['email']
        name = contact.get('name', '')

        if is_blacklisted(email, conn):
            continue

        upsert_contact(email, name, contact.get('tags', ''), conn)

        try:
            send_email_brevo(sender, email, name, subject, body_html)
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

    campaign_progress[campaign_id]['status'] = 'done'
    conn.execute("UPDATE campaigns SET status='done',finished_at=NOW() WHERE id=%s", (campaign_id,))
    conn.commit()
    conn.close()

# ── Agendador de cadências ────────────────────────────────────────────────────

def processar_cadencias():
    conn = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cur = conn.execute('''
        SELECT sc.*, s.sender_email AS seq_sender
        FROM sequence_contacts sc
        JOIN sequences s ON s.id = sc.sequence_id
        WHERE sc.status = 'active' AND sc.next_send_at <= %s
    ''', (now,))
    pending = cur.fetchall()

    if not pending:
        conn.close()
        return

    if not BREVO_API_KEY:
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
            if best_hour is not None:
                next_dt = next_dt.replace(hour=best_hour, minute=0, second=0)
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

# ── Guard: redireciona para setup se banco não estiver pronto ─────────────────

_SETUP_EXEMPT = {'health', 'setup_page', 'static'}

@app.before_request
def require_db():
    if not _db_ready and request.endpoint not in _SETUP_EXEMPT:
        return render_template('setup.html',
                               db_url_set=bool(DATABASE_URL),
                               brevo_set=bool(BREVO_API_KEY),
                               db_error=_db_error), 503

@app.route('/setup')
def setup_page():
    return render_template('setup.html',
                           db_url_set=bool(DATABASE_URL),
                           brevo_set=bool(BREVO_API_KEY),
                           db_error=_db_error), 503

# ── Rotas de campanhas ────────────────────────────────────────────────────────

@app.route('/')
def index():
    conn = get_db()
    campaigns = conn.execute("SELECT * FROM campaigns ORDER BY created_at DESC LIMIT 20").fetchall()
    total_contacts = conn.execute('SELECT COUNT(*) as n FROM contacts').fetchone()['n']
    blacklist_count = conn.execute('SELECT COUNT(*) as n FROM blacklist').fetchone()['n']
    hot_leads = conn.execute('SELECT COUNT(*) as n FROM contact_scores WHERE score > 50').fetchone()['n']
    sent_total = conn.execute("SELECT COUNT(*) as n FROM sequence_logs WHERE status='sent'").fetchone()['n']
    opens_total = conn.execute('SELECT COUNT(*) as n FROM email_opens').fetchone()['n']
    open_rate = round(opens_total / sent_total * 100, 1) if sent_total > 0 else 0
    conn.close()
    return render_template('index.html', campaigns=campaigns,
                           total_contacts=total_contacts, blacklist_count=blacklist_count,
                           hot_leads=hot_leads, open_rate=open_rate)

@app.route('/nova-campanha', methods=['GET', 'POST'])
def nova_campanha():
    if request.method == 'POST':
        name = request.form.get('campaign_name', '').strip()
        sender = request.form.get('sender_email', '').strip()
        subject = request.form.get('subject', '').strip()
        body_html = request.form.get('body_html', '').strip()
        send_mode = request.form.get('send_mode', 'csv')

        if not all([name, sender, subject, body_html]):
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('nova_campanha'))

        if send_mode == 'individual':
            ind_name = request.form.get('ind_name', '').strip()
            ind_email = request.form.get('ind_email', '').strip()
            if not ind_email:
                flash('Informe o email do destinatário.', 'danger')
                return redirect(url_for('nova_campanha'))
            contacts = [{'name': ind_name, 'email': ind_email, 'tags': ''}]
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

        conn = get_db()
        cur = conn.execute(
            "INSERT INTO campaigns (name,subject,body,sender_email,total_contacts,status) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (name, subject, body_html, sender, len(contacts), 'pending'))
        campaign_id = cur.fetchone()['id']
        conn.commit()
        conn.close()

        t = threading.Thread(target=run_campaign, args=(campaign_id, contacts, sender, subject, body_html), daemon=True)
        t.start()
        flash(f'Campanha iniciada! Enviando para {len(contacts)} contato(s).', 'success')
        return redirect(url_for('campanha_detalhe', campaign_id=campaign_id))

    return render_template('nova_campanha.html')

@app.route('/campanha/<int:campaign_id>')
def campanha_detalhe(campaign_id):
    conn = get_db()
    campaign = conn.execute("SELECT * FROM campaigns WHERE id=%s", (campaign_id,)).fetchone()
    logs = conn.execute(
        "SELECT * FROM campaign_logs WHERE campaign_id=%s ORDER BY id DESC LIMIT 200",
        (campaign_id,)).fetchall()
    conn.close()
    if not campaign:
        flash('Campanha não encontrada.', 'danger')
        return redirect(url_for('index'))
    return render_template('campanha_detalhe.html', campaign=campaign, logs=logs)

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
    conn.close()
    return render_template('configuracoes.html', signature=sig)

@app.route('/configuracoes/assinatura', methods=['POST'])
def salvar_assinatura():
    body_html = request.form.get('sig_body', '').strip()
    name = request.form.get('sig_name', '').strip()
    conn = get_db()
    existing = conn.execute('SELECT id FROM signature LIMIT 1').fetchone()
    if existing:
        conn.execute(
            "UPDATE signature SET name=%s,body_html=%s,updated_at=NOW() WHERE id=%s",
            (name, body_html, existing['id']))
    else:
        conn.execute('INSERT INTO signature (name,body_html) VALUES (%s,%s)', (name, body_html))
    conn.commit()
    conn.close()
    flash('Assinatura salva com sucesso!', 'success')
    return redirect(url_for('configuracoes'))

@app.route('/api/assinatura')
def api_assinatura():
    conn = get_db()
    sig = conn.execute('SELECT * FROM signature ORDER BY id DESC LIMIT 1').fetchone()
    conn.close()
    return jsonify({'body_html': sig['body_html'] if sig else '', 'name': sig['name'] if sig else ''})

@app.route('/api/templates')
def api_templates():
    conn = get_db()
    tpls = conn.execute('SELECT * FROM email_templates ORDER BY category, name').fetchall()
    conn.close()
    return jsonify([dict(t) for t in tpls])

@app.route('/upload/imagem', methods=['POST'])
def upload_imagem():
    if 'imagem' not in request.files:
        return jsonify({'erro': 'Nenhum arquivo enviado'}), 400
    file = request.files['imagem']
    if file.filename == '' or not allowed_image(file.filename):
        return jsonify({'erro': 'Tipo não permitido'}), 400
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(IMAGES_FOLDER, filename))
    return jsonify({'url': f'/uploads/imagens/{filename}'})

@app.route('/uploads/imagens/<path:filename>')
def serve_imagem(filename):
    return send_from_directory(IMAGES_FOLDER, filename)

# ── Tracking ──────────────────────────────────────────────────────────────────

@app.route('/track/open')
def track_open():
    email = request.args.get('email', '')
    seq_id = request.args.get('seq', type=int)
    step_num = request.args.get('step', type=int)
    if email and seq_id and step_num is not None:
        try:
            conn = get_db()
            conn.execute(
                'INSERT INTO email_opens (sequence_id,contact_email,step_number) VALUES (%s,%s,%s)',
                (seq_id, email, step_num))
            now = datetime.now()
            conn.execute(
                'UPDATE send_analytics SET opened_at=%s,hour_of_day=%s,day_of_week=%s'
                ' WHERE id=(SELECT id FROM send_analytics WHERE contact_email=%s AND opened_at IS NULL ORDER BY sent_at DESC LIMIT 1)',
                (now.strftime('%Y-%m-%d %H:%M:%S'), now.hour, now.weekday(), email))
            opens_count = conn.execute(
                'SELECT COUNT(*) as n FROM email_opens WHERE contact_email=%s', (email,)
            ).fetchone()['n']
            update_score(email, 5 if opens_count == 1 else 2, conn)
            log_activity(email, 'email_opened', f'Cadência {seq_id}, passo {step_num}', conn)
            conn.commit()
            conn.close()
        except Exception:
            pass
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

        if not name or not sender or not days:
            flash('Preencha nome, remetente e pelo menos um passo.', 'danger')
            return redirect(url_for('nova_cadencia'))

        conn = get_db()
        cur = conn.execute(
            'INSERT INTO sequences (name,description,sender_email) VALUES (%s,%s,%s) RETURNING id',
            (name, description, sender))
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
    contacts = conn.execute(
        'SELECT sc.*, cs.score FROM sequence_contacts sc LEFT JOIN contact_scores cs ON cs.email=sc.contact_email WHERE sc.sequence_id=%s ORDER BY sc.started_at DESC LIMIT 200',
        (seq_id,)).fetchall()

    total = conn.execute('SELECT COUNT(*) as n FROM sequence_contacts WHERE sequence_id=%s', (seq_id,)).fetchone()['n']
    active = conn.execute("SELECT COUNT(*) as n FROM sequence_contacts WHERE sequence_id=%s AND status='active'", (seq_id,)).fetchone()['n']
    finished = conn.execute("SELECT COUNT(*) as n FROM sequence_contacts WHERE sequence_id=%s AND status='finished'", (seq_id,)).fetchone()['n']
    sent_total = conn.execute("SELECT COUNT(*) as n FROM sequence_logs WHERE sequence_id=%s AND status='sent'", (seq_id,)).fetchone()['n']
    opens_total = conn.execute('SELECT COUNT(*) as n FROM email_opens WHERE sequence_id=%s', (seq_id,)).fetchone()['n']
    open_rate = round(opens_total / sent_total * 100, 1) if sent_total > 0 else 0

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
        step_metrics.append({'step': st, 'sent_a': s_a, 'sent_b': s_b, 'opens': o_a,
                              'open_rate': round(o_a / (s_a + s_b) * 100, 1) if (s_a + s_b) > 0 else 0})
    conn.close()
    return render_template('cadencia_detalhe.html', seq=seq, steps=steps, contacts=contacts,
                           total=total, active=active, finished=finished,
                           sent_total=sent_total, open_rate=open_rate, step_metrics=step_metrics)

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
        days = request.form.getlist('step_day[]')
        subjects = request.form.getlist('step_subject[]')
        bodies = request.form.getlist('step_body[]')
        conditions = request.form.getlist('step_condition[]')
        ab_subjects_b = request.form.getlist('ab_subject_b[]')
        ab_bodies_b = request.form.getlist('ab_body_b[]')
        ab_ratios = request.form.getlist('ab_ratio[]')

        conn.execute('UPDATE sequences SET name=%s,description=%s,sender_email=%s WHERE id=%s',
                     (name, description, sender, seq_id))
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

    tag_filter = request.form.get('tag_filter', '').strip()

    if 'csv_file' not in request.files or request.files['csv_file'].filename == '':
        flash('Selecione um arquivo CSV.', 'danger'); conn.close(); return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

    file = request.files['csv_file']
    if not allowed_file(file.filename):
        flash('Arquivo deve ser .csv', 'danger'); conn.close(); return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

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
    next_send = (now + timedelta(days=first_step['day_offset'])).strftime('%Y-%m-%d %H:%M:%S')
    added = 0
    for c in all_contacts:
        if is_blacklisted(c['email'], conn):
            continue
        existing = conn.execute(
            'SELECT id FROM sequence_contacts WHERE sequence_id=%s AND contact_email=%s',
            (seq_id, c['email'])).fetchone()
        if not existing:
            conn.execute(
                'INSERT INTO sequence_contacts (sequence_id,contact_email,contact_name,current_step,next_send_at) VALUES (%s,%s,%s,%s,%s)',
                (seq_id, c['email'], c['name'], first_step['step_number'], next_send))
            upsert_contact(c['email'], c['name'], c.get('tags', ''), conn)
            added += 1

    conn.commit(); conn.close()
    flash(f'{added} contatos adicionados à cadência.', 'success')
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
    status = request.form.get('status', 'lead').strip()
    tags = request.form.get('tags', '').strip()
    product_interest = request.form.get('product_interest', '').strip()
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
        'INSERT INTO contacts (email,name,phone,company,status,tags,product_interest) VALUES (%s,%s,%s,%s,%s,%s,%s)',
        (email, name, phone, company, status or 'lead', tags, product_interest or None))
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
        fields = ['name', 'phone', 'company', 'position', 'status', 'tags', 'notes', 'product_interest']
        updates = {f: request.form.get(f, '').strip() for f in fields}
        conn.execute(
            "UPDATE contacts SET name=%s,phone=%s,company=%s,position=%s,status=%s,tags=%s,notes=%s,product_interest=%s,updated_at=NOW() WHERE email=%s",
            (*updates.values(), email))
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
    best_hour = get_best_send_hour(email)
    is_bl = is_blacklisted(email, conn)
    conn.close()
    return render_template('contato_perfil.html', contact=contact, activities=activities,
                           cadencias=cadencias_do_contato, best_hour=best_hour, is_blacklisted=is_bl)

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

_db_ready = False
_db_error = ''

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

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok' if _db_ready else 'error',
        'db_url_set': bool(DATABASE_URL),
        'brevo_set': bool(BREVO_API_KEY),
        'db_error': _db_error if not _db_ready else None,
    }), 200 if _db_ready else 503

if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    if _db_ready:
        _scheduler = BackgroundScheduler(daemon=True)
        _scheduler.add_job(processar_cadencias, 'interval', minutes=30)
        _scheduler.add_job(calcular_scores_inativos, 'interval', hours=24)
        _scheduler.start()

if __name__ == '__main__':
    print("\nASA Email Marketing rodando em: http://127.0.0.1:5000\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
