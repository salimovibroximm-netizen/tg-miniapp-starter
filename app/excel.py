"""Excel export with live formulas and embedded photo thumbnails."""
import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .config import settings
from .db import Report

PHOTO_COL = 6
THUMB_W, THUMB_H = 110, 82  # pixels; the row height below is set to fit


def build_workbook(reports: list[Report], title: str = "Reports") -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Reports"
    ws.append([title])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append(["#", "Date", "Author", "Title", "Photos", "First photo", "Note"])
    head = PatternFill("solid", fgColor="DDEBF7")
    for c in ws[2]:
        c.font = Font(bold=True)
        c.fill = head
    widths = [5, 17, 24, 32, 9, 17, 40]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    first = 3
    for n, r in enumerate(reports, start=1):
        row = first + n - 1
        ws.append([n, r.created_at, r.user.full_name, r.title, len(r.photos), "", r.note or ""])
        ws.cell(row, 2).number_format = "dd.mm.yyyy hh:mm"
        ws.cell(row, 7).alignment = Alignment(wrap_text=True, vertical="top")
        if r.photos:
            _add_thumb(ws, r.photos[0].thumb, row)
    last = first + len(reports) - 1

    # A real formula, so the total stays right if someone deletes or edits rows.
    total = last + 2
    ws.cell(total, 4, "Total photos").font = Font(bold=True)
    ws.cell(total, 5, f"=SUM(E{first}:E{max(last, first)})" if reports else 0).font = Font(bold=True)
    ws.freeze_panes = "A3"

    stamp = datetime.now(settings.tz).strftime("%d.%m.%Y %H:%M")
    ws.cell(total + 1, 4, f"Exported {stamp}").font = Font(italic=True, color="888888")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _add_thumb(ws, rel_path: str, row: int) -> None:
    file = settings.data_dir / "media" / rel_path
    if not file.is_file():
        return
    img = XLImage(str(file))
    ratio = min(THUMB_W / img.width, THUMB_H / img.height, 1)
    img.width, img.height = int(img.width * ratio), int(img.height * ratio)
    ws.add_image(img, f"{get_column_letter(PHOTO_COL)}{row}")
    ws.row_dimensions[row].height = THUMB_H * 0.78  # points, roughly px * 0.75
