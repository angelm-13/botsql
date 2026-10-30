from __future__ import annotations
import os
import secrets
import string
from datetime import datetime, timezone
import bcrypt
from app.models import PublicApiKey
from app.models.session import transaction_context
from app.utils.tiempo import a_iso_utc


class PublicApiKeyManager:
    PREFIX_LENGTH = 8
    KEY_LENGTH = 40

    @classmethod
    def default_rate_limit(cls) -> int:
        try:
            return max(int(os.getenv('PUBLIC_API_RATE_LIMIT_DEFAULT', '60')), 1)
        except (TypeError, ValueError):
            return 60

    @classmethod
    def _now(cls):
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @classmethod
    def generate_plain_key(cls) -> str:
        alphabet = string.ascii_letters + string.digits
        secret = ''.join(secrets.choice(alphabet) for _ in range(cls.KEY_LENGTH))
        return 'txpub_' + secret

    @classmethod
    def hash_key(cls, plain_key: str) -> str:
        return bcrypt.hashpw(plain_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @classmethod
    def verify_key(cls, plain_key: str, key_hash: str) -> bool:
        try:
            return bcrypt.checkpw(str(plain_key or '').encode('utf-8'), str(key_hash or '').encode('utf-8'))
        except Exception:
            return False

    @classmethod
    def create_key(cls, *, label: str, allowed_domains='[]', rate_limit_per_min=None, user_id=None) -> dict:
        plain_key = cls.generate_plain_key()
        now = cls._now()
        record = PublicApiKey(
            label=str(label or '').strip() or 'Public catalog key',
            key_hash=cls.hash_key(plain_key),
            key_prefix=plain_key[:cls.PREFIX_LENGTH],
            allowed_domains=allowed_domains or '[]',
            rate_limit_per_min=int(rate_limit_per_min or cls.default_rate_limit()),
            is_active=True,
            last_used_at=None,
            created_by=user_id or 1,
            creation_date=now,
            last_update_date=now,
        )
        with transaction_context() as session:
            session.add(record)
            session.flush()
            result = {
                'id_public_api_key': record.id_public_api_key,
                'label': record.label,
                'key_prefix': record.key_prefix,
                'allowed_domains': record.allowed_domains,
                'rate_limit_per_min': record.rate_limit_per_min,
                'is_active': bool(record.is_active),
                'plain_key': plain_key,
            }
        return result

    @classmethod
    def safe_serialize(cls, record: PublicApiKey) -> dict:
        return {
            'id_public_api_key': record.id_public_api_key,
            'label': record.label,
            'key_prefix': record.key_prefix,
            'allowed_domains': record.allowed_domains,
            'rate_limit_per_min': record.rate_limit_per_min,
            'is_active': bool(record.is_active),
            'last_used_at': record.last_used_at.isoformat() if record.last_used_at else None,
            'created_by': record.created_by,
            'creation_date': a_iso_utc(record.creation_date),
            'last_update_date': a_iso_utc(record.last_update_date),
        }
