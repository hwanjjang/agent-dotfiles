#!/usr/bin/env python3
"""Build a screenshot manual from a local JSON source; never capture or publish data."""
import argparse
import json
import os
from pathlib import Path
import tempfile
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer


def require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be nonempty text')
    return value


def build(source, output, font=None, overwrite=False):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or (output.exists() and not overwrite):
        raise ValueError('Output exists or would replace the source; choose a new path or --overwrite')
    data = json.loads(source.read_text(encoding='utf-8'))
    title = require_text(data.get('title'), 'title')
    scenario = require_text(data.get('scenario'), 'scenario')
    steps = data.get('steps')
    if not isinstance(steps, list) or not steps:
        raise ValueError('steps must be a nonempty list')
    images = []
    text_values = [title, scenario]
    for i, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            raise ValueError(f'step {i} must be an object')
        for field in ('title', 'instruction', 'expected', 'caption', 'screenshot'):
            text_values.append(require_text(step.get(field), f'step {i}.{field}'))
        relative = Path(step['screenshot'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Screenshots must be relative to the source directory')
        image = (source.parent / relative).resolve()
        if not image.is_relative_to(source.parent) or not image.is_file():
            raise ValueError(f'Missing or escaping screenshot for step {i}')
        if image == output:
            raise ValueError('Output would replace a screenshot')
        ImageReader(str(image)).getSize()
        images.append(image)
    font_name = 'Helvetica'
    if font:
        pdfmetrics.registerFont(TTFont('ManualFont', str(font)))
        font_name = 'ManualFont'
    elif any(ord(c) > 127 for text in text_values for c in text):
        raise ValueError('Non-ASCII content requires --font with a suitable redistributable TTF font')
    width, height = A4
    margin, gap = 42, 10
    # SimpleDocTemplate's frame has six-point padding on each side.
    usable_width, usable_height = width - 2*margin - 12, height - 2*margin - 20 - 12
    styles = {
        'title': ParagraphStyle('Title', fontName=font_name, fontSize=20, leading=25, textColor=colors.HexColor('#163d32')),
        'heading': ParagraphStyle('Heading', fontName=font_name, fontSize=14, leading=19),
        'body': ParagraphStyle('Body', fontName=font_name, fontSize=11, leading=16),
        'caption': ParagraphStyle('Caption', fontName=font_name, fontSize=9, leading=13, textColor=colors.HexColor('#46564e')),
    }
    def paragraph(text, style):
        return Paragraph(escape(text).replace('\n', '<br/>'), styles[style])
    story = []
    for i, (step, image_path) in enumerate(zip(steps, images), 1):
        top = [paragraph(title, 'title'), Spacer(1, gap), paragraph(scenario, 'body'),
               Spacer(1, gap), paragraph(f'{i}. {step["title"]}', 'heading'),
               Spacer(1, gap), paragraph(step['instruction'], 'body'), Spacer(1, gap)]
        bottom = [Spacer(1, gap), paragraph(step['caption'], 'caption'), Spacer(1, gap),
                  paragraph('Expected result: '+step['expected'], 'body')]
        text_height = sum(x.wrap(usable_width, usable_height)[1] for x in top+bottom)
        max_image_height = usable_height-text_height-8
        if max_image_height < 100:
            raise ValueError(f'Step {i} has too much text for a readable screenshot; split the step')
        iw, ih = ImageReader(str(image_path)).getSize()
        scale = min(usable_width/iw, max_image_height/ih)
        story.extend(top+[Image(str(image_path), width=iw*scale, height=ih*scale)]+bottom)
        if i < len(steps):
            story.append(PageBreak())
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.manual-', suffix='.pdf', dir=output.parent)
    os.close(fd)
    def footer(canvas, doc):
        canvas.setFont(font_name, 9)
        canvas.setFillColor(colors.HexColor('#46564e'))
        canvas.drawRightString(width-margin, 24, f'{doc.page} / {len(steps)}')
    try:
        doc = SimpleDocTemplate(temporary, pagesize=A4, leftMargin=margin, rightMargin=margin,
                                topMargin=margin, bottomMargin=margin+20, title=title, author='')
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        # The one-step-per-page promise must hold for the resulting artifact.
        from pypdf import PdfReader
        if len(PdfReader(temporary).pages) != len(steps):
            raise ValueError('Unexpected pagination; shorten or split the overflowing step')
        os.replace(temporary, output)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()
    return len(steps)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--font', type=Path, help='TTF font with glyphs for the document language')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    try:
        pages = build(args.source, args.output, args.font, args.overwrite)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'Manual build failed: {error}\n')
    print(f'Built {pages} pages. Render and inspect every page before delivery.')


if __name__ == '__main__':
    main()
