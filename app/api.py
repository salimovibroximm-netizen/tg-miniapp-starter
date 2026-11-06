from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .auth import current_user, is_admin, require_admin
from .config import settings
from .db import Photo, Report, User, get_db, now
from .excel import build_workbook
from .media import BadImage, media_url, save_image

router = APIRouter(prefix="/api")


def report_json(r: Report) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "note": r.note,
        "author": r.user.full_name,
        "created_at": r.created_at.isoformat(timespec="minutes"),
        "photos": [{"url": media_url(p.path), "thumb": media_url(p.thumb)} for p in r.photos],
    }


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {
        "id": user.id,
        "full_name": user.full_name,
        "is_admin": is_admin(user),
        "lang": user.lang or "en",
        "max_photos": settings.max_photos,
    }


@router.get("/reports")
def list_reports(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Users see their own reports; admins see everyone's."""
    q = select(Report).options(selectinload(Report.photos), selectinload(Report.user)).order_by(Report.id.desc())
    if not is_admin(user):
        q = q.where(Report.user_id == user.id)
    return {"items": [report_json(r) for r in db.scalars(q.limit(200))]}


@router.post("/reports")
async def create_report(
    # Form("") and not Form(...): FastAPI treats an empty required field as missing and
    # answers with a technical 422. Checking it ourselves gives the user a clear message.
    title: str = Form(""),
    note: str = Form(""),
    photos: list[UploadFile] = File(default=[]),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    title = title.strip()[:200]
    if len(title) < 2:
        raise HTTPException(400, "Write a title")
    if len(photos) > settings.max_photos:
        raise HTTPException(400, f"No more than {settings.max_photos} photos")
    stamp = f"{now():%d.%m.%Y %H:%M}"
    report = Report(user_id=user.id, title=title, note=note.strip()[:2000] or None)
    for f in photos:
        data = await f.read()
        if not data:
            continue
        try:
            path, thumb = save_image(data, "reports", stamp)
        except BadImage as exc:
            raise HTTPException(400, str(exc))
        report.photos.append(Photo(path=path, thumb=thumb))
    db.add(report)
    db.commit()
    db.refresh(report)
    return report_json(report)


@router.get("/export.xlsx")
def export(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    reports = list(db.scalars(
        select(Report).options(selectinload(Report.photos), selectinload(Report.user)).order_by(Report.id)
    ))
    data = build_workbook(reports)
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="reports-{now():%Y-%m-%d}.xlsx"'},
    )
