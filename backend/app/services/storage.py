"""File uploads, always namespaced per church (``church_<id>/<folder>``).

Uses Cloudinary when ``CLOUDINARY_*`` is configured (required in production: hosted
containers have ephemeral disks), otherwise the local ``uploads/`` directory that
``main.py`` serves at ``/uploads``.
"""
from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile

from app.core.config import settings

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}


def _cloudinary_enabled() -> bool:
    return bool(settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET)


def save_image(church_id: UUID, folder: str, file: UploadFile) -> str:
    """Validate and store an image; returns its public URL (absolute for Cloudinary,
    ``/uploads/...`` for local storage)."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Upload a JPG, PNG, WEBP or GIF image")
    data = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Images must be 5 MB or smaller")
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")

    namespace = f"church_{church_id}/{folder}"
    if _cloudinary_enabled():
        import cloudinary
        import cloudinary.uploader

        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME, api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET, secure=True,
        )
        result = cloudinary.uploader.upload(data, folder=namespace, resource_type="image")
        return result["secure_url"]

    directory = Path("uploads") / namespace
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{_EXTENSIONS[file.content_type]}"
    (directory / filename).write_bytes(data)
    return f"/uploads/{namespace}/{filename}"


def delete_church_files(church_id: UUID) -> None:
    """Remove everything uploaded for a church (account purge). Best effort: a storage
    failure is logged and must never block deleting the database rows."""
    import logging
    import shutil

    log = logging.getLogger("app.storage")
    namespace = f"church_{church_id}"
    try:
        if _cloudinary_enabled():
            import cloudinary
            import cloudinary.api

            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME, api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET, secure=True,
            )
            cloudinary.api.delete_resources_by_prefix(f"{namespace}/")
            cloudinary.api.delete_folder(namespace)
        else:
            shutil.rmtree(Path("uploads") / namespace, ignore_errors=True)
    except Exception:
        log.exception("Could not delete stored files for church %s", church_id)
