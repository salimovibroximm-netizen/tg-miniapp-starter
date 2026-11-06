import io
import time

from openpyxl import load_workbook
from PIL import Image

from tests.conftest import ADMIN_TG, TOKEN, as_user, init_data, jpeg


def test_init_data_is_verified():
    from app.auth import verify_init_data

    assert verify_init_data(init_data(42), TOKEN)["id"] == 42
    assert verify_init_data(init_data(42, token="999:OTHER"), TOKEN) is None  # signed by another bot
    assert verify_init_data(init_data(42).replace("Test", "Evil"), TOKEN) is None  # tampered
    assert verify_init_data(init_data(42, auth_date=int(time.time()) - 3 * 86400), TOKEN) is None  # stale
    assert verify_init_data("", TOKEN) is None


def test_requests_without_telegram_are_rejected(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers={"X-Dev-Tg-Id": "42"}).status_code == 401  # DEV_MODE is off
    assert client.get("/health").json() == {"ok": True}


def test_report_with_stamped_photo(client):
    me = client.get("/api/me", headers=as_user(2001, first_name="Ali")).json()
    assert me["full_name"] == "Ali" and me["is_admin"] is False

    for empty in ("", " "):
        r = client.post("/api/reports", headers=as_user(2001), data={"title": empty})
        assert r.status_code == 400 and r.json()["detail"] == "Write a title"
    r = client.post("/api/reports", headers=as_user(2001), data={"title": "Shelf check", "note": "ok"},
                    files=[("photos", ("a.jpg", jpeg(), "image/jpeg"))])
    assert r.status_code == 200, r.text
    photo = r.json()["photos"][0]

    # The photo is served only with a valid signature
    full = client.get(photo["url"])
    assert full.status_code == 200 and full.headers["content-type"] == "image/jpeg"
    assert client.get(photo["url"].split("?")[0] + "?s=forged").status_code == 404

    # The date stamp darkened the bottom-right corner of a plain orange photo
    img = Image.open(io.BytesIO(full.content)).convert("RGB")
    assert sum(img.getpixel((img.width - 40, img.height - 20))) < 200
    assert sum(img.getpixel((20, 20))) > 300

    # Not a photo
    r = client.post("/api/reports", headers=as_user(2001), data={"title": "Bad"},
                    files=[("photos", ("x.jpg", b"not an image", "image/jpeg"))])
    assert r.status_code == 400


def test_users_see_only_their_own_reports(client):
    client.post("/api/reports", headers=as_user(2002, first_name="Vali"), data={"title": "Vali's report"})
    titles = [r["title"] for r in client.get("/api/reports", headers=as_user(2002)).json()["items"]]
    assert titles == ["Vali's report"]
    everyone = client.get("/api/reports", headers=as_user(ADMIN_TG)).json()["items"]
    assert {"Vali's report", "Shelf check"} <= {r["title"] for r in everyone}


def test_excel_export_for_admin_only(client):
    assert client.get("/api/export.xlsx", headers=as_user(2001)).status_code == 403
    r = client.get("/api/export.xlsx", headers=as_user(ADMIN_TG))
    assert r.status_code == 200
    ws = load_workbook(io.BytesIO(r.content))["Reports"]
    assert [c.value for c in ws[2]][:4] == ["#", "Date", "Author", "Title"]
    totals = [ws.cell(row, 5).value for row in range(3, ws.max_row + 1)]
    assert any(isinstance(v, str) and v.startswith("=SUM(E3:") for v in totals)
    assert len(ws._images) >= 1  # the stamped photo is embedded as a thumbnail
