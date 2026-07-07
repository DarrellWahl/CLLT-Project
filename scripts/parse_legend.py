import json
import re
from pathlib import Path
import fitz


def normalize_line(line: str) -> str:
    line = line.replace('\xa0', ' ')
    line = re.sub(r'(?:(?:[A-Za-z]\s+){2,}[A-Za-z])', lambda m: m.group(0).replace(' ', ''), line)
    line = re.sub(r'\s*\.\s*', '.', line)
    line = re.sub(r'\s*,\s*', ', ', line)
    line = re.sub(r'\s*&\s*', ' & ', line)
    line = re.sub(r'\s+', ' ', line)
    return line.strip()


def split_codes(code_part: str):
    code_part = code_part.replace('(', '').replace(')', '')
    code_part = code_part.replace(' and ', ', ')
    code_part = code_part.replace('&', ', ')
    parts = [p.strip() for p in re.split(r'[;,]', code_part) if p.strip()]
    return [part.replace(' ', '').upper() for part in parts]


def is_valid_description(line: str) -> bool:
    if not line:
        return False
    letters = sum(ch.isalpha() for ch in line)
    digits = sum(ch.isdigit() for ch in line)
    if letters < 3:
        return False
    if digits > letters:
        return False
    if re.fullmatch(r'[\d\s\W]+', line):
        return False
    return True


def parse_block_text(text: str):
    entries = []
    lines = [normalize_line(line) for line in text.splitlines() if line.strip()]
    current_codes = []
    code_pattern = re.compile(r'^(?P<codes>R\d{1,3}(?:\.\d+)?(?:[,&]\s*R\d{1,3}(?:\.\d+)?)*)\s*(?P<desc>.*)$', re.IGNORECASE)

    for line in lines:
        match = code_pattern.match(line)
        if match:
            codes = split_codes(match.group('codes'))
            desc = match.group('desc').strip()
            if desc and is_valid_description(desc):
                for code in codes:
                    entries.append({'code': code, 'description': desc})
                current_codes = []
            else:
                current_codes = codes
            continue

        if current_codes and is_valid_description(line):
            for code in current_codes:
                entries.append({'code': code, 'description': line})
            current_codes = []

    return entries


def main():
    pdf_path = Path('assets/pdf/Road Traffic Signs.pdf')
    output_path = Path('output/sign_legend.json')
    pdf = fitz.open(pdf_path)
    page = pdf[4]
    blocks = page.get_text('blocks')
    legend_blocks = [b for b in blocks if b[0] < 1320 and 150 < b[1] < 1800 and len(b[4].strip()) > 20]

    entries = []
    for (_, _, _, _, text, _, _) in legend_blocks:
        entries.extend(parse_block_text(text))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    print(f'Saved {len(entries)} legend entries to {output_path}')


if __name__ == '__main__':
    main()
