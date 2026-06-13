from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from cryptography.fernet import Fernet, InvalidToken


class EncryptedTextField(models.TextField):
    """Encrypt/decrypt text transparently using Fernet."""

    def _fernet(self):
        key = getattr(settings, "FERNET_KEY", None)
        if not key:
            raise ImproperlyConfigured("FERNET_KEY is required for encrypted fields")
        return Fernet(key.encode("utf-8"))

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        token = self._fernet().encrypt(str(value).encode("utf-8"))
        return token.decode("utf-8")

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        try:
            return self._fernet().decrypt(value.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError):
            return value

    def to_python(self, value):
        if value in (None, "") or not isinstance(value, str):
            return value
        try:
            return self._fernet().decrypt(value.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError):
            return value
