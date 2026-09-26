import sys
import io
import pytest
from fastapi import UploadFile, HTTPException, status
from backend.services.file_service import _validate_file


def make_upload_file(filename, content_bytes):
    file_obj = io.BytesIO(content_bytes)
    return UploadFile(filename=filename, file=file_obj)

def test_validate_file_allowed_extension():
    upload = make_upload_file("test.pdf", b"%PDF-1.4 test content")
    # Should not raise
    _validate_file(upload)

def test_validate_file_disallowed_extension():
    upload = make_upload_file("test.exe", b"binary content")
    with pytest.raises(HTTPException) as exc:
        _validate_file(upload)
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "extension" in exc.value.detail

# MIME type validation is optional; if python-magic not installed, _validate_file should pass.
# We simulate environment where python-magic is absent.
def test_validate_file_without_magic(monkeypatch):
    monkeypatch.setitem(sys.modules, 'magic', None)
    upload = make_upload_file("test.png", b"\x89PNG\r\n\x1a\n" + b"data")
    # Should not raise even if mime check cannot be performed
    _validate_file(upload)
