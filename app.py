import os
import csv
import json
import sqlite3
import threading
import io
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'campaigns.db')
ALLOWED_EXTENSIONS = {'csv'}
AWS_REGION = os.environ.get('AWS_REGION', 'sa-east-1')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max

# --- Banco de dados ---
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            sender_email TEXT NOT NULL,
            total_contacts INTEGER DEFAULT 0,
            sent INTEGER DEFAULT 0,
            errors INTEGER DEFAULT 0,
            bounces INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            finished_at TEXT
        );

        CREATE TABLE IF NOT EXISTS campaign_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            contact_email TEXT NOT NULL,
            contact_name TEXT,
            status TEXT NOT NULL,
            error_message TEXT,
            sent_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
        );
    ''')
    conn.commit()
    conn.close()

# Estado em memória para progresso em tempo real
campaign_progress = {}

# --- Utilitários ---

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_csv(filepath):
    contacts = []
    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
    for enc in encodings:
        try:
            with open(filepath, newline='', encoding=enc) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Tenta variações comuns de nome de coluna
                    name = (row.get('nome') or row.get('Nome') or row.get('name') or
                            row.get('Name') or row.get('NOME') or '').strip()
                    email = (row.get('email') or row.get('Email') or row.get('EMAIL') or
                             row.get('e-mail') or row.get('E-mail') or '').strip()
                    if email:
                        contacts.append({'name': name, 'email': email})
            return contacts
        except (UnicodeDecodeError, Exception):
            continue
    return contacts

def get_ses_client():
    return boto3.client('ses', region_name=AWS_REGION, aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'), aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'))

def send_email_ses(ses_client, sender, recipient_email, recipient_name, subject, body_html):
    # Personaliza com o nome do contato
    personalized_subject = subject.replace('{nome}', recipient_name or 'Cliente')
    personalized_body = body_html.replace('{nome}', recipient_name or 'Cliente')

    response = ses_client.send_email(
        Source=sender,
        Destination={'ToAddresses': [recipient_email]},
        Message={
            'Subject': {'Data': personalized_subject, 'Charset': 'UTF-8'},
            'Body': {
                'Html': {'Data': personalized_body, 'Charset': 'UTF-8'},
                'Text': {
                    'Data': personalized_body.replace('<br>', '\n').replace('<br/>', '\n'),
                    'Charset': 'UTF-8'
                }
            }
        }
    )
    return response

def run_campaign(campaign_id, contacts, sender, subject, body_html):
    conn = get_db()
    ses = get_ses_client()

    campaign_progress[campaign_id] = {
        'total': len(contacts), 'sent': 0, 'errors': 0,
        'status': 'running', 'logs': []
    }

    conn.execute("UPDATE campaigns SET status='running', total_contacts=? WHERE id=?",
                 (len(contacts), campaign_id))
    conn.commit()

    for contact in contacts:
        email = contact['email']
        name = contact.get('name', '')
        try:
            send_email_ses(ses, sender, email, name, subject, body_html)
            status = 'sent'
            campaign_progress[campaign_id]['sent'] += 1
            campaign_progress[campaign_id]['logs'].append(
                {'email': email, 'name': name, 'status': 'sent', 'error': None}
            )
            conn.execute(
                "UPDATE campaigns SET sent=sent+1 WHERE id=?", (campaign_id,))
        except ClientError as e:
            err_msg = e.response['Error']['Message']
            status = 'error'
            campaign_progress[campaign_id]['errors'] += 1
            campaign_progress[campaign_id]['logs'].append(
                {'email': email, 'name': name, 'status': 'error', 'error': err_msg}
            )
            conn.execute(
                "UPDATE campaigns SET errors=errors+1 WHERE id=?", (campaign_id,))

        conn.execute(
            "INSERT INTO campaign_logs (campaign_id,contact_email,contact_name,status,error_message)"
            " VALUES (?,?,?,?,?)",
            (campaign_id, email, name, status,
             campaign_progress[campaign_id]['logs'][-1]['error'])
        )
        conn.commit()

    # Finaliza
    campaign_progress[campaign_id]['status'] = 'done'
    conn.execute(
        "UPDATE campaigns SET status='done', finished_at=datetime('now','localtime') WHERE id=?",
        (campaign_id,))
    conn.commit()
    conn.close()

# --- Rotas ---

@app.route('/')
def index():
    conn = get_db()
    campaigns = conn.execute(
        "SELECT * FROM campaigns ORDER BY created_at DESC LIMIT 20").fetchall()
    conn.close()
    return render_template('index.html', campaigns=campaigns)

@app.route('/nova-campanha', methods=['GET', 'POST'])
def nova_campanha():
    if request.method == 'POST':
        name = request.form.get('campaign_name', '').strip()
        sender = request.form.get('sender_email', '').strip()
        subject = request.form.get('subject', '').strip()
        body_html = request.form.get('body_html', '').strip()

        if not all([name, sender, subject, body_html]):
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('nova_campanha'))

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
            flash('Nenhum contato válido encontrado no CSV. Verifique as colunas nome e email.', 'danger')
            return redirect(url_for('nova_campanha'))

        conn = get_db()
        cursor = conn.execute(
            "INSERT INTO campaigns (name, subject, body, sender_email, total_contacts, status)"
            " VALUES (?,?,?,?,?,?)",
            (name, subject, body_html, sender, len(contacts), 'pending')
        )
        campaign_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Dispara em thread separada
        t = threading.Thread(
            target=run_campaign,
            args=(campaign_id, contacts, sender, subject, body_html),
            daemon=True
        )
        t.start()

        flash(f'Campanha iniciada! Enviando para {len(contacts)} contatos.', 'success')
        return redirect(url_for('campanha_detalhe', campaign_id=campaign_id))

    return render_template('nova_campanha.html')

@app.route('/campanha/<int:campaign_id>')
def campanha_detalhe(campaign_id):
    conn = get_db()
    campaign = conn.execute(
        "SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    logs = conn.execute(
        "SELECT * FROM campaign_logs WHERE campaign_id=? ORDER BY id DESC LIMIT 200",
        (campaign_id,)).fetchall()
    conn.close()
    if not campaign:
        flash('Campanha não encontrada.', 'danger')
        return redirect(url_for('index'))
    return render_template('campanha_detalhe.html', campaign=campaign, logs=logs)

@app.route('/api/progresso/<int:campaign_id>')
def api_progresso(campaign_id):
    prog = campaign_progress.get(campaign_id)
    if prog:
        return jsonify(prog)
    # Se não tem em memória, busca no banco
    conn = get_db()
    c = conn.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    conn.close()
    if c:
        return jsonify({
            'total': c['total_contacts'], 'sent': c['sent'],
            'errors': c['errors'], 'status': c['status'], 'logs': []
        })
    return jsonify({'error': 'não encontrado'}), 404

@app.route('/api/verificar-ses')
def api_verificar_ses():
    try:
        ses = get_ses_client()
        identities = ses.list_verified_email_addresses()
        domains = ses.list_identities(IdentityType='Domain')
        quota = ses.get_send_quota()
        return jsonify({
            'ok': True,
            'emails_verificados': identities.get('VerifiedEmailAddresses', []),
            'dominios': domains.get('Identities', []),
            'quota_diaria': quota.get('Max24HourSend', 0),
            'enviados_hoje': quota.get('SentLast24Hours', 0),
            'taxa_por_segundo': quota.get('MaxSendRate', 0)
        })
    except ClientError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 500
    except Exception as e:
        return jsonify({'ok': False, 'erro': f'AWS CLI não configurado: {str(e)}'}), 500

@app.route('/configuracoes')
def configuracoes():
    return render_template('configuracoes.html')

init_db()

if __name__ == '__main__':
    print("\nASA Email Marketing rodando em: http://127.0.0.1:5000\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
