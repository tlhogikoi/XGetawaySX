from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateGalleryStorage(FileSystemStorage):
    """Private filesystem storage; files are never exposed through MEDIA_URL."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            location=Path(settings.PRIVATE_GALLERY_STORAGE_ROOT),
            base_url=None,
            file_permissions_mode=0o640,
            directory_permissions_mode=0o750,
        )

    @property
    def location(self):
        return str(Path(settings.PRIVATE_GALLERY_STORAGE_ROOT))

    def url(self, name):
        raise ValueError("Private Gallery files do not have public storage URLs.")
