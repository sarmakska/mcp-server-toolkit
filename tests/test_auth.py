"""Auth: API key comparison, rate limiter, OAuth verifier, PKCE client."""
import time

import pytest
from jose import jwt

from mcp_toolkit.auth import RateLimiter, verify_api_key
from mcp_toolkit.auth.oauth import OAuthError, OAuthVerifier
from mcp_toolkit.oauth_client import generate_pkce_pair


def test_api_key_constant_time_compare():
    assert verify_api_key("abc", "abc") is True
    assert verify_api_key("abc", "abd") is False
    assert verify_api_key(None, "abc") is False
    assert verify_api_key("abc", "") is False


def test_rate_limiter_allows_burst_then_blocks():
    limiter = RateLimiter(rate=1, burst=3)
    assert [limiter.allow("client-a") for _ in range(3)] == [True, True, True]
    assert limiter.allow("client-a") is False
    # A different client has its own bucket.
    assert limiter.allow("client-b") is True


def test_rate_limiter_refills_over_time():
    limiter = RateLimiter(rate=100, burst=1)
    assert limiter.allow("c") is True
    assert limiter.allow("c") is False
    time.sleep(0.05)  # 100 rps refills well within 50ms
    assert limiter.allow("c") is True


def test_pkce_pair_is_valid_s256():
    import base64
    import hashlib

    verifier, challenge = generate_pkce_pair()
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    assert challenge == expected
    assert "=" not in verifier and "=" not in challenge


@pytest.fixture
def rsa_signing(scope="module"):
    """Generate an RSA keypair and expose its JWK, mirroring a real JWKS."""
    from jose import jwk
    from jose.constants import ALGORITHMS

    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ImportError:  # pragma: no cover
        pytest.skip("cryptography not available")

    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    public_jwk = jwk.construct(public_pem, ALGORITHMS.RS256).to_dict()
    public_jwk["kid"] = "k1"
    # jose returns bytes for n/e; JSON expects strings.
    for field_name in ("n", "e"):
        if isinstance(public_jwk.get(field_name), bytes):
            public_jwk[field_name] = public_jwk[field_name].decode()
    return pem, public_jwk


async def test_oauth_verifier_accepts_valid_token(monkeypatch, rsa_signing):
    pem, public_jwk = rsa_signing
    token = jwt.encode(
        {
            "iss": "https://issuer.example",
            "aud": "mcp-toolkit",
            "exp": int(time.time()) + 300,
            "sub": "user-1",
        },
        pem,
        algorithm="RS256",
        headers={"kid": "k1"},
    )
    verifier = OAuthVerifier(issuer="https://issuer.example", audience="mcp-toolkit")

    async def fake_jwks():
        return {"keys": [public_jwk]}

    monkeypatch.setattr(verifier, "_get_jwks", fake_jwks)
    claims = await verifier.verify(token)
    assert claims["sub"] == "user-1"


async def test_oauth_verifier_rejects_wrong_audience(monkeypatch, rsa_signing):
    pem, public_jwk = rsa_signing
    token = jwt.encode(
        {
            "iss": "https://issuer.example",
            "aud": "someone-else",
            "exp": int(time.time()) + 300,
        },
        pem,
        algorithm="RS256",
        headers={"kid": "k1"},
    )
    verifier = OAuthVerifier(issuer="https://issuer.example", audience="mcp-toolkit")

    async def fake_jwks():
        return {"keys": [public_jwk]}

    monkeypatch.setattr(verifier, "_get_jwks", fake_jwks)
    with pytest.raises(OAuthError):
        await verifier.verify(token)


async def test_oauth_verifier_rejects_malformed_token():
    verifier = OAuthVerifier(issuer="https://issuer.example", audience="mcp-toolkit")
    with pytest.raises(OAuthError):
        await verifier.verify("not-a-jwt")
