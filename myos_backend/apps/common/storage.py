from django.core.files.storage import FileSystemStorage

try:
    from storages.backends.s3 import S3Storage
except ImportError:  # pragma: no cover - optional dependency
    S3Storage = None


class PublicMediaStorage(FileSystemStorage):
    location = "media/public"


if S3Storage is not None:
    class PrivateMediaStorage(S3Storage):
        default_acl = "private"
        file_overwrite = False
else:
    class PrivateMediaStorage(FileSystemStorage):  # pragma: no cover - local fallback
        location = "media/private"

