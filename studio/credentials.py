"""Credentials (GÖREV-16, Adım 3a): Windows Credential Manager through `keyring`, service name `30AStudio`. Housing Atlas's
`atlas/secrets.py`, narrowed to this program's one secret.

The values are never written to a file, a log, a command line or an API answer; the API says only whether one is saved. Every value
saved or read in this process goes on the log's mask list (`studio.logs.register_secret`), so a message that happens to carry it is
written with `***` instead.
"""
import logging

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

from . import logs

log = logging.getLogger(__name__)

SERVICE = "30AStudio"
MAX_LENGTH = 500
LABELS = {"abd_proxy_parolasi": "ABD proxy parolası"}
STORE_FAILURES = {"save": "Windows Kimlik Bilgisi Yöneticisi'ne kaydedilemedi", "read": "Windows Kimlik Bilgisi Yöneticisi'nden okunamadı",
                  "delete": "Windows Kimlik Bilgisi Yöneticisi'nden silinemedi"}


class SecretError(Exception):
    """A Turkish message for the user (it never carries the value)."""


def check_name(name):
    if name not in LABELS:
        raise SecretError(f"Bilinmeyen gizli bilgi: {name}.")
    return name


def clean_value(name, value):
    if not isinstance(value, str) or not value.strip():
        raise SecretError(f"{LABELS[name]} boş olamaz.")
    value = value.strip()
    if len(value) > MAX_LENGTH:
        raise SecretError(f"{LABELS[name]} en çok {MAX_LENGTH} karakter olabilir.")
    return value


def store_error(name, action, exc):
    """The user gets a Turkish message; keyring's (English) detail goes to the application log only."""
    message = f"{LABELS[name]} {STORE_FAILURES[action]}."
    log.warning("%s Ayrıntı: %s", message, exc)
    return SecretError(f"{message} Ayrıntısı uygulama günlüğünde.")


def set_secret(name, value):
    check_name(name)
    clean = clean_value(name, value)
    logs.register_secret(clean)
    try:
        keyring.set_password(SERVICE, name, clean)
    except KeyringError as exc:
        raise store_error(name, "save", exc) from exc
    log.info("%s Kimlik Bilgisi Yöneticisi'ne kaydedildi.", LABELS[name])


def get_secret(name):
    check_name(name)
    try:
        value = keyring.get_password(SERVICE, name)
    except KeyringError as exc:
        raise store_error(name, "read", exc) from exc
    logs.register_secret(value)
    return value


def has_secret(name):
    return bool(get_secret(name))


def delete_secret(name):
    check_name(name)
    try:
        keyring.delete_password(SERVICE, name)
    except PasswordDeleteError:
        return
    except KeyringError as exc:
        raise store_error(name, "delete", exc) from exc
    log.info("%s Kimlik Bilgisi Yöneticisi'nden silindi.", LABELS[name])
