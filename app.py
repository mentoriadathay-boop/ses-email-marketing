import os
import csv
import io
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
from flask import (Flask, render_template, request, jsonify, redirect,
                   url_for, flash, Response, send_from_directory)
from werkzeug.utils import secure_filename
import boto3
from botocore.exceptions import ClientError
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
IMAGES_FOLDER = os.path.join(UPLOAD_FOLDER, 'imagens')
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'campaigns.db')
ALLOWED_EXTENSIONS = {'csv'}
ALLOWED_IMAGE_EXT = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
AWS_REGION = os.environ.get('AWS_REGION', 'sa-east-1')
APP_URL = os.environ.get('APP_URL', 'http://127.0.0.1:5000').rstrip('/')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
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

# ── Banco de dados ──────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL,
            sender_email TEXT NOT NULL, total_contacts INTEGER DEFAULT 0,
            sent INTEGER DEFAULT 0, errors INTEGER DEFAULT 0, bounces INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now','localtime')), finished_at TEXT
        );
        CREATE TABLE IF NOT EXISTS campaign_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_id INTEGER NOT NULL,
            contact_email TEXT NOT NULL, contact_name TEXT, status TEXT NOT NULL,
            error_message TEXT, sent_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        );
        CREATE TABLE IF NOT EXISTS sequences (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT,
            sender_email TEXT NOT NULL DEFAULT '', status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS sequence_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT, sequence_id INTEGER NOT NULL,
            step_number INTEGER NOT NULL, day_offset INTEGER NOT NULL,
            subject TEXT NOT NULL, body_html TEXT NOT NULL, condition TEXT DEFAULT 'always',
            ab_subject_b TEXT, ab_body_b TEXT, ab_ratio INTEGER DEFAULT 50,
            FOREIGN KEY (sequence_id) REFERENCES sequences(id)
        );
        CREATE TABLE IF NOT EXISTS sequence_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, sequence_id INTEGER NOT NULL,
            contact_email TEXT NOT NULL, contact_name TEXT,
            current_step INTEGER DEFAULT 1, status TEXT DEFAULT 'active',
            next_send_at TEXT, started_at TEXT DEFAULT (datetime('now','localtime')),
            finished_at TEXT, FOREIGN KEY (sequence_id) REFERENCES sequences(id)
        );
        CREATE TABLE IF NOT EXISTS sequence_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, sequence_id INTEGER NOT NULL,
            contact_email TEXT NOT NULL, step_number INTEGER NOT NULL,
            status TEXT NOT NULL, error_message TEXT, ab_version TEXT DEFAULT 'A',
            sent_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS email_opens (
            id INTEGER PRIMARY KEY AUTOINCREMENT, sequence_id INTEGER,
            contact_email TEXT NOT NULL, step_number INTEGER,
            opened_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS email_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT,
            subject TEXT, body_html TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS signature (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, body_html TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS contact_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE,
            score INTEGER DEFAULT 0, updated_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS send_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT, contact_email TEXT NOT NULL,
            sent_at TEXT NOT NULL, opened_at TEXT, hour_of_day INTEGER, day_of_week INTEGER
        );
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE,
            name TEXT, phone TEXT, company TEXT, position TEXT,
            status TEXT DEFAULT 'lead', score INTEGER DEFAULT 0, tags TEXT, notes TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS contact_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT, contact_email TEXT NOT NULL,
            type TEXT NOT NULL, description TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE,
            reason TEXT, added_at TEXT DEFAULT (datetime('now','localtime'))
        );
    ''')

    # Migrations para colunas adicionadas após criação inicial
    for migration in [
        "ALTER TABLE sequence_steps ADD COLUMN ab_subject_b TEXT",
        "ALTER TABLE sequence_steps ADD COLUMN ab_body_b TEXT",
        "ALTER TABLE sequence_steps ADD COLUMN ab_ratio INTEGER DEFAULT 50",
        "ALTER TABLE sequence_logs ADD COLUMN ab_version TEXT DEFAULT 'A'",
    ]:
        try:
            conn.execute(migration)
        except Exception:
            pass

    conn.commit()

    if conn.execute('SELECT COUNT(*) FROM email_templates').fetchone()[0] == 0:
        for name, cat, subj, body in _DEFAULT_TEMPLATES:
            conn.execute(
                'INSERT INTO email_templates (name,category,subject,body_html) VALUES (?,?,?,?)',
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
    conn.execute('INSERT OR IGNORE INTO contacts (email,name,tags) VALUES (?,?,?)', (email, name, tags))
    if name:
        conn.execute("UPDATE contacts SET name=?,updated_at=datetime('now','localtime') WHERE email=? AND (name IS NULL OR name='')", (name, email))
    if tags:
        existing = conn.execute('SELECT tags FROM contacts WHERE email=?', (email,)).fetchone()
        if existing and existing['tags']:
            merged = ','.join(sorted(set(t.strip() for t in (existing['tags']+','+tags).split(',') if t.strip())))
        else:
            merged = tags
        conn.execute('UPDATE contacts SET tags=? WHERE email=?', (merged, email))
    if close: conn.commit(); conn.close()

def is_blacklisted(email, conn=None):
    close = conn is None
    if close: conn = get_db()
    r = conn.execute('SELECT id FROM blacklist WHERE email=?', (email,)).fetchone()
    if close: conn.close()
    return r is not None

def add_to_blacklist(email, reason, conn=None):
    close = conn is None
    if close: conn = get_db()
    try:
        conn.execute('INSERT OR IGNORE INTO blacklist (email,reason) VALUES (?,?)', (email, reason))
        if close: conn.commit()
    except Exception: pass
    if close: conn.close()

def update_score(email, delta, conn=None):
    close = conn is None
    if close: conn = get_db()
    existing = conn.execute('SELECT score FROM contact_scores WHERE email=?', (email,)).fetchone()
    if existing:
        new_score = max(0, existing['score'] + delta)
        conn.execute("UPDATE contact_scores SET score=?,updated_at=datetime('now','localtime') WHERE email=?", (new_score, email))
    else:
        new_score = max(0, delta)
        conn.execute('INSERT INTO contact_scores (email,score) VALUES (?,?)', (email, new_score))
    conn.execute("UPDATE contacts SET score=? WHERE email=?", (new_score, email))
    if close: conn.commit(); conn.close()
    return new_score

def log_activity(email, type_, description, conn=None):
    close = conn is None
    if close: conn = get_db()
    conn.execute('INSERT INTO contact_activities (contact_email,type,description) VALUES (?,?,?)', (email, type_, description))
    if close: conn.commit(); conn.close()

def get_best_send_hour(email):
    conn = get_db()
    row = conn.execute(
        'SELECT hour_of_day FROM send_analytics WHERE contact_email=? AND hour_of_day IS NOT NULL GROUP BY hour_of_day ORDER BY COUNT(*) DESC LIMIT 1',
        (email,)
    ).fetchone()
    conn.close()
    return row['hour_of_day'] if row else None

def score_label(score):
    s = score or 0
    if s >= 100: return ('Muito Quente', '#dc2626', '#fee2e2')
    if s >= 51:  return ('Quente', '#ea580c', '#ffedd5')
    if s >= 21:  return ('Morno', '#ca8a04', '#fef9c3')
    return ('Frio', '#2563eb', '#dbeafe')

app.jinja_env.globals['score_label'] = score_label

def get_ses_client():
    return boto3.client('ses', region_name=AWS_REGION,
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'))

def send_email_ses(ses_client, sender, recipient_email, recipient_name, subject, body_html):
    personalized_subject = subject.replace('{nome}', recipient_name or 'Cliente')
    personalized_body = body_html.replace('{nome}', recipient_name or 'Cliente')
    return ses_client.send_email(
        Source=sender,
        Destination={'ToAddresses': [recipient_email]},
        Message={
            'Subject': {'Data': personalized_subject, 'Charset': 'UTF-8'},
            'Body': {
                'Html': {'Data': personalized_body, 'Charset': 'UTF-8'},
                'Text': {'Data': personalized_body.replace('<br>', '\n').replace('<br/>', '\n'), 'Charset': 'UTF-8'}
            }
        }
    )

# ── Campanha ─────────────────────────────────────────────────────────────────

def run_campaign(campaign_id, contacts, sender, subject, body_html):
    conn = get_db()
    ses = get_ses_client()
    campaign_progress[campaign_id] = {'total': len(contacts), 'sent': 0, 'errors': 0, 'status': 'running', 'logs': []}
    conn.execute("UPDATE campaigns SET status='running',total_contacts=? WHERE id=?", (len(contacts), campaign_id))
    conn.commit()

    for contact in contacts:
        email = contact['email']
        name = contact.get('name', '')

        if is_blacklisted(email, conn):
            continue

        upsert_contact(email, name, contact.get('tags', ''), conn)

        try:
            send_email_ses(ses, sender, email, name, subject, body_html)
            status = 'sent'
            campaign_progress[campaign_id]['sent'] += 1
            campaign_progress[campaign_id]['logs'].append({'email': email, 'name': name, 'status': 'sent', 'error': None})
            conn.execute("UPDATE campaigns SET sent=sent+1 WHERE id=?", (campaign_id,))
            log_activity(email, 'email_sent', f'Campanha: {campaign_id}', conn)
        except ClientError as e:
            err_msg = e.response['Error']['Message']
            status = 'error'
            campaign_progress[campaign_id]['errors'] += 1
            campaign_progress[campaign_id]['logs'].append({'email': email, 'name': name, 'status': 'error', 'error': err_msg})
            conn.execute("UPDATE campaigns SET errors=errors+1 WHERE id=?", (campaign_id,))

        conn.execute("INSERT INTO campaign_logs (campaign_id,contact_email,contact_name,status,error_message) VALUES (?,?,?,?,?)",
                     (campaign_id, email, name, status, campaign_progress[campaign_id]['logs'][-1]['error']))
        conn.commit()

    campaign_progress[campaign_id]['status'] = 'done'
    conn.execute("UPDATE campaigns SET status='done',finished_at=datetime('now','localtime') WHERE id=?", (campaign_id,))
    conn.commit()
    conn.close()

# ── Agendador de cadências ────────────────────────────────────────────────────

def processar_cadencias():
    conn = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pending = conn.execute('''
        SELECT sc.*, s.sender_email AS seq_sender
        FROM sequence_contacts sc
        JOIN sequences s ON s.id = sc.sequence_id
        WHERE sc.status = 'active' AND sc.next_send_at <= ?
    ''', (now,)).fetchall()

    if not pending:
        conn.close()
        return

    try:
        ses = get_ses_client()
    except Exception:
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
            conn.execute("UPDATE sequence_contacts SET status='stopped' WHERE id=?", (contact_id,))
            conn.commit()
            continue

        step = conn.execute('SELECT * FROM sequence_steps WHERE sequence_id=? AND step_number=?', (seq_id, step_num)).fetchone()
        if not step:
            conn.execute("UPDATE sequence_contacts SET status='finished',finished_at=datetime('now','localtime') WHERE id=?", (contact_id,))
            conn.commit()
            continue

        # Condição de envio
        should_send = True
        cond = step['condition']
        if cond in ('only_if_opened', 'only_if_not_opened'):
            opens = conn.execute('SELECT COUNT(*) FROM email_opens WHERE sequence_id=? AND contact_email=? AND step_number<?', (seq_id, email, step_num)).fetchone()[0]
            if cond == 'only_if_opened' and opens == 0: should_send = False
            elif cond == 'only_if_not_opened' and opens > 0: should_send = False

        if should_send:
            # A/B test
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
            click_prefix = f"{APP_URL}/track/click?email={quote(email)}&seq={seq_id}&step={step_num}&url="
            unsub_url = f"{APP_URL}/descadastrar?email={quote(email)}&seq={seq_id}"
            body = (use_body
                    + f'<img src="{pixel_url}" width="1" height="1" style="display:none;border:0" />'
                    + f'<div style="text-align:center;margin-top:24px;font-size:11px;color:#aaa"><a href="{unsub_url}" style="color:#aaa">Descadastrar</a></div>')

            try:
                send_email_ses(ses, sender, email, name, use_subject, body)
                conn.execute('INSERT INTO sequence_logs (sequence_id,contact_email,step_number,status,ab_version) VALUES (?,?,?,?,?)',
                             (seq_id, email, step_num, 'sent', ab_version))
                conn.execute('INSERT INTO send_analytics (contact_email,sent_at) VALUES (?,?)',
                             (email, now))
                log_activity(email, 'email_sent', f'Cadência {seq_id}, passo {step_num} (versão {ab_version})', conn)
            except ClientError as e:
                conn.execute('INSERT INTO sequence_logs (sequence_id,contact_email,step_number,status,error_message,ab_version) VALUES (?,?,?,?,?,?)',
                             (seq_id, email, step_num, 'error', e.response['Error']['Message'], ab_version))
        else:
            conn.execute('INSERT INTO sequence_logs (sequence_id,contact_email,step_number,status) VALUES (?,?,?,?)',
                         (seq_id, email, step_num, 'skipped'))

        # Avançar passo (com horário inteligente)
        next_step = conn.execute('SELECT * FROM sequence_steps WHERE sequence_id=? AND step_number=?', (seq_id, step_num + 1)).fetchone()
        if next_step:
            try:
                started_at = datetime.strptime(c['started_at'], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                started_at = datetime.now()
            next_dt = started_at + timedelta(days=next_step['day_offset'])
            best_hour = get_best_send_hour(email)
            if best_hour is not None:
                next_dt = next_dt.replace(hour=best_hour, minute=0, second=0)
            next_send = next_dt.strftime('%Y-%m-%d %H:%M:%S')
            conn.execute('UPDATE sequence_contacts SET current_step=?,next_send_at=? WHERE id=?', (step_num + 1, next_send, contact_id))
        else:
            conn.execute("UPDATE sequence_contacts SET status='finished',finished_at=datetime('now','localtime') WHERE id=?", (contact_id,))

        conn.commit()
    conn.close()

def calcular_scores_inativos():
    """Diminui score de contatos que não abriram em 7 dias."""
    conn = get_db()
    sete_dias_atras = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    inativos = conn.execute('''
        SELECT DISTINCT cs.email FROM contact_scores cs
        WHERE cs.score > 0
        AND cs.email NOT IN (
            SELECT DISTINCT contact_email FROM email_opens WHERE opened_at >= ?
        )
    ''', (sete_dias_atras,)).fetchall()
    for row in inativos:
        update_score(row['email'], -5, conn)
    conn.commit()
    conn.close()

# ── Rotas de campanhas ────────────────────────────────────────────────────────

@app.route('/')
def index():
    conn = get_db()
    campaigns = conn.execute("SELECT * FROM campaigns ORDER BY created_at DESC LIMIT 20").fetchall()
    total_contacts = conn.execute('SELECT COUNT(*) FROM contacts').fetchone()[0]
    blacklist_count = conn.execute('SELECT COUNT(*) FROM blacklist').fetchone()[0]
    hot_leads = conn.execute('SELECT COUNT(*) FROM contact_scores WHERE score > 50').fetchone()[0]
    sent_total = conn.execute("SELECT COUNT(*) FROM sequence_logs WHERE status='sent'").fetchone()[0]
    opens_total = conn.execute('SELECT COUNT(*) FROM email_opens').fetchone()[0]
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
        cursor = conn.execute(
            "INSERT INTO campaigns (name,subject,body,sender_email,total_contacts,status) VALUES (?,?,?,?,?,?)",
            (name, subject, body_html, sender, len(contacts), 'pending'))
        campaign_id = cursor.lastrowid
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
    campaign = conn.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    logs = conn.execute("SELECT * FROM campaign_logs WHERE campaign_id=? ORDER BY id DESC LIMIT 200", (campaign_id,)).fetchall()
    conn.close()
    if not campaign:
        flash('Campanha não encontrada.', 'danger')
        return redirect(url_for('index'))
    return render_template('campanha_detalhe.html', campaign=campaign, logs=logs)

@app.route('/api/progresso/<int:campaign_id>')
def api_progresso(campaign_id):
    prog = campaign_progress.get(campaign_id)
    if prog: return jsonify(prog)
    conn = get_db()
    c = conn.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    conn.close()
    if c:
        return jsonify({'total': c['total_contacts'], 'sent': c['sent'], 'errors': c['errors'], 'status': c['status'], 'logs': []})
    return jsonify({'error': 'não encontrado'}), 404

@app.route('/api/verificar-ses')
def api_verificar_ses():
    try:
        ses = get_ses_client()
        identities = ses.list_verified_email_addresses()
        domains = ses.list_identities(IdentityType='Domain')
        quota = ses.get_send_quota()
        return jsonify({'ok': True,
            'emails_verificados': identities.get('VerifiedEmailAddresses', []),
            'dominios': domains.get('Identities', []),
            'quota_diaria': quota.get('Max24HourSend', 0),
            'enviados_hoje': quota.get('SentLast24Hours', 0),
            'taxa_por_segundo': quota.get('MaxSendRate', 0)})
    except ClientError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 500
    except Exception as e:
        return jsonify({'ok': False, 'erro': f'AWS não configurado: {str(e)}'}), 500

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
        conn.execute("UPDATE signature SET name=?,body_html=?,updated_at=datetime('now','localtime') WHERE id=?", (name, body_html, existing['id']))
    else:
        conn.execute('INSERT INTO signature (name,body_html) VALUES (?,?)', (name, body_html))
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

@app.route('/api/debug-credenciais')
def debug_credenciais():
    def mascara(val):
        if not val: return '(vazia)'
        return f'{val[:4]}...{val[-4:]} (len={len(val)}, spaces={val != val.strip()})'
    return jsonify({
        'AWS_ACCESS_KEY_ID': mascara(os.environ.get('AWS_ACCESS_KEY_ID', '')),
        'AWS_SECRET_ACCESS_KEY': mascara(os.environ.get('AWS_SECRET_ACCESS_KEY', '')),
        'AWS_REGION': os.environ.get('AWS_REGION', '') or '(vazia)',
    })

# ── Tracking ──────────────────────────────────────────────────────────────────

@app.route('/track/open')
def track_open():
    email = request.args.get('email', '')
    seq_id = request.args.get('seq', type=int)
    step_num = request.args.get('step', type=int)
    if email and seq_id and step_num is not None:
        try:
            conn = get_db()
            conn.execute('INSERT INTO email_opens (sequence_id,contact_email,step_number) VALUES (?,?,?)', (seq_id, email, step_num))
            # Registra horário de abertura
            now = datetime.now()
            conn.execute(
                'UPDATE send_analytics SET opened_at=?,hour_of_day=?,day_of_week=? WHERE id=(SELECT id FROM send_analytics WHERE contact_email=? AND opened_at IS NULL ORDER BY sent_at DESC LIMIT 1)',
                (now.strftime('%Y-%m-%d %H:%M:%S'), now.hour, now.weekday(), email))
            # Score: +5 primeira abertura, +2 subsequentes
            opens_count = conn.execute('SELECT COUNT(*) FROM email_opens WHERE contact_email=?', (email,)).fetchone()[0]
            update_score(email, 5 if opens_count == 1 else 2, conn)
            log_activity(email, 'email_opened', f'Cadência {seq_id}, passo {step_num}', conn)
            conn.commit()
            conn.close()
        except Exception:
            pass
    return Response(PIXEL_GIF, mimetype='image/gif', headers={'Cache-Control': 'no-cache,no-store,must-revalidate'})

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
            conn.execute("UPDATE sequence_contacts SET status='unsubscribed' WHERE sequence_id=? AND contact_email=?", (seq_id, email))
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
        total = conn.execute('SELECT COUNT(*) FROM sequence_contacts WHERE sequence_id=?', (sid,)).fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM sequence_contacts WHERE sequence_id=? AND status='active'", (sid,)).fetchone()[0]
        finished = conn.execute("SELECT COUNT(*) FROM sequence_contacts WHERE sequence_id=? AND status='finished'", (sid,)).fetchone()[0]
        sent = conn.execute("SELECT COUNT(*) FROM sequence_logs WHERE sequence_id=? AND status='sent'", (sid,)).fetchone()[0]
        opens = conn.execute('SELECT COUNT(*) FROM email_opens WHERE sequence_id=?', (sid,)).fetchone()[0]
        result.append({'seq': s, 'total': total, 'active': active, 'finished': finished, 'open_rate': round(opens / sent * 100, 1) if sent > 0 else 0})
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
        cur = conn.execute('INSERT INTO sequences (name,description,sender_email) VALUES (?,?,?)', (name, description, sender))
        seq_id = cur.lastrowid
        for i, (day, subj, body, cond) in enumerate(zip(days, subjects, bodies, conditions), start=1):
            ab_b = ab_subjects_b[i-1] if i <= len(ab_subjects_b) else ''
            ab_bdy = ab_bodies_b[i-1] if i <= len(ab_bodies_b) else ''
            ab_r = int(ab_ratios[i-1]) if i <= len(ab_ratios) and ab_ratios[i-1].isdigit() else 50
            conn.execute(
                'INSERT INTO sequence_steps (sequence_id,step_number,day_offset,subject,body_html,condition,ab_subject_b,ab_body_b,ab_ratio) VALUES (?,?,?,?,?,?,?,?,?)',
                (seq_id, i, int(day or 0), subj, body, cond or 'always', ab_b or None, ab_bdy or None, ab_r))
        conn.commit()
        conn.close()
        flash('Cadência criada!', 'success')
        return redirect(url_for('cadencia_detalhe', seq_id=seq_id))
    return render_template('nova_cadencia.html', seq=None, steps=[], editing=False)

@app.route('/cadencias/<int:seq_id>')
def cadencia_detalhe(seq_id):
    conn = get_db()
    seq = conn.execute('SELECT * FROM sequences WHERE id=?', (seq_id,)).fetchone()
    if not seq:
        flash('Cadência não encontrada.', 'danger'); conn.close(); return redirect(url_for('cadencias'))

    steps = conn.execute('SELECT * FROM sequence_steps WHERE sequence_id=? ORDER BY step_number', (seq_id,)).fetchall()
    contacts = conn.execute('SELECT sc.*, cs.score FROM sequence_contacts sc LEFT JOIN contact_scores cs ON cs.email=sc.contact_email WHERE sc.sequence_id=? ORDER BY sc.started_at DESC LIMIT 200', (seq_id,)).fetchall()

    total = conn.execute('SELECT COUNT(*) FROM sequence_contacts WHERE sequence_id=?', (seq_id,)).fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM sequence_contacts WHERE sequence_id=? AND status='active'", (seq_id,)).fetchone()[0]
    finished = conn.execute("SELECT COUNT(*) FROM sequence_contacts WHERE sequence_id=? AND status='finished'", (seq_id,)).fetchone()[0]
    sent_total = conn.execute("SELECT COUNT(*) FROM sequence_logs WHERE sequence_id=? AND status='sent'", (seq_id,)).fetchone()[0]
    opens_total = conn.execute('SELECT COUNT(*) FROM email_opens WHERE sequence_id=?', (seq_id,)).fetchone()[0]
    open_rate = round(opens_total / sent_total * 100, 1) if sent_total > 0 else 0

    step_metrics = []
    for st in steps:
        sn = st['step_number']
        s_a = conn.execute("SELECT COUNT(*) FROM sequence_logs WHERE sequence_id=? AND step_number=? AND status='sent' AND (ab_version='A' OR ab_version IS NULL)", (seq_id, sn)).fetchone()[0]
        s_b = conn.execute("SELECT COUNT(*) FROM sequence_logs WHERE sequence_id=? AND step_number=? AND status='sent' AND ab_version='B'", (seq_id, sn)).fetchone()[0]
        o_a = conn.execute('SELECT COUNT(*) FROM email_opens WHERE sequence_id=? AND step_number=?', (seq_id, sn)).fetchone()[0]
        step_metrics.append({'step': st, 'sent_a': s_a, 'sent_b': s_b, 'opens': o_a,
                              'open_rate': round(o_a / (s_a + s_b) * 100, 1) if (s_a + s_b) > 0 else 0})
    conn.close()
    return render_template('cadencia_detalhe.html', seq=seq, steps=steps, contacts=contacts,
                           total=total, active=active, finished=finished,
                           sent_total=sent_total, open_rate=open_rate, step_metrics=step_metrics)

@app.route('/cadencias/<int:seq_id>/editar', methods=['GET', 'POST'])
def editar_cadencia(seq_id):
    conn = get_db()
    seq = conn.execute('SELECT * FROM sequences WHERE id=?', (seq_id,)).fetchone()
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

        conn.execute('UPDATE sequences SET name=?,description=?,sender_email=? WHERE id=?', (name, description, sender, seq_id))
        conn.execute('DELETE FROM sequence_steps WHERE sequence_id=?', (seq_id,))
        for i, (day, subj, body, cond) in enumerate(zip(days, subjects, bodies, conditions), start=1):
            ab_b = ab_subjects_b[i-1] if i <= len(ab_subjects_b) else ''
            ab_bdy = ab_bodies_b[i-1] if i <= len(ab_bodies_b) else ''
            ab_r = int(ab_ratios[i-1]) if i <= len(ab_ratios) and ab_ratios[i-1].isdigit() else 50
            conn.execute(
                'INSERT INTO sequence_steps (sequence_id,step_number,day_offset,subject,body_html,condition,ab_subject_b,ab_body_b,ab_ratio) VALUES (?,?,?,?,?,?,?,?,?)',
                (seq_id, i, int(day or 0), subj, body, cond or 'always', ab_b or None, ab_bdy or None, ab_r))
        conn.commit()
        conn.close()
        flash('Cadência atualizada!', 'success')
        return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

    steps = conn.execute('SELECT * FROM sequence_steps WHERE sequence_id=? ORDER BY step_number', (seq_id,)).fetchall()
    conn.close()
    return render_template('nova_cadencia.html', seq=seq, steps=steps, editing=True)

@app.route('/cadencias/<int:seq_id>/adicionar-contatos', methods=['POST'])
def adicionar_contatos_cadencia(seq_id):
    conn = get_db()
    seq = conn.execute('SELECT * FROM sequences WHERE id=?', (seq_id,)).fetchone()
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

    # Filtro por tag
    if tag_filter:
        all_contacts = [c for c in all_contacts if tag_filter.lower() in (c.get('tags') or '').lower()]

    first_step = conn.execute('SELECT * FROM sequence_steps WHERE sequence_id=? ORDER BY step_number LIMIT 1', (seq_id,)).fetchone()
    if not first_step:
        flash('Adicione pelo menos um passo antes de importar.', 'danger'); conn.close(); return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

    now = datetime.now()
    next_send = (now + timedelta(days=first_step['day_offset'])).strftime('%Y-%m-%d %H:%M:%S')
    added = 0
    for c in all_contacts:
        if is_blacklisted(c['email'], conn):
            continue
        existing = conn.execute('SELECT id FROM sequence_contacts WHERE sequence_id=? AND contact_email=?', (seq_id, c['email'])).fetchone()
        if not existing:
            conn.execute('INSERT INTO sequence_contacts (sequence_id,contact_email,contact_name,current_step,next_send_at) VALUES (?,?,?,?,?)',
                         (seq_id, c['email'], c['name'], first_step['step_number'], next_send))
            upsert_contact(c['email'], c['name'], c.get('tags', ''), conn)
            added += 1

    conn.commit(); conn.close()
    flash(f'{added} contatos adicionados à cadência.', 'success')
    return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

@app.route('/cadencias/<int:seq_id>/pausar', methods=['POST'])
def pausar_cadencia(seq_id):
    conn = get_db()
    conn.execute("UPDATE sequence_contacts SET status='paused' WHERE sequence_id=? AND status='active'", (seq_id,))
    conn.execute("UPDATE sequences SET status='paused' WHERE id=?", (seq_id,))
    conn.commit(); conn.close()
    flash('Cadência pausada.', 'warning')
    return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

@app.route('/cadencias/<int:seq_id>/retomar', methods=['POST'])
def retomar_cadencia(seq_id):
    conn = get_db()
    conn.execute("UPDATE sequence_contacts SET status='active' WHERE sequence_id=? AND status='paused'", (seq_id,))
    conn.execute("UPDATE sequences SET status='active' WHERE id=?", (seq_id,))
    conn.commit(); conn.close()
    flash('Cadência retomada.', 'success')
    return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

@app.route('/cadencias/<int:seq_id>/contato/<path:email>/parar', methods=['POST'])
def parar_contato_cadencia(seq_id, email):
    conn = get_db()
    conn.execute("UPDATE sequence_contacts SET status='stopped' WHERE sequence_id=? AND contact_email=?", (seq_id, email))
    conn.commit(); conn.close()
    flash(f'Cadência parada para {email}.', 'info')
    return redirect(url_for('cadencia_detalhe', seq_id=seq_id))

@app.route('/api/cadencias/<int:seq_id>/metricas')
def api_cadencia_metricas(seq_id):
    conn = get_db()
    steps = conn.execute('SELECT * FROM sequence_steps WHERE sequence_id=? ORDER BY step_number', (seq_id,)).fetchall()
    result = []
    for st in steps:
        sn = st['step_number']
        sent = conn.execute("SELECT COUNT(*) FROM sequence_logs WHERE sequence_id=? AND step_number=? AND status='sent'", (seq_id, sn)).fetchone()[0]
        opens = conn.execute('SELECT COUNT(*) FROM email_opens WHERE sequence_id=? AND step_number=?', (seq_id, sn)).fetchone()[0]
        result.append({'step': sn, 'day_offset': st['day_offset'], 'subject': st['subject'], 'sent': sent, 'opens': opens, 'open_rate': round(opens / sent * 100, 1) if sent > 0 else 0})
    conn.close()
    return jsonify(result)

# ── CRM — Contatos ────────────────────────────────────────────────────────────

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
    if status_filter: query += ' AND c.status=?'; params.append(status_filter)
    if tag_filter: query += ' AND c.tags LIKE ?'; params.append(f'%{tag_filter}%')
    if search: query += ' AND (c.email LIKE ? OR c.name LIKE ? OR c.company LIKE ?)'; params += [f'%{search}%', f'%{search}%', f'%{search}%']
    if sort == 'score': query += ' ORDER BY current_score DESC'
    elif sort == 'name': query += ' ORDER BY c.name ASC'
    else: query += ' ORDER BY c.created_at DESC'

    contatos = conn.execute(query, params).fetchall()
    all_tags = set()
    for c in conn.execute('SELECT tags FROM contacts WHERE tags IS NOT NULL AND tags != ""').fetchall():
        for t in c['tags'].split(','):
            if t.strip(): all_tags.add(t.strip())
    conn.close()
    return render_template('contatos.html', contatos=contatos, all_tags=sorted(all_tags),
                           status_filter=status_filter, tag_filter=tag_filter, search=search, sort=sort)

@app.route('/contatos/<path:email>', methods=['GET', 'POST'])
def contato_perfil(email):
    conn = get_db()
    contact = conn.execute('SELECT c.*, COALESCE(cs.score,0) as current_score FROM contacts c LEFT JOIN contact_scores cs ON cs.email=c.email WHERE c.email=?', (email,)).fetchone()
    if not contact:
        flash('Contato não encontrado.', 'danger'); conn.close(); return redirect(url_for('lista_contatos'))

    if request.method == 'POST':
        fields = ['name', 'phone', 'company', 'position', 'status', 'tags', 'notes']
        updates = {f: request.form.get(f, '').strip() for f in fields}
        conn.execute("UPDATE contacts SET name=?,phone=?,company=?,position=?,status=?,tags=?,notes=?,updated_at=datetime('now','localtime') WHERE email=?",
                     (*updates.values(), email))
        conn.commit()
        log_activity(email, 'contact_updated', 'Dados atualizados pelo usuário', conn)
        conn.commit()
        conn.close()
        flash('Contato atualizado!', 'success')
        return redirect(url_for('contato_perfil', email=email))

    activities = conn.execute('SELECT * FROM contact_activities WHERE contact_email=? ORDER BY created_at DESC LIMIT 50', (email,)).fetchall()
    cadencias_do_contato = conn.execute('''SELECT sc.*, s.name as seq_name FROM sequence_contacts sc
        JOIN sequences s ON s.id=sc.sequence_id WHERE sc.contact_email=? ORDER BY sc.started_at DESC''', (email,)).fetchall()
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
        'SELECT c.*, COALESCE(cs.score,0) as current_score FROM contacts c LEFT JOIN contact_scores cs ON cs.email=c.email WHERE c.tags LIKE ?',
        (f'%{tag}%',)
    ).fetchall()
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
    conn.execute('DELETE FROM blacklist WHERE email=?', (email,))
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
    rows = [(c['id'], c['name'], c['subject'], c['sender_email'], c['total_contacts'], c['sent'], c['errors'], c['status'], c['created_at']) for c in camps]
    return _csv_response(rows, ['ID','Nome','Assunto','Remetente','Total','Enviados','Erros','Status','Criado em'], 'campanhas.csv')

@app.route('/exportar/cadencia/<int:seq_id>')
def exportar_cadencia(seq_id):
    conn = get_db()
    contacts = conn.execute('''SELECT sc.contact_email, sc.contact_name, sc.current_step, sc.status, sc.next_send_at, sc.started_at, sc.finished_at, COALESCE(cs.score,0) as score
        FROM sequence_contacts sc LEFT JOIN contact_scores cs ON cs.email=sc.contact_email WHERE sc.sequence_id=?''', (seq_id,)).fetchall()
    conn.close()
    rows = [(c['contact_email'], c['contact_name'], c['current_step'], c['status'], c['next_send_at'], c['started_at'], c['finished_at'], c['score']) for c in contacts]
    return _csv_response(rows, ['Email','Nome','Passo Atual','Status','Próximo Envio','Iniciado em','Finalizado em','Score'], f'cadencia_{seq_id}.csv')

@app.route('/exportar/contatos')
def exportar_contatos():
    conn = get_db()
    contatos = conn.execute('SELECT c.*, COALESCE(cs.score,0) as current_score FROM contacts c LEFT JOIN contact_scores cs ON cs.email=c.email ORDER BY c.name').fetchall()
    conn.close()
    rows = [(c['email'], c['name'], c['phone'], c['company'], c['position'], c['status'], c['current_score'], c['tags'], c['created_at']) for c in contatos]
    return _csv_response(rows, ['Email','Nome','Telefone','Empresa','Cargo','Status','Score','Tags','Criado em'], 'contatos.csv')

# ── Dashboard analytics ────────────────────────────────────────────────────────

@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    conn = get_db()

    # Envios por dia (últimos 30 dias)
    rows = conn.execute('''
        SELECT date(sent_at) as d, COUNT(*) as c FROM (
            SELECT sent_at FROM campaign_logs WHERE status='sent'
            UNION ALL
            SELECT sent_at FROM sequence_logs WHERE status='sent'
        ) WHERE date(sent_at) >= date('now','-30 days')
        GROUP BY d ORDER BY d
    ''').fetchall()
    sends_by_day = [{'date': r['d'], 'count': r['c']} for r in rows]

    # Taxa de abertura por cadência (top 8)
    seqs = conn.execute('''
        SELECT s.name,
            COUNT(DISTINCT sl.contact_email) as sent,
            COUNT(DISTINCT eo.contact_email) as opened
        FROM sequences s
        LEFT JOIN sequence_logs sl ON sl.sequence_id=s.id AND sl.status='sent'
        LEFT JOIN email_opens eo ON eo.sequence_id=s.id
        GROUP BY s.id ORDER BY sent DESC LIMIT 8
    ''').fetchall()
    seq_stats = [{'name': s['name'], 'sent': s['sent'], 'opened': s['opened'],
                  'rate': round(s['opened']/s['sent']*100, 1) if s['sent'] > 0 else 0} for s in seqs]

    # Heatmap (hora x dia da semana)
    heatmap_rows = conn.execute('''
        SELECT hour_of_day, day_of_week, COUNT(*) as cnt
        FROM send_analytics WHERE hour_of_day IS NOT NULL GROUP BY hour_of_day, day_of_week
    ''').fetchall()
    heatmap = {}
    for r in heatmap_rows:
        heatmap[f"{r['day_of_week']}-{r['hour_of_day']}"] = r['cnt']

    conn.close()
    return jsonify({'sends_by_day': sends_by_day, 'seq_stats': seq_stats, 'heatmap': heatmap})

init_db()

if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(processar_cadencias, 'interval', minutes=30)
    _scheduler.add_job(calcular_scores_inativos, 'interval', hours=24)
    _scheduler.start()

if __name__ == '__main__':
    print("\nASA Email Marketing rodando em: http://127.0.0.1:5000\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
