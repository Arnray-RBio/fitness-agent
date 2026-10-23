"""Compare source snapshots and original model extractions, without changing records."""
import difflib
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from overview_app import group_captures

FIELDS = ('services', 'programmes', 'branches', 'packages', 'deals')
RECORD_FIELDS = {
    'branches': ('name', 'address'),
    'packages': ('name', 'price', 'currency', 'billing_or_validity', 'sessions'),
    'deals': ('description', 'expiry'),
}


def whitespace(value):
    return ' '.join(value.split())


def normalize(value):
    if isinstance(value, str):
        return whitespace(value)
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


def records(venue, field):
    items = venue.get(field, [])
    result = {}
    for item in items:
        if field in RECORD_FIELDS:
            item = {key: item.get(key) for key in RECORD_FIELDS[field]}
        cleaned = normalize(item)
        result[json.dumps(cleaned, sort_keys=True, ensure_ascii=False)] = cleaned
    return result


def compare(old, new):
    old_venue = old['extraction']['venue']
    new_venue = new['extraction']['venue']
    field_changes = {}
    if normalize(old_venue.get('name')) != normalize(new_venue.get('name')):
        field_changes['brand_name'] = {'before': old_venue.get('name'), 'after': new_venue.get('name')}
    for field in FIELDS:
        before = records(old_venue, field)
        after = records(new_venue, field)
        added = [after[key] for key in sorted(after.keys() - before.keys())]
        absent = [before[key] for key in sorted(before.keys() - after.keys())]
        if added or absent:
            field_changes[field] = {'newly_extracted': added, 'no_longer_extracted': absent}
    source_changed = whitespace(old['webpage_text']) != whitespace(new['webpage_text'])
    if source_changed:
        status = 'source_changed_needs_review'
    elif field_changes:
        status = 'extraction_variation_on_unchanged_text'
    else:
        status = 'no_detected_change'
    warnings = []
    if any(row['extraction'].get('input_truncated') for row in (old, new)):
        warnings.append('At least one extraction used truncated input; missing facts may be outside the supplied text.')
    if old['extraction'].get('model') != new['extraction'].get('model'):
        warnings.append('Recorded model metadata differs or is missing; extraction differences may reflect model settings.')
    if any(any(row['extraction'].get('rejected_items', {}).values()) for row in (old,new)):
        warnings.append('At least one capture has rejected items; evidence filtering may explain missing extracted facts.')
    diff = list(difflib.unified_diff(old['webpage_text'].splitlines(), new['webpage_text'].splitlines(),
                                   fromfile=f"Capture {old['id']}", tofile=f"Capture {new['id']}", lineterm='', n=2)) if source_changed else []
    return {
        'status': status, 'previous_capture_id': old['id'], 'latest_capture_id': new['id'],
        'previous_checked_at_utc': old['checked_at_utc'], 'latest_checked_at_utc': new['checked_at_utc'],
        'source_text_changed': source_changed, 'extracted_fields_changed': bool(field_changes),
        'field_changes': field_changes, 'warnings': warnings,
        'previous_text_sha256': hashlib.sha256(whitespace(old['webpage_text']).encode()).hexdigest(),
        'latest_text_sha256': hashlib.sha256(whitespace(new['webpage_text']).encode()).hexdigest(),
        'source_diff_excerpt': '\n'.join(diff[:160]), 'source_diff_truncated': len(diff)>160,
    }


def latest_batch_failures(project):
    paths = sorted((project / 'data' / 'runs').glob('*.json'), reverse=True)
    if not paths:
        return None
    try:
        run = json.loads(paths[0].read_text(encoding='utf-8'))
        return {'report_file': paths[0].name, 'started_at_utc': run.get('started_at_utc'),
                'finished_at_utc': run.get('finished_at_utc'), 'import_status': run.get('import_status'),
                'failed_pages': [page for page in run.get('pages', []) if page.get('status')=='failed']}
    except (ValueError,OSError) as error:
        return {'report_file': paths[0].name, 'error': str(error)}


def build_report(project):
    database = project / 'data' / 'fitness_agent.db'
    if not database.exists():
        raise ValueError('Database not found.')
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = [dict(row) for row in db.execute('SELECT * FROM captures')]
    groups = group_captures(rows)
    pages = []
    for key, history in groups.items():
        latest = history[0]
        page = {'group_key': key, 'brand': latest['extraction']['venue'].get('name') or latest['brand_name'],
                'source_url': latest['source_url'], 'page_type': latest['registered'].get('page_type', 'unregistered'),
                'snapshots': len(history)}
        if len(history)<2:
            page.update(status='baseline_only', latest_capture_id=latest['id'], latest_checked_at_utc=latest['checked_at_utc'],
                        warnings=['Only one successful capture exists. No comparison is available.'], field_changes={})
        else:
            page.update(compare(history[1],latest))
        pages.append(page)
    return {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'scope': 'Latest two successful captures per webpage; original extractions, not manual reviews.',
            'pages': pages, 'latest_batch': latest_batch_failures(project)}


def save_report(project):
    report = build_report(project)
    destination = project / 'data' / 'changes'
    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path = destination / (stamp + '.json')
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return report,path
