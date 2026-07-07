import json
import re
import shutil
from pathlib import Path

root = Path(__file__).resolve().parent.parent
output_dir = root / 'output'
website_dir = root / 'website'
source_json = output_dir / 'sign_mappings_clean.json'
source_signs = output_dir / 'signs'
website_data_dir = website_dir / 'data'
website_signs_dir = website_dir / 'signs'


def humanize_description(text: str) -> str:
    text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)
    text = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text.title()


def main():
    if not source_json.exists():
        raise FileNotFoundError(f'Missing source JSON: {source_json}')
    if not source_signs.exists():
        raise FileNotFoundError(f'Missing source signs directory: {source_signs}')

    website_data_dir.mkdir(parents=True, exist_ok=True)
    website_signs_dir.mkdir(parents=True, exist_ok=True)

    with source_json.open('r', encoding='utf-8') as f:
        signs = json.load(f)

    for item in signs:
        item['description'] = humanize_description(item.get('description', ''))

    target_json = website_data_dir / 'signs.json'
    with target_json.open('w', encoding='utf-8') as f:
        json.dump(signs, f, indent=2, ensure_ascii=False)

    for item in signs:
        src = source_signs / item['filename']
        dest = website_signs_dir / item['filename']
        if not src.exists():
            raise FileNotFoundError(f'Missing sign image: {src}')
        shutil.copy2(src, dest)

    print(f'Website data assembled at {website_dir}')
    print(f'- Sign JSON: {target_json}')
    print(f'- Sign images: {len(signs)} files copied to {website_signs_dir}')


if __name__ == '__main__':
    main()
