from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import json
import zipfile
import jarvis_knowledge as knowledge
from jarvis_operations import Operations
from jarvis_sources import answer, public_web

with TemporaryDirectory() as folder:
    root = Path(folder)
    data = root / "Data"
    (data / "Contracts").mkdir(parents=True)
    document = data / "Contracts" / "terms.txt"
    document.write_text("Northstar delivery is Friday.\nCobalt invoices need approval.", encoding="utf-8")
    def model(**kwargs):
        payload = json.loads(kwargs["messages"][1]["content"])
        assert payload["evidence"][0]["file"] == "Contracts/terms.txt"
        return NS(choices=[NS(message=NS(content="Northstar delivery is Friday. [1]"))])
    def no_web(*args, **kwargs):
        raise AssertionError("Local questions must never leave the computer")
    result = answer("What do my files say about Northstar delivery?", root, model, no_web)
    assert "Friday" in result and "Contracts/terms.txt, line 1" in result
    rows, _ = knowledge.retrieve("cobalt invoices", root)
    assert rows and "Cobalt" in rows[0][2]
    document.write_text("Northstar delivery is Wednesday.", encoding="utf-8")
    rows, _ = knowledge.retrieve("Northstar", root)
    assert "Wednesday" in rows[0][2] and all("Friday" not in row[2] for row in rows)
    document.unlink()
    assert knowledge.retrieve("Northstar", root)[0] == []
    with zipfile.ZipFile(data / "supplier.docx", "w") as archive:
        archive.writestr("word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>Bluefin supplier confirmed Monday.</w:t></w:r></w:p></w:body></w:document>')
    rows, _ = knowledge.retrieve("Bluefin", root)
    assert rows[0][0] == "supplier.docx" and rows[0][1] == "paragraph 1"
    (data / "sales.csv").write_text("Region,Amount\nEast,0.10\nEast,0.20\nWest,7.50\nWest,unknown\n", encoding="utf-8")
    result = answer("Total Amount in sales.csv by Region", root, None, no_web)
    assert "East: total Amount = 0.30" in result and "West: total Amount = 7.50" in result
    assert "1 blank or nonnumeric" in result
    assert "count rows = 4" in answer("Count rows in sales.csv", root, None, no_web)
    assert "4 records" in answer("Analyze sales.csv", root, None, no_web)
    assert "exact column" in answer("Sum Missing in sales.csv", root, None, no_web)
    # A PDF containing actual extractable text exercises the bundled dependency.
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 200 Td (Orion warranty lasts twelve months.) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(data / "warranty.pdf")
    rows, _ = knowledge.retrieve("Orion warranty", root)
    assert any(row[0] == "warranty.pdf" and "twelve" in row[2] and row[1] == "page 1" for row in rows)
    (data / "broken.pdf").write_bytes(b"invalid pdf")
    assert "broken.pdf" in knowledge.retrieve("Orion", root)[1]

with TemporaryDirectory() as folder:
    root = Path(folder)
    (root / "Data").mkdir()
    path = root / "Data" / "jobs.json"
    jobs = [{"id":"J-1", "title":"Cobalt install", "status":"delayed", "blocker":"Missing valve",
             "evidence":"Supplier email", "owner":"Sam"}]
    path.write_text(json.dumps(jobs), encoding="utf-8")
    ops = Operations()
    assert "J-1" in ops.answer("What needs my attention today?", root)
    assert "Missing valve" in ops.answer("Open job J-1", root)
    assert "Supplier email" in ops.answer("Why is it delayed?", root)
    assert "CUSTOMER UPDATE" in ops.answer("Draft an update", root)
    jobs[0]["blocker"] = "Schedule changed"
    path.write_text(json.dumps(jobs), encoding="utf-8")
    assert "records changed" in ops.answer("Approve drafts for job J-1", root)
    assert not (root / "Approved").exists()
    assert "CUSTOMER UPDATE" in ops.answer("Draft an update", root)
    assert "Saved both" in ops.answer("Approve drafts for job J-1", root)

print("Knowledge, document formats, exact CSV calculations and stale approval checks passed")

with TemporaryDirectory() as folder:
    root = Path(folder)
    (root / "Data").mkdir()
    (root / "Data" / "private.txt").write_text("Cobalt account secret internal reference.", encoding="utf-8")
    calls = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def raise_for_status(self): pass
        class raw:
            @staticmethod
            def read(*args, **kwargs):
                return b'<a class="result__a" href="https://example.org/public">Public</a><a class="result__snippet">Public supplier information.</a>'
    def public_get(url, **kwargs):
        calls.append(kwargs["params"]["q"])
        return Response()
    result = answer("Compare my documents about Cobalt with web research about public suppliers", root, None, public_get)
    assert calls == ["public suppliers"]
    assert "LOCAL DOCUMENT EVIDENCE" in result and "PUBLIC WEB EVIDENCE" in result
    assert "secret internal" in result
    assert "exact" not in result.casefold()  # no claim the independent sources establish a match
    assert "Data" in answer("What can you do?", root, None, public_get)
print("Combined research keeps document content out of public search")
