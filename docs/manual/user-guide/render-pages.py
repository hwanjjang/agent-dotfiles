#!/usr/bin/env python3
"""Render PDF pages for visual review using PDFium; original PDF is unchanged."""
import argparse
from pathlib import Path
import pypdfium2 as pdfium


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('output_directory', type=Path)
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)
    with pdfium.PdfDocument(args.pdf) as doc:
        for index in range(len(doc)):
            path = args.output_directory / f'page-{index+1:03}.png'
            if path.exists():
                parser.exit(1, f'Refusing to replace existing render: {path}\n')
        for index in range(len(doc)):
            page = doc[index]
            try:
                bitmap = page.render(scale=1.5)
                try:
                    bitmap.to_pil().save(args.output_directory / f'page-{index+1:03}.png')
                finally:
                    bitmap.close()
            finally:
                page.close()
    print('Rendered all pages. Inspect images; rendering alone is not visual review.')


if __name__ == '__main__':
    main()
