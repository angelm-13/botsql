from __future__ import annotations

import os


os.environ.setdefault('TESTING', '1')
os.environ.setdefault('JWT_SECRET', 'test-secret')
os.environ.setdefault('JWT_SS', 'test-secret')
os.environ.setdefault('MFA_ISSUER', 'TYAKXA Test')
