from io import BytesIO

from docx import Document
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.config import Settings
from app.main import create_app
from app.parsing import extract_sections


def test_document_workflow(tmp_path):
    app = create_app(Settings(data_dir=tmp_path))
    client = TestClient(app)
    assert client.get("/api/status").json()["document_count"] == 0
    assert client.post("/api/ask", json={"question": "请假提前几天？"}).json()["sources"] == []

    doc = Document()
    doc.add_paragraph("员工请假需要提前三个工作日申请，并由主管审批。")
    word = BytesIO()
    doc.save(word)
    uploaded = client.post("/api/documents", files={"file": ("员工手册.docx", word.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert uploaded.status_code == 201, uploaded.text
    doc_id = uploaded.json()["id"]
    result = client.post("/api/ask", json={"question": "员工请假需要提前几个工作日申请？"})
    assert result.status_code == 200
    assert result.json()["sources"][0]["document_id"] == doc_id
    assert "段落 1" in result.json()["sources"][0]["locator"]
    assert "三个工作日" in result.json()["answer"]
    follow_up = client.post("/api/ask", json={"question": "这条规定由谁审批？", "history": [
        {"role": "user", "content": "员工请假需要提前几个工作日申请？"},
        {"role": "assistant", "content": result.json()["answer"]},
    ]})
    assert follow_up.status_code == 200
    assert "主管审批" in follow_up.json()["answer"]

    pdf_bytes = BytesIO()
    pdf = canvas.Canvas(pdf_bytes)
    pdf.drawString(72, 720, "Expense approval requires manager review.")
    pdf.save()
    uploaded_pdf = client.post("/api/documents", files={"file": ("policy.pdf", pdf_bytes.getvalue(), "application/pdf")})
    assert uploaded_pdf.status_code == 201, uploaded_pdf.text
    assert len(client.get("/api/documents").json()) == 2
    assert client.delete(f"/api/documents/{doc_id}").json() == {"deleted": True}
    assert len(client.get("/api/documents").json()) == 1
    assert client.delete(f"/api/documents/{doc_id}").status_code == 404
    app.state.store.qdrant.close()


def test_invalid_uploads(tmp_path):
    app = create_app(Settings(data_dir=tmp_path, max_upload_mb=1))
    client = TestClient(app)
    assert client.post("/api/documents", files={"file": ("x.exe", b"bad")}).status_code == 415
    assert client.post("/api/documents", files={"file": ("x.txt", b"x" * (1024 * 1024 + 1))}).status_code == 413
    assert client.post("/api/documents", files={"file": ("blank.txt", b"  ")}).status_code == 422
    assert client.post("/api/documents", files={"file": ("broken.pdf", b"not a pdf")}).status_code == 422
    app.state.store.qdrant.close()


def test_public_demo_is_readonly(tmp_path):
    app = create_app(Settings(data_dir=tmp_path, demo_readonly=True))
    client = TestClient(app)
    assert client.get("/api/status").json()["demo_readonly"] is True
    assert client.post("/api/documents", files={"file": ("x.txt", b"demo")}).status_code == 403
    assert client.delete("/api/documents/any-id").status_code == 403
    assert client.post("/api/ask", json={"question": "示例文档说了什么？"}).status_code == 200
    app.state.store.qdrant.close()


def test_text_paragraph_locations():
    assert extract_sections("policy.txt", "年假申请。\n\n报销审批。".encode()) == [
        ("段落 1", "年假申请。"), ("段落 2", "报销审批。")
    ]
