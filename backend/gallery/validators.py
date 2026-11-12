from django.core.exceptions import ValidationError


MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_EVIDENCE_BYTES = 15 * 1024 * 1024

_IMAGE_SIGNATURES = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),
)
_EVIDENCE_SIGNATURES = _IMAGE_SIGNATURES + (
    (b"%PDF-", "application/pdf"),
)


def _signature(upload, allowed, max_bytes, field_name):
    if upload.size <= 0 or upload.size > max_bytes:
        raise ValidationError({field_name: f"File must be between 1 byte and {max_bytes // (1024 * 1024)} MB."})
    position = upload.tell()
    upload.seek(0)
    header = upload.read(12)
    upload.seek(position)
    for signature, mime in allowed:
        if header.startswith(signature):
            if mime == "image/webp" and header[8:12] != b"WEBP":
                continue
            return mime
    raise ValidationError({field_name: "Unsupported or invalid file content. Use JPEG, PNG, WebP" + (", or PDF." if field_name == "evidence_file" else ".")})


def validate_gallery_image(upload):
    _signature(upload, _IMAGE_SIGNATURES, MAX_IMAGE_BYTES, "image_file")


def validate_gallery_evidence(upload):
    _signature(upload, _EVIDENCE_SIGNATURES, MAX_EVIDENCE_BYTES, "evidence_file")


def gallery_image_content_type(upload):
    position = upload.tell()
    upload.seek(0)
    header = upload.read(12)
    upload.seek(position)
    for signature, mime in _IMAGE_SIGNATURES:
        if header.startswith(signature):
            if mime == "image/webp" and header[8:12] != b"WEBP":
                continue
            return mime
    raise ValidationError("Stored Gallery image has an unsupported signature.")
