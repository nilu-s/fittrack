"""Rehearse v1 revocation on an explicitly disposable, initially empty database."""
import os
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

if os.environ.get('APP_MIGRATION_REHEARSAL') != '1' or os.environ.get('APP_IGNORE_DOTENV') != '1':
    raise SystemExit('Requires APP_MIGRATION_REHEARSAL=1 and APP_IGNORE_DOTENV=1 on a disposable empty DB')
url = os.environ.get('DATABASE_URL')
if not url:
    raise SystemExit('DATABASE_URL required')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, inspect, insert, text
from app.models import Account, Todo, TravelWatch, TravelNotification

engine = create_engine(url.replace('postgresql+asyncpg:', 'postgresql+psycopg2:'))
if inspect(engine).get_table_names():
    raise SystemExit('Refusing nonempty database')
root = Path(__file__).resolve().parents[1]
def migrate(*args):
    subprocess.run([sys.executable, '-m', 'alembic', *args], cwd=root, check=True)

migrate('upgrade', 'a60908c001')
account, device, login, todo, watch, event = [uuid.uuid4() for _ in range(6)]
now = datetime.now(timezone.utc)
with engine.begin() as c:
    c.execute(insert(Account).values(id=account, google_subject='migration-synthetic', email='migration@example.test'))
    c.execute(text('INSERT INTO native_sessions (id, account_id, credential_hash, platform, push_token, expires_at) VALUES (:id,:account,:hash,:platform,:push,:expires)'),
              dict(id=device, account=account, hash='synthetic-hash', platform='android', push='synthetic-push', expires=now + timedelta(days=1)))
    c.execute(text('INSERT INTO native_logins (id, account_id, challenge, platform, expires_at) VALUES (:id,:account,:challenge,:platform,:expires)'),
              dict(id=login, account=account, challenge='synthetic', platform='android', expires=now + timedelta(minutes=5)))
    c.execute(insert(Todo).values(id=todo, account_id=account, title='Synthetic migration trip'))
    c.execute(insert(TravelWatch).values(id=watch, account_id=account, todo_id=todo, device_id=device,
              plan_hash='synthetic', origin={'placeId': 'synthetic'}, live_fix={'latitude': 52},
              live_until=now+timedelta(hours=1), expires_at=now+timedelta(hours=2), next_check_at=now))
    c.execute(insert(TravelNotification).values(id=event, account_id=account, watch_id=watch, generation=1,
              event_key='synthetic', kind='lead', expires_at=now+timedelta(minutes=5), next_attempt_at=now))
migrate('upgrade', 'head')
with engine.connect() as c:
    assert c.execute(text('SELECT revoked AND push_token IS NULL AND protocol_version = 1 FROM native_sessions')).scalar_one()
    assert c.execute(text('SELECT consumed FROM native_logins')).scalar_one()
    assert c.execute(text('SELECT NOT active AND origin IS NULL AND live_fix IS NULL AND live_until IS NULL FROM travel_watches')).scalar_one()
    assert c.execute(text('SELECT discarded FROM travel_notifications')).scalar_one()
    assert c.execute(text('SELECT title FROM todos')).scalar_one() == 'Synthetic migration trip'
migrate('downgrade', 'a60908c001')
with engine.connect() as c:
    assert c.execute(text('SELECT revoked AND push_token IS NULL FROM native_sessions')).scalar_one()
migrate('upgrade', 'head')
migrate('heads')
engine.dispose()
print('Native migration: v1 login/session/push invalidated, locations cleared, todo retained, downgrade never reactivates credentials.')
