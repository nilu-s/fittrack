"""Google v2 proof, real isolated persistence, and account/session boundaries."""
import asyncio
import os
import unittest
import uuid
from datetime import timedelta
from unittest.mock import patch

import httpx
from fastapi import HTTPException
from google.auth.exceptions import TransportError
from sqlalchemy import delete, select, func

from app.config import settings
from app.database import async_session, engine
from app.main import app
from app.models import Account, AccountWeightRange, GoogleToken, NativeLogin, NativeSession, Todo, TravelWatch, TravelNotification
from app.services.google_native_auth import verify_identity, start_login, exchange_google_login
from app.services.native_auth import proof_challenge, utcnow


def claims(**changes):
    return dict(iss='https://accounts.google.com', aud='test-client', exp=utcnow().timestamp() + 600,
                sub='test-subject', email='allowed@example.test', email_verified=True, **changes)


class GoogleIdentityValidation(unittest.TestCase):
    def test_real_signature_verification_with_local_test_keys(self):
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from jose import jwt
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        payload = claims() | {'iat': int(utcnow().timestamp())}
        with patch.object(settings, 'ALLOWED_GOOGLE_EMAILS', 'allowed@example.test'), \
             patch('google.oauth2.id_token._fetch_certs', return_value={'test-key': public}):
            for signing_key, changes, allowed in ((key, {}, True), (other, {}, False),
                    (key, {'aud': 'wrong-client'}, False), (key, {'exp': 0}, False)):
                pem = signing_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
                token = jwt.encode(payload | changes, pem, algorithm='RS256', headers={'kid': 'test-key'})
                if allowed:
                    self.assertEqual(verify_identity(token, 'test-client')['sub'], 'test-subject')
                else:
                    with self.assertRaises(HTTPException) as error: verify_identity(token, 'test-client')
                    self.assertEqual(error.exception.status_code, 401)

    def test_google_verification_is_called_with_expected_audience_and_rejects_bad_signature(self):
        with patch('app.services.google_native_auth.id_token.verify_oauth2_token', side_effect=ValueError('synthetic')) as verify:
            with self.assertRaises(HTTPException) as error:
                verify_identity('synthetic-token', 'test-client')
            self.assertEqual(error.exception.status_code, 401)
            self.assertEqual(verify.call_args.args[2], 'test-client')

    def test_claims_allowlist_and_provider_failures(self):
        with patch.object(settings, 'ALLOWED_GOOGLE_EMAILS', 'allowed@example.test'):
            for changes, expected in (({}, 200), ({'aud': 'foreign'}, 401), ({'iss': 'foreign'}, 401),
                    ({'exp': 0}, 401), ({'email_verified': False}, 401), ({'email_verified': 'true'}, 401),
                    ({'sub': ''}, 401), ({'email': 'foreign@example.test'}, 403)):
                with self.subTest(changes=changes), patch('app.services.google_native_auth.id_token.verify_oauth2_token', return_value=claims() | changes):
                    if expected == 200:
                        self.assertEqual(verify_identity('synthetic-token', 'test-client')['sub'], 'test-subject')
                    else:
                        with self.assertRaises(HTTPException) as error: verify_identity('synthetic-token', 'test-client')
                        self.assertEqual(error.exception.status_code, expected)
            with patch('app.services.google_native_auth.id_token.verify_oauth2_token', side_effect=TransportError('synthetic')):
                with self.assertRaises(HTTPException) as error: verify_identity('synthetic-token', 'test-client')
                self.assertEqual(error.exception.status_code, 503)


class GoogleLoginRoutes(unittest.IsolatedAsyncioTestCase):
    async def test_missing_configuration_and_validation_do_not_expose_secrets(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='https://testserver') as client:
            with patch.object(settings, 'GOOGLE_NATIVE_CLIENT_ID', ''):
                for path, body in (('/start', {'challenge': proof_challenge('a' * 64)}),
                        ('/exchange', {'login_id': str(uuid.uuid4()), 'verifier': 'a' * 64, 'id_token': 'synthetic'})):
                    response = await client.post('/api/native/google' + path, json=body)
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(response.headers['cache-control'], 'no-store')
            response = await client.post('/api/native/google/exchange', json={'id_token': 'synthetic-secret', 'user_id': 'foreign'})
            self.assertEqual(response.status_code, 422)
            self.assertNotIn('synthetic-secret', response.text)
            self.assertNotIn('foreign', response.text)


@unittest.skipUnless(os.environ.get('APP_INTEGRATION_DATABASE') == '1', 'requires disposable PostgreSQL')
class GoogleNativeIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.subject = f'google-test-{uuid.uuid4()}'
        self.email = f'{uuid.uuid4()}@example.test'
        self.logins = []
        self.account_ids = []
        self.gate = patch.multiple(settings, GOOGLE_NATIVE_CLIENT_ID='test-client', ALLOWED_GOOGLE_EMAILS=self.email)
        self.gate.start()
        self.addCleanup(self.gate.stop)

    async def asyncTearDown(self):
        async with async_session() as session:
            ids = list((await session.scalars(select(Account.id).where(Account.google_subject == self.subject))).all()) + self.account_ids
            for model in (TravelNotification, TravelWatch, Todo, NativeSession, GoogleToken, AccountWeightRange):
                await session.execute(delete(model).where(model.account_id.in_(ids)))
            await session.execute(delete(NativeLogin).where(NativeLogin.id.in_(self.logins)))
            await session.execute(delete(Account).where(Account.id.in_(ids)))
            await session.commit()
        await engine.dispose()

    async def begin(self):
        result = await start_login(proof_challenge('a' * 64))
        self.logins.append(result['login_id'])
        return result

    def identity(self, login):
        return claims() | {'sub': self.subject, 'email': self.email, 'nonce': login['nonce']}

    async def exchange(self, login):
        with patch('app.services.google_native_auth.id_token.verify_oauth2_token', return_value=self.identity(login)):
            return await exchange_google_login(login['login_id'], 'a' * 64, 'synthetic')

    async def test_success_reuses_subject_and_never_overwrites_google_integration(self):
        account = Account(id=uuid.uuid4(), google_subject=self.subject, email=self.email, alias='a_' + uuid.uuid4().hex[:10])
        async with async_session() as session:
            session.add(account)
            await session.flush()
            session.add(GoogleToken(account_id=account.id, email=self.email, access_token='existing-access', refresh_token='existing-refresh'))
            await session.commit()
        login = await self.begin()
        result = await self.exchange(login)
        self.assertTrue(result['credential'].startswith('crn2_'))
        async with async_session() as session:
            saved = await session.get(NativeSession, result['device_id'])
            self.assertEqual(saved.account_id, account.id)
            self.assertEqual(saved.protocol_version, 2)
            self.assertNotEqual(saved.credential_hash, result['credential'])
            token = await session.scalar(select(GoogleToken).where(GoogleToken.account_id == account.id))
            self.assertEqual(token.refresh_token, 'existing-refresh')
            row = await session.get(NativeLogin, login['login_id'])
            self.assertNotEqual(row.nonce_hash, login['nonce'])
            self.assertTrue(row.consumed)

    async def test_nonce_verifier_expiry_v1_and_replay(self):
        login = await self.begin()
        for verifier, changes in (('b' * 64, {}), ('a' * 64, {'nonce': 'wrong'}), ('a' * 64, {'nonce': None})):
            with patch('app.services.google_native_auth.id_token.verify_oauth2_token', return_value=self.identity(login) | changes):
                with self.assertRaises(HTTPException): await exchange_google_login(login['login_id'], verifier, 'synthetic')
        await self.exchange(login)
        with self.assertRaises(HTTPException): await self.exchange(login)
        for changes in ({'expires_at': utcnow() - timedelta(seconds=1)}, {'protocol_version': 1}, {'platform': 'ios'}):
            other = await self.begin()
            async with async_session() as session:
                row = await session.get(NativeLogin, other['login_id'])
                for name, value in changes.items(): setattr(row, name, value)
                await session.commit()
            with self.assertRaises(HTTPException): await self.exchange(other)

    async def test_parallel_exchange_creates_exactly_one_session(self):
        login = await self.begin()
        with patch('app.services.google_native_auth.id_token.verify_oauth2_token', return_value=self.identity(login)):
            results = await asyncio.gather(*[exchange_google_login(login['login_id'], 'a' * 64, 'synthetic') for _ in range(2)], return_exceptions=True)
        self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
        self.assertEqual(sum(isinstance(result, HTTPException) for result in results), 1)
        async with async_session() as session:
            account_id = await session.scalar(select(Account.id).where(Account.google_subject == self.subject))
            self.assertEqual(await session.scalar(select(func.count()).select_from(NativeSession).where(NativeSession.account_id == account_id)), 1)

    async def test_routes_exchange_and_reject_client_identity(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='https://testserver') as client:
            started = await client.post('/api/native/google/start', json={'challenge': proof_challenge('a' * 64)})
            self.assertEqual(started.status_code, 200)
            login = started.json()
            login['login_id'] = uuid.UUID(login['login_id'])
            self.logins.append(login['login_id'])
            body = {'login_id': str(login['login_id']), 'verifier': 'a' * 64, 'id_token': 'synthetic'}
            for field in ('account_id', 'user_id', 'platform'):
                response = await client.post('/api/native/google/exchange', json=body | {field: 'foreign'})
                self.assertEqual(response.status_code, 422)
            with patch('app.services.google_native_auth.id_token.verify_oauth2_token', return_value=self.identity(login)):
                response = await client.post('/api/native/google/exchange', json=body)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['cache-control'], 'no-store')
            self.assertNotIn('set-cookie', response.headers)
            self.assertNotIn('synthetic', response.text)

    async def test_concurrent_first_logins_share_one_account(self):
        first, second = await self.begin(), await self.begin()
        def verify(token, *args):
            return self.identity(first if token == 'first' else second)
        with patch('app.services.google_native_auth.id_token.verify_oauth2_token', side_effect=verify):
            results = await asyncio.gather(exchange_google_login(first['login_id'], 'a' * 64, 'first'),
                                           exchange_google_login(second['login_id'], 'a' * 64, 'second'))
        async with async_session() as session:
            devices = (await session.scalars(select(NativeSession).where(NativeSession.id.in_([r['device_id'] for r in results])))).all()
            self.assertEqual(len({device.account_id for device in devices}), 1)

    async def test_new_account_private_defaults_and_revocation(self):
        login = await self.begin()
        result = await self.exchange(login)
        headers = {'Authorization': 'Bearer ' + result['credential']}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='https://testserver', headers=headers) as client:
            me = (await client.get('/api/auth/me')).json()
            self.assertTrue(me['authenticated'])
            self.assertTrue(me['alias_required'])
            self.assertEqual((await client.post('/api/native/logout')).status_code, 204)
            self.assertFalse((await client.get('/api/auth/me')).json()['authenticated'])
        async with async_session() as session:
            self.assertEqual(await session.scalar(select(func.count()).select_from(AccountWeightRange).where(AccountWeightRange.account_id == uuid.UUID(me['id']))), 1)
            self.assertEqual(await session.scalar(select(func.count()).select_from(GoogleToken).where(GoogleToken.account_id == uuid.UUID(me['id']))), 0)
