import json
from pathlib import Path
from urllib.parse import urlparse

PROJECT_DIR = Path(__file__).resolve().parent
from categories import CATEGORIES
PAGE_TYPES = ['overview', 'locations', 'pricing', 'promotions', 'news']


def valid_url(url):
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)


def load_config():
    config = json.loads((PROJECT_DIR / 'config.json').read_text(encoding='utf-8-sig'))
    if not isinstance(config, dict):
        raise ValueError('config.json must contain an object.')
    for field in ('ollama_host', 'model'):
        if not isinstance(config.get(field), str) or not config[field].strip():
            raise ValueError(f'Invalid configuration: {field}')
    if not valid_url(config['ollama_host']):
        raise ValueError('ollama_host must be a complete HTTP URL.')
    for field in ('num_ctx', 'num_predict', 'input_character_limit', 'fetch_timeout_seconds', 'model_timeout_seconds'):
        if type(config.get(field)) is not int or config[field] <= 0:
            raise ValueError(f'{field} must be a positive integer.')
    if type(config.get('think')) is not bool:
        raise ValueError('think must be true or false.')
    pause = config.get('pause_seconds')
    if type(pause) not in (int, float) or not 0 <= pause <= 60:
        raise ValueError('pause_seconds must be between 0 and 60.')
    return config


def validate_sources(sources):
    if not isinstance(sources, list):
        raise ValueError('sources.json must contain a list.')
    ids = set()
    urls = set()
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError('Every source must be an object.')
        for field in ('source_id', 'brand_name'):
            if not isinstance(source.get(field), str) or not source[field].strip():
                raise ValueError(f'Every source needs {field}.')
        if source['source_id'] in ids:
            raise ValueError('Duplicate source_id: ' + source['source_id'])
        ids.add(source['source_id'])
        if not valid_url(source.get('url')):
            raise ValueError('Invalid URL for ' + source['source_id'])
        url = source['url'].rstrip('/')
        if url in urls:
            raise ValueError('Duplicate URL: ' + source['url'])
        urls.add(url)
        if source.get('category') not in CATEGORIES or source.get('page_type') not in PAGE_TYPES:
            raise ValueError('Invalid category or page_type for ' + source['source_id'])
        if type(source.get('enabled')) is not bool:
            raise ValueError('enabled must be true or false.')
    return sources


def load_sources():
    return validate_sources(json.loads((PROJECT_DIR / 'sources.json').read_text(encoding='utf-8-sig')))
