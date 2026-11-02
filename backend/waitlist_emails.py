"""Resend delivery, durable signup receipts and daily private subscriber reports."""
import asyncio
import base64
import csv
import io
import logging
import os
from datetime import datetime, timedelta, timezone
from html import escape
from zoneinfo import ZoneInfo

import requests
from pymongo import ReturnDocument

logger = logging.getLogger(__name__)
RESEND_API_URL = 'https://api.resend.com/emails'
ROMANIA = ZoneInfo('Europe/Bucharest')


def _next_morning(now):
    local = now.astimezone(ROMANIA)
    morning = local.replace(hour=9, minute=0, second=0, microsecond=0)
    if morning <= local:
        morning += timedelta(days=1)
    return morning.astimezone(timezone.utc)


def _frame(title, body):
    return (
        '<div style="background:#fff8f3;padding:32px 16px;font-family:Arial,sans-serif;color:#211d25">'
        '<div style="max-width:560px;margin:auto;background:white;border:1px solid #eedfd7;border-radius:24px;padding:32px">'
        '<p style="font-size:23px;font-weight:bold">Valandala<span style="color:#ff7a30">.</span></p>'
        f'<h1 style="font-size:27px;line-height:1.25">{escape(title)}</h1>'
        f'<div style="line-height:1.8;font-size:15px">{body}</div>'
        '<p style="border-top:1px solid #eedfd7;padding-top:18px;color:#756d76;font-size:12px">'
        'Ai o întrebare sau vrei să te retragem de pe listă? Scrie-ne la '
        '<a href="mailto:info@valandala.ro" style="color:#c65319">info@valandala.ro</a>.</p></div></div>'
    )


async def queue_email(db, key, payload):
    await db.waitlist_email_outbox.update_one(
        {'_id': key},
        {'$setOnInsert': {'payload': payload, 'status': 'pending', 'attempts': 0,
                          'next_attempt_at': datetime.now(timezone.utc)}}, upsert=True,
    )


async def queue_confirmation(db, subscriber):
    greeting = f"Salut, {escape(subscriber['name'])}!" if subscriber.get('name') else 'Salut!'
    payload = {
        'to': [subscriber['email']],
        'subject': 'Ești pe lista Valandala. Ne auzim la lansare!',
        'html': _frame('Îți păstrăm un loc.', f'<p>{greeting}</p><p>Înscrierea ta este salvată. '
                       'Când Valandala se lansează, primești un email de la noi.</p>'
                       '<p>Până atunci, poate găsești în dulap o geacă pe care nu o mai porți '
                       'sau o pereche care merită alte drumuri.</p>'
                       '<p>Nu ți-am creat un cont în aplicație. Te vom anunța când poți începe.</p>'
                       '<p>Pe curând,<br>Echipa Valandala</p>'),
        'text': f"Salut{', ' + subscriber['name'] if subscriber.get('name') else ''}!\n\n"
                'Înscrierea ta pe lista Valandala este salvată. Te anunțăm când se lansează aplicația. '
                'Nu ți-am creat un cont.\n\nPentru întrebări sau retragerea acordului: info@valandala.ro',
    }
    await queue_email(db, f"confirmation/{subscriber['id']}", payload)


def _csv_cell(value):
    value = str(value or '')
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else value


async def _queue_daily_report(db, now):
    schedule = await db.website_settings.find_one({'_id': 'waitlist_daily_digest'})
    if not schedule or schedule['next_run'].replace(tzinfo=timezone.utc) > now:
        return
    date = now.astimezone(ROMANIA).strftime('%d.%m.%Y')
    key = 'daily-report/' + now.astimezone(ROMANIA).date().isoformat()
    if not await db.waitlist_email_outbox.find_one({'_id': key}, {'_id': 1}):
        output = io.StringIO(newline='')
        writer = csv.writer(output)
        writer.writerow(['Prenume', 'Email', 'Data înscrierii (România)'])
        total = new_today = 0
        period_start = now.astimezone(ROMANIA) - timedelta(days=1)
        async for person in db.launch_waitlist.find({'status': 'subscribed', 'created_at': {'$lte': now}}).sort('created_at', 1):
            created = person['created_at'].replace(tzinfo=timezone.utc).astimezone(ROMANIA)
            writer.writerow([_csv_cell(person.get('name')), _csv_cell(person['email']), created.strftime('%d.%m.%Y %H:%M')])
            total += 1
            new_today += created >= period_start
        content = output.getvalue().encode('utf-8-sig')
        if len(content) > 8 * 1024 * 1024:
            raise RuntimeError('Waitlist CSV exceeds the email attachment size limit; export from MongoDB instead.')
        payload = {
            'to': [os.getenv('WAITLIST_REPORT_EMAIL', 'info@valandala.ro').strip()],
            'subject': f'Valandala · Lista de lansare · {date}',
            'html': _frame('Lista de lansare, la zi.', f'<p>Raportul din {date}, ora '
                           f'{now.astimezone(ROMANIA):%H:%M}.</p><p><strong>{total}</strong> persoane înscrise în total. '
                           f'<strong>{new_today}</strong> înscrieri în ultimele 24 de ore.</p>'
                           '<p>Lista completă este atașată în format CSV, cu prenumele, emailul și data înscrierii. '
                           'Datele sunt confidențiale și sunt destinate gestionării campaniei de lansare.</p>'),
            'text': f'Lista Valandala din {date}: {total} persoane în total, {new_today} înscrise în ultimele 24 de ore. Lista completă este atașată.',
            'attachments': [{'filename': f'valandala-inscrieri-{date}.csv', 'content': base64.b64encode(content).decode('ascii')}],
        }
        await queue_email(db, key, payload)
    await db.website_settings.update_one({'_id': 'waitlist_daily_digest', 'next_run': schedule['next_run']},
                                        {'$set': {'next_run': _next_morning(now)}})


def _send(payload, key):
    sender = os.getenv('EMAIL_FROM_ADDRESS', 'notificari@valandala.ro').strip()
    name = os.getenv('EMAIL_FROM_NAME', 'Valandala').strip()
    response = requests.post(
        RESEND_API_URL,
        headers={'Authorization': 'Bearer ' + os.environ['RESEND_API_KEY'].strip(),
                 'Idempotency-Key': key, 'User-Agent': 'valandala-website/1.0'},
        json={**payload, 'from': f'{name} <{sender}>', 'reply_to': 'info@valandala.ro'}, timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f'Resend HTTP {response.status_code}')
    return response.json()['id']


async def email_worker(db):
    if not os.getenv('RESEND_API_KEY', '').strip():
        logger.warning('Resend is not configured; signup receipts remain queued until it is enabled.')
        return
    await db.waitlist_email_outbox.create_index([('status', 1), ('next_attempt_at', 1)])
    await db.website_settings.update_one(
        {'_id': 'waitlist_daily_digest'},
        {'$setOnInsert': {'next_run': _next_morning(datetime.now(timezone.utc))}}, upsert=True,
    )
    while True:
        job = None
        try:
            now = datetime.now(timezone.utc)
            await _queue_daily_report(db, now)
            job = await db.waitlist_email_outbox.find_one_and_update(
                {'$or': [{'status': 'pending', 'next_attempt_at': {'$lte': now}},
                         {'status': 'sending', 'lease_until': {'$lte': now}}]},
                {'$set': {'status': 'sending', 'lease_until': now + timedelta(minutes=2)}, '$inc': {'attempts': 1}},
                return_document=ReturnDocument.AFTER,
            )
            if job:
                try:
                    message_id = await asyncio.to_thread(_send, job['payload'], job['_id'])
                    await db.waitlist_email_outbox.update_one({'_id': job['_id']}, {'$set': {
                        'status': 'sent', 'resend_id': message_id, 'sent_at': datetime.now(timezone.utc)},
                        '$unset': {'payload': '', 'last_error': '', 'lease_until': ''}})
                except Exception as exc:
                    await db.waitlist_email_outbox.update_one({'_id': job['_id']}, {'$set': {
                        'status': 'failed' if job['attempts'] >= 5 else 'pending',
                        'next_attempt_at': now + timedelta(minutes=min(30, 2 ** job['attempts'])),
                        'last_error': type(exc).__name__ + (': ' + str(exc) if isinstance(exc, RuntimeError) else ''),
                    }})
                    logger.warning('Waitlist email delivery failed: %s', type(exc).__name__)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception('Waitlist email worker error')
        await asyncio.sleep(1 if job else 30)
