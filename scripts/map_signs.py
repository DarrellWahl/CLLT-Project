import json
import csv
from pathlib import Path


def load_legend(path: Path):
    with path.open('r', encoding='utf-8') as f:
        entries = json.load(f)
    legend = {entry['code']: entry['description'] for entry in entries}
    return legend


def load_metadata(path: Path):
    with path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = [
            {
                'page': int(row['page']),
                'index': int(row['index']),
                'filename': row['filename'],
                'x': int(row['x']),
                'y': int(row['y']),
                'w': int(row['w']),
                'h': int(row['h']),
            }
            for row in reader
        ]
    return rows


def build_code_sequence(codes):
    # Sort codes by numeric order and alpha
    def code_key(code: str):
        prefix = ''.join(filter(str.isalpha, code))
        suffix = code[len(prefix):].replace('.', '')
        return (prefix, int(suffix))
    return sorted(codes, key=code_key)


def map_crops_to_codes(metadata, codes):
    # Map by page then index order: assume crop order matches legend order by page
    per_page = {}
    for row in metadata:
        per_page.setdefault(row['page'], []).append(row)
    for page, rows in per_page.items():
        rows.sort(key=lambda r: (r['y'], r['x']))

    mapped = []
    code_index = 0
    for page in sorted(per_page.keys()):
        rows = per_page[page]
        for row in rows:
            if code_index >= len(codes):
                break
            mapped.append({
                'page': page,
                'filename': row['filename'],
                'code': codes[code_index],
            })
            code_index += 1
    return mapped


def save_mappings(mapped, legend, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as f:
        json.dump([
            {
                'filename': item['filename'],
                'page': item['page'],
                'code': item['code'],
                'description': legend.get(item['code'], ''),
            }
            for item in mapped
        ], f, indent=2, ensure_ascii=False)


def main():
    legend = load_legend(Path('output/sign_legend.json'))
    metadata = load_metadata(Path('output/signs_metadata.csv'))
    codes = build_code_sequence(list(legend.keys()))
    mapped = map_crops_to_codes(metadata, codes)
    save_mappings(mapped, legend, Path('output/sign_mappings.json'))
    print(f'Saved {len(mapped)} sign mappings to output/sign_mappings.json')


if __name__ == '__main__':
    main()
