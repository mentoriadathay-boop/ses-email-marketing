import imaplib
import smtplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime, formataddr
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import re
from datetime import datetime


def _decode_hdr(raw):
    if not raw:
        return ''
    parts = decode_header(raw)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or 'utf-8', errors='replace'))
        else:
            decoded.append(data)
    return ''.join(decoded)


def _parse_addr(raw):
    if not raw:
        return '', ''
    decoded = _decode_hdr(raw)
    match = re.match(r'^(.*?)\s*<(.+?)>\s*$', decoded)
    if match:
        return match.group(1).strip().strip('"'), match.group(2).strip()
    return '', decoded.strip()


def imap_connect(server, port, email_addr, password, use_ssl=True):
    if use_ssl:
        conn = imaplib.IMAP4_SSL(server, port, timeout=30)
    else:
        conn = imaplib.IMAP4(server, port, timeout=30)
    conn.login(email_addr, password)
    return conn


def list_folders(imap_conn):
    status, folder_list = imap_conn.list()
    folders = []
    if status == 'OK':
        for item in folder_list:
            if isinstance(item, bytes):
                match = re.search(rb'"([^"]*)"$|(\S+)$', item)
                if match:
                    name = (match.group(1) or match.group(2)).decode('utf-8', errors='replace')
                    folders.append(name)
    return folders


def detect_sent_folder(imap_conn):
    folders = list_folders(imap_conn)
    candidates = ['Sent', 'INBOX.Sent', 'Sent Messages', 'Sent Items',
                  '[Gmail]/Sent Mail', 'INBOX.Sent Messages', 'Enviados']
    for c in candidates:
        if c in folders:
            return c
    for f in folders:
        if 'sent' in f.lower():
            return f
    return 'Sent'


def detect_spam_folder(imap_conn):
    folders = list_folders(imap_conn)
    candidates = ['Spam', 'INBOX.Spam', 'Junk', 'INBOX.Junk', 'Junk E-mail',
                  '[Gmail]/Spam', 'Bulk Mail', 'INBOX.Bulk Mail']
    for c in candidates:
        if c in folders:
            return c
    for f in folders:
        if 'spam' in f.lower() or 'junk' in f.lower():
            return f
    return 'Spam'


def fetch_mailbox(imap_conn, folder='INBOX', page=1, per_page=25, order='desc'):
    status, _ = imap_conn.select(folder, readonly=True)
    if status != 'OK':
        return [], 0

    status, data = imap_conn.uid('search', None, 'ALL')
    if status != 'OK' or not data[0]:
        return [], 0

    uids = data[0].split()
    total = len(uids)
    if order == 'desc':
        uids.reverse()

    start = (page - 1) * per_page
    end = start + per_page
    page_uids = uids[start:end]

    if not page_uids:
        return [], total

    uid_str = b','.join(page_uids)
    status, msg_data = imap_conn.uid('fetch', uid_str,
                                      '(FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)])')
    if status != 'OK':
        return [], total

    messages = []
    i = 0
    while i < len(msg_data):
        if isinstance(msg_data[i], tuple):
            meta_line = msg_data[i][0].decode('utf-8', errors='replace')
            header_bytes = msg_data[i][1]

            uid_match = re.search(r'UID\s+(\d+)', meta_line)
            uid = uid_match.group(1) if uid_match else '0'
            is_read = b'\\Seen' in msg_data[i][0] if isinstance(msg_data[i][0], bytes) else '\\Seen' in meta_line

            msg = email.message_from_bytes(header_bytes)
            from_name, from_email_addr = _parse_addr(msg.get('From', ''))
            subject = _decode_hdr(msg.get('Subject', '(sem assunto)'))
            date_str = msg.get('Date', '')
            try:
                date = parsedate_to_datetime(date_str)
            except Exception:
                date = datetime.now()

            messages.append({
                'uid': uid,
                'from_name': from_name,
                'from_email': from_email_addr,
                'subject': subject,
                'date': date,
                'is_read': is_read,
                'message_id': msg.get('Message-ID', ''),
            })
        i += 1

    if page_uids:
        uid_order = {uid.decode('utf-8'): idx for idx, uid in enumerate(page_uids)}
        messages.sort(key=lambda m: uid_order.get(m['uid'], 0))

    return messages, total


def fetch_email(imap_conn, uid, folder='INBOX'):
    status, _ = imap_conn.select(folder)
    if status != 'OK':
        return None

    imap_conn.uid('store', uid.encode() if isinstance(uid, str) else uid, '+FLAGS', '\\Seen')

    status, data = imap_conn.uid('fetch', uid.encode() if isinstance(uid, str) else uid, '(RFC822)')
    if status != 'OK' or not data or not data[0]:
        return None

    raw = data[0][1] if isinstance(data[0], tuple) else data[0]
    msg = email.message_from_bytes(raw)

    from_name, from_email_addr = _parse_addr(msg.get('From', ''))
    to_raw = msg.get('To', '')
    cc_raw = msg.get('Cc', '')
    subject = _decode_hdr(msg.get('Subject', '(sem assunto)'))
    date_str = msg.get('Date', '')
    try:
        date = parsedate_to_datetime(date_str)
    except Exception:
        date = datetime.now()

    text_body = ''
    html_body = ''
    attachments = []
    att_index = 0

    for part in msg.walk():
        content_type = part.get_content_type()
        disposition = str(part.get('Content-Disposition', ''))

        if 'attachment' in disposition:
            filename = part.get_filename()
            if filename:
                filename = _decode_hdr(filename)
            else:
                filename = f'attachment_{att_index}'
            size = len(part.get_payload(decode=True) or b'')
            attachments.append({
                'index': att_index,
                'filename': filename,
                'content_type': content_type,
                'size': size,
            })
            att_index += 1
        elif content_type == 'text/plain' and not text_body:
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or 'utf-8'
            text_body = payload.decode(charset, errors='replace') if payload else ''
        elif content_type == 'text/html' and not html_body:
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or 'utf-8'
            html_body = payload.decode(charset, errors='replace') if payload else ''

    return {
        'uid': uid,
        'from_name': from_name,
        'from_email': from_email_addr,
        'to': _decode_hdr(to_raw),
        'cc': _decode_hdr(cc_raw),
        'subject': subject,
        'date': date,
        'text_body': text_body,
        'html_body': html_body,
        'attachments': attachments,
        'message_id': msg.get('Message-ID', ''),
        'references': msg.get('References', ''),
    }


def fetch_attachment(imap_conn, uid, attachment_index, folder='INBOX'):
    status, _ = imap_conn.select(folder, readonly=True)
    if status != 'OK':
        return None, None, None

    status, data = imap_conn.uid('fetch', uid.encode() if isinstance(uid, str) else uid, '(RFC822)')
    if status != 'OK' or not data or not data[0]:
        return None, None, None

    raw = data[0][1] if isinstance(data[0], tuple) else data[0]
    msg = email.message_from_bytes(raw)

    idx = 0
    for part in msg.walk():
        disposition = str(part.get('Content-Disposition', ''))
        if 'attachment' in disposition:
            if idx == attachment_index:
                filename = _decode_hdr(part.get_filename() or f'attachment_{idx}')
                content_type = part.get_content_type()
                payload = part.get_payload(decode=True)
                return filename, content_type, payload
            idx += 1

    return None, None, None


def send_email(smtp_server, smtp_port, email_addr, password,
               to, subject, body_html, cc=None, bcc=None,
               reply_to_msg_id=None, references=None, attachments=None):
    msg = MIMEMultipart('mixed')
    msg['From'] = email_addr
    msg['To'] = to
    msg['Subject'] = subject
    if cc:
        msg['Cc'] = cc
    if reply_to_msg_id:
        msg['In-Reply-To'] = reply_to_msg_id
        msg['References'] = (references + ' ' + reply_to_msg_id).strip() if references else reply_to_msg_id

    html_part = MIMEText(body_html, 'html', 'utf-8')
    msg.attach(html_part)

    if attachments:
        for file_obj in attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(file_obj.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment', filename=file_obj.filename)
            msg.attach(part)

    recipients = [addr.strip() for addr in to.split(',')]
    if cc:
        recipients += [addr.strip() for addr in cc.split(',')]
    if bcc:
        recipients += [addr.strip() for addr in bcc.split(',')]

    if smtp_port == 465:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
    else:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
        server.starttls()

    server.login(email_addr, password)
    server.sendmail(email_addr, recipients, msg.as_string())
    server.quit()


def mark_read(imap_conn, uid, folder='INBOX'):
    imap_conn.select(folder)
    imap_conn.uid('store', uid.encode() if isinstance(uid, str) else uid, '+FLAGS', '\\Seen')


def mark_unread(imap_conn, uid, folder='INBOX'):
    imap_conn.select(folder)
    imap_conn.uid('store', uid.encode() if isinstance(uid, str) else uid, '-FLAGS', '\\Seen')


def detect_trash_folder(imap_conn):
    folders = list_folders(imap_conn)
    candidates = ['Trash', 'INBOX.Trash', 'Deleted Messages', 'Deleted Items',
                  '[Gmail]/Trash', 'INBOX.Deleted Messages', 'Lixeira']
    for c in candidates:
        if c in folders:
            return c
    for f in folders:
        if 'trash' in f.lower() or 'lixeira' in f.lower() or 'deleted' in f.lower():
            return f
    return 'Trash'


def detect_drafts_folder(imap_conn):
    folders = list_folders(imap_conn)
    candidates = ['Drafts', 'INBOX.Drafts', 'Draft', '[Gmail]/Drafts',
                  'INBOX.Draft', 'Rascunhos']
    for c in candidates:
        if c in folders:
            return c
    for f in folders:
        if 'draft' in f.lower() or 'rascunho' in f.lower():
            return f
    return 'Drafts'


def move_to_trash(imap_conn, uid, folder='INBOX', trash_folder='Trash'):
    uid_b = uid.encode() if isinstance(uid, str) else uid
    imap_conn.select(folder)
    status, _ = imap_conn.uid('copy', uid_b, trash_folder)
    if status != 'OK':
        imap_conn.create(trash_folder)
        status, _ = imap_conn.uid('copy', uid_b, trash_folder)
    if status == 'OK':
        imap_conn.uid('store', uid_b, '+FLAGS', '\\Deleted')
        imap_conn.expunge()
    else:
        raise Exception(f'Falha ao copiar para {trash_folder}: {status}')


def move_to_trash_bulk(imap_conn, uids, folder='INBOX', trash_folder='Trash'):
    imap_conn.select(folder)
    created = False
    for uid in uids:
        uid_b = uid.encode() if isinstance(uid, str) else uid
        status, _ = imap_conn.uid('copy', uid_b, trash_folder)
        if status != 'OK' and not created:
            imap_conn.create(trash_folder)
            created = True
            status, _ = imap_conn.uid('copy', uid_b, trash_folder)
        if status == 'OK':
            imap_conn.uid('store', uid_b, '+FLAGS', '\\Deleted')
    imap_conn.expunge()


def delete_email(imap_conn, uid, folder='INBOX'):
    imap_conn.select(folder)
    imap_conn.uid('store', uid.encode() if isinstance(uid, str) else uid, '+FLAGS', '\\Deleted')
    imap_conn.expunge()


def save_draft(imap_conn, email_addr, to, subject, body_html, drafts_folder='Drafts'):
    msg = MIMEMultipart('mixed')
    msg['From'] = email_addr
    msg['To'] = to or ''
    msg['Subject'] = subject or '(sem assunto)'
    msg['Date'] = email.utils.formatdate(localtime=True)
    msg.attach(MIMEText(body_html or '', 'html', 'utf-8'))
    imap_conn.append(drafts_folder, '\\Draft', None, msg.as_bytes())


def format_size(size_bytes):
    if size_bytes < 1024:
        return f'{size_bytes} B'
    elif size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.1f} KB'
    else:
        return f'{size_bytes / (1024 * 1024):.1f} MB'
