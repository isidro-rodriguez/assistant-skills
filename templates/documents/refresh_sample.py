#!/usr/bin/env python3
"""Update every index of an .odt through LibreOffice (UNO) and export it to PDF.

build_templates.py runs this with a Python that can import uno (LibreOffice's
own, or the system one with python3-uno), since headless conversion leaves
tables of contents as they were saved. Standard library and uno only.

  python3 refresh_sample.py --profile /tmp/profile muestra.odt muestra.pdf
"""

from __future__ import annotations

import argparse
import contextlib
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import uno
from com.sun.star.beans import PropertyValue
from com.sun.star.connection import NoConnectException
from com.sun.star.lang import DisposedException


def props(**values) -> tuple:
    result = []
    for name, value in values.items():
        prop = PropertyValue()
        prop.Name, prop.Value = name, value
        result.append(prop)
    return tuple(result)


def connect(pipe: str, timeout: float = 60):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local
    )
    deadline = time.monotonic() + timeout
    while True:
        try:
            return resolver.resolve(
                f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext"
            )
        except NoConnectException:  # until soffice is listening
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("odt", type=Path, help="document, updated in place")
    parser.add_argument("pdf", type=Path, help="PDF to write")
    parser.add_argument(
        "--profile",
        type=Path,
        required=True,
        help="folder for a throwaway LibreOffice profile",
    )
    parser.add_argument("--soffice", default=shutil.which("soffice") or "soffice")
    args = parser.parse_args()

    pipe = f"refresh-{uuid.uuid4().hex}"
    office = subprocess.Popen(
        [
            args.soffice,
            f"-env:UserInstallation={args.profile.resolve().as_uri()}",
            "--headless",
            "--invisible",
            "--norestore",
            f"--accept=pipe,name={pipe};urp;",
        ]
    )
    try:
        context = connect(pipe)
        desktop = context.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", context
        )
        doc = desktop.loadComponentFromURL(
            args.odt.resolve().as_uri(), "_blank", 0, props(Hidden=True)
        )
        # Twice: the first pass can move pages, which changes the page numbers.
        for _ in range(2):
            indexes = doc.getDocumentIndexes()
            for i in range(indexes.getCount()):
                indexes.getByIndex(i).update()
            doc.refresh()
        doc.storeToURL(args.odt.resolve().as_uri(), props(FilterName="writer8"))
        doc.storeToURL(
            args.pdf.resolve().as_uri(), props(FilterName="writer_pdf_Export")
        )
        doc.close(True)
        # The bridge drops as soffice exits.
        with contextlib.suppress(DisposedException):
            desktop.terminate()
        office.wait(timeout=60)
    finally:
        if office.poll() is None:
            office.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
