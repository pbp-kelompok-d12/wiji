from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateDocumentStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(
            location=settings.PRIVATE_MEDIA_ROOT,
        )

    def url(self, name):
        raise ValueError(
            "Dokumen privat hanya dapat diakses melalui halaman unduhan."
        )


private_document_storage = PrivateDocumentStorage()