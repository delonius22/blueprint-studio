"""T-19 / NFR-6: no configured key value appears in any download kind (S1.5).

Every kind with a renderer is rendered from a rich session state and searched, entry by
entry for zip-based files. Kinds join this scan as their renderers are added.
"""

import io
import zipfile

from conftest import INTERVIEW_KEY, REVIEW_KEY
from test_prd import signed_off_state

from blueprint.downloads import RENDERERS, render, unmet


def contents(data: bytes) -> list[bytes]:
    if data[:2] == b"PK":
        archive = zipfile.ZipFile(io.BytesIO(data))
        return [archive.read(name) for name in archive.namelist()]
    return [data]


def test_no_download_contains_a_key() -> None:
    state = signed_off_state()
    scanned = []
    for kind in RENDERERS:
        if unmet(state, kind) is not None:
            continue
        for part in contents(render(state, kind, "URL shortener")):
            assert INTERVIEW_KEY.encode() not in part and REVIEW_KEY.encode() not in part, kind
        scanned.append(kind)
    assert "prd-v1.0.docx" in scanned
