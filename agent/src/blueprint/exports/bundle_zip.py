"""bundle.zip (SPECS S10.8, S10.9): every available kind except itself, under its S10.2 file
name, in the fixed kind order, every entry dated tickets_approved_at."""

import io
import zipfile

from blueprint.exports.docx_util import parse_time
from blueprint.state import SessionState

Entry = tuple[str, bytes]


def render_bundle(state: SessionState, entries: list[Entry]) -> bytes:
    if state.tickets_approved_at is None:
        raise LookupError("available once the ticket breakdown is approved")
    at = parse_time(state.tickets_approved_at)
    stamp = (at.year, at.month, at.day, at.hour, at.minute, at.second)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            info = zipfile.ZipInfo(name, date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            info.create_system = 0
            archive.writestr(info, data)
    return out.getvalue()
