import json
import uuid
from settings import CATEGORIES, PAGE_TYPES, PROJECT_DIR, load_sources, validate_sources


def choose(label, options):
    for i, option in enumerate(options, 1):
        print(f'{i}. {option}')
    while True:
        answer = input(label + ' (number): ').strip()
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        print('Enter one of the listed numbers.')


def main():
    sources = load_sources()
    brand = input('Brand name: ').strip()
    url = input('Official webpage URL: ').strip()
    category = choose('Category for organising sources', CATEGORIES)
    page_type = choose('Page type', PAGE_TYPES)
    source = dict(source_id=uuid.uuid4().hex, brand_name=brand, url=url,
                  category=category, page_type=page_type, enabled=True)
    validate_sources(sources + [source])
    destination = PROJECT_DIR / 'sources.json'
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(sources + [source], indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(destination)
    print('Source registered. Repeat this command for another page or venue.')
    print('The source category is an organisational label, not a verified branch category.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print(f'Source not registered: {error}')
        raise SystemExit(1)
