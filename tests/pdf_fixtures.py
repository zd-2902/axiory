"""Tiny in-memory, explicitly synthetic PDFs; no downloaded/binary fixtures."""

from io import BytesIO

from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)


def synthetic_pdf(
    *pages: str | None, encrypted: bool = False, password: str = "synthetic-password"
) -> bytes:
    writer = PdfWriter()
    writer.add_metadata({"/Title": "SYNTHETIC Axiory test fixture"})
    for text in pages:
        page = writer.add_blank_page(width=595, height=842)
        if text is None:
            continue
        stream = DecodedStreamObject()
        if text == "[image]":
            image = DecodedStreamObject()
            image.set_data(b"\xff\xff\xff")
            image.update(
                {
                    NameObject("/Type"): NameObject("/XObject"),
                    NameObject("/Subtype"): NameObject("/Image"),
                    NameObject("/Width"): NumberObject(1),
                    NameObject("/Height"): NumberObject(1),
                    NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
                    NameObject("/BitsPerComponent"): NumberObject(8),
                }
            )
            page[NameObject("/Resources")] = DictionaryObject(
                {
                    NameObject("/XObject"): DictionaryObject(
                        {NameObject("/Im0"): writer._add_object(image)}
                    )
                }
            )
            stream.set_data(b"q 100 0 0 100 50 600 cm /Im0 Do Q")
        elif text == "[inline-image]":
            stream.set_data(
                b"q 100 0 0 100 50 600 cm BI /W 1 /H 1 /CS /RGB /BPC 8 ID \xff\xff\xff\nEI Q"
            )
        elif text == "[vector]":
            stream.set_data(b"0 0 100 100 re S")
        else:
            font = DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                    NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
                }
            )
            page[NameObject("/Resources")] = DictionaryObject(
                {
                    NameObject("/Font"): DictionaryObject(
                        {NameObject("/F1"): writer._add_object(font)}
                    )
                }
            )
            escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream.set_data(f"BT /F1 12 Tf 50 750 Td ({escaped}) Tj ET".encode("cp1252"))
            if text == "[broken-stream]":
                stream[NameObject("/Filter")] = NameObject("/UnsupportedSyntheticFilter")
        page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        # RC4 is used only to construct a rejection fixture, never for data protection.
        writer.encrypt(password, algorithm="RC4-128")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
