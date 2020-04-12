#!/usr/bin/env python3
#
# Provides functions for managing Public Key Infrastructure (PKI) within a
# Kubernetes cluster

import cryptography.hazmat.backends as crypto_backends
import cryptography.hazmat.primitives.asymmetric.ec as ellipic_curve
import cryptography.hazmat.primitives.hashes
import cryptography.x509 as x509
import dataclasses
import datetime
import secrets
import typing

PrivateKey = typing.Union[ellipic_curve.EllipticCurvePrivateKeyWithSerialization]


@dataclasses.dataclass(frozen=True)
class Keypair:
    private_key: PrivateKey
    public_key: x509.Certificate


def standard_hash_algorithm() -> cryptography.hazmat.primitives.hashes.HashAlgorithm:
    return cryptography.hazmat.primitives.hashes.SHA256()


def _random_serial_number() -> int:
    # https://tools.ietf.org/html/rfc3280#section-4.1.2.2
    return secrets.randbits(20 * 8)


def generate_private_key() -> PrivateKey:
    private_key = ellipic_curve.generate_private_key(
        # The cryptography library only supports the NIST curves; there is a
        # general concern that the NSA may have influenced the selection of
        # weaker curves, so this is a candidate to revisit in the future.
        #
        # There are three NIST curves considered secure as of April 2020:
        # - P-256
        # P-384
        # P-521
        # P-256 is significantly faster than the other two and is used here.
        curve=ellipic_curve.SECP256R1(),
        backend=crypto_backends.default_backend(),
    )
    assert isinstance(
        private_key, ellipic_curve.EllipticCurvePrivateKeyWithSerialization
    )
    return private_key


def standard_key_usage() -> x509.KeyUsage:
    return x509.KeyUsage(
        content_commitment=False,
        crl_sign=False,
        data_encipherment=False,
        decipher_only=False,
        digital_signature=True,
        encipher_only=False,
        key_agreement=False,
        key_cert_sign=False,
        key_encipherment=True,
    )


def generate_subject_name(
    common_name: str, *, organization: str
) -> cryptography.x509.Name:
    return cryptography.x509.Name(
        (
            cryptography.x509.NameAttribute(
                cryptography.x509.oid.NameOID.COMMON_NAME, common_name
            ),
            cryptography.x509.NameAttribute(
                cryptography.x509.oid.NameOID.ORGANIZATION_NAME, organization
            ),
        )
    )


def generate_certificate_authority_certificate(
    name: x509.Name, *, signing_key: PrivateKey
) -> x509.Certificate:
    # https://cryptography.io/en/latest/x509/reference/#x-509-certificate-builder
    return (
        (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .add_extension(
                # https://tools.ietf.org/html/rfc3280#section-4.2.1.10
                x509.BasicConstraints(ca=True, path_length=2),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    content_commitment=False,
                    crl_sign=True,
                    data_encipherment=True,
                    decipher_only=False,
                    digital_signature=False,
                    encipher_only=False,
                    key_agreement=False,
                    key_cert_sign=True,
                    key_encipherment=False,
                ),
                critical=True,
            )
            .add_extension(
                # https://tools.ietf.org/html/rfc3280#section-4.2.1.2
                x509.SubjectKeyIdentifier.from_public_key(signing_key.public_key()),
                critical=False,
            )
            .serial_number(_random_serial_number())
            .not_valid_before(datetime.datetime.now())
            .not_valid_after(
                # Expire in 5 years
                datetime.datetime.now()
                + datetime.timedelta(days=365 * 5)
            )
        )
        .public_key(signing_key.public_key())
        .sign(
            private_key=signing_key,
            algorithm=standard_hash_algorithm(),
            backend=cryptography.hazmat.backends.default_backend(),
        )
    )


def generate_keypair(
    name: x509.Name,
    *,
    subject_alternative_name: x509.SubjectAlternativeName = None,
    key_usage: x509.KeyUsage,
    certificate_authority_keypair: Keypair
) -> Keypair:
    private_key = generate_private_key()

    csr_builder = x509.CertificateSigningRequestBuilder().subject_name(name)
    if subject_alternative_name:
        csr_builder.add_extension(subject_alternative_name, critical=False)
    csr = csr_builder.sign(
        private_key=private_key,
        algorithm=standard_hash_algorithm(),
        backend=cryptography.hazmat.backends.default_backend(),
    )

    certificate_builder = (
        x509.CertificateBuilder()
        .subject_name(csr.subject)
        .public_key(csr.public_key())
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(key_usage, critical=True)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(
                certificate_authority_keypair.private_key.public_key()
            ),
            critical=False,
        )
        .add_extension(
            # crypto/tls requires client auth extension
            # https://etcd.io/docs/v3.4.0/op-guide/security/#im-seeing-a-sslv3-alert-handshake-failure-when-using-tls-client-authentication
            x509.ExtendedKeyUsage(usages=[x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
        .issuer_name(certificate_authority_keypair.public_key.subject)
        .serial_number(_random_serial_number())
        .not_valid_before(datetime.datetime.now())
        .not_valid_after(datetime.datetime.now() + datetime.timedelta(365))
    )

    for extension in csr.extensions:
        certificate_builder = certificate_builder.add_extension(
            extension.value, critical=extension.critical
        )

    return Keypair(
        private_key=private_key,
        public_key=certificate_builder.sign(
            private_key=certificate_authority_keypair.private_key,
            algorithm=standard_hash_algorithm(),
            backend=crypto_backends.default_backend(),
        ),
    )
