"""Back up and migrate current register categories; never rewrite captures/reviews."""
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from categories import CATEGORY_MAP, translate_branch

PROJECT_DIR = Path(__file__).resolve().parent


def main():
    database = PROJECT_DIR / 'data' / 'fitness_agent.db'
    source_file = PROJECT_DIR / 'sources.json'
    sources = json.loads(source_file.read_text(encoding='utf-8-sig'))
    if not isinstance(sources, list):
        raise ValueError('sources.json must be a list.')
    source_changes = 0
    for source in sources:
        value = source.get('category')
        if value not in CATEGORY_MAP:
            raise ValueError(f'Unsupported source category {value!r}. Resolve it before migration; no files changed.')
        target = CATEGORY_MAP[value]
        source_changes += value != target
        source['category'] = target
    if not database.exists():
        raise ValueError('Database not found; no files changed.')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup_dir = PROJECT_DIR / 'data' / 'backups' / ('categories_' + stamp)
    backup_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(source_file, backup_dir / 'sources.json')
    temporary = source_file.with_name('sources.categories.tmp')
    temporary.write_text(json.dumps(sources, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    updated = 0
    legacy = 0
    source_written = False
    try:
        with sqlite3.connect(database, timeout=15) as connection:
            connection.row_factory = sqlite3.Row
            with sqlite3.connect(backup_dir / 'fitness_agent.db') as backup:
                connection.backup(backup)
            connection.execute('BEGIN IMMEDIATE')
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'registry_branches' in tables:
                if 'registry_revisions' not in tables:
                    raise ValueError('Registry revision table missing. No migration applied.')
                for row in connection.execute('SELECT * FROM registry_branches').fetchall():
                    original = json.loads(row['details_json'])
                    changed = translate_branch(original)
                    legacy += bool(changed.get('legacy_categories'))
                    if changed == original:
                        continue
                    now = datetime.now(timezone.utc).isoformat()
                    revision = row['revision'] + 1
                    payload = json.dumps(changed, ensure_ascii=False)
                    connection.execute('UPDATE registry_branches SET details_json=?,revision=?,updated_at_utc=? WHERE id=?',
                                       (payload, revision, now, row['id']))
                    connection.execute('INSERT INTO registry_revisions(branch_id,revision,details_json,saved_at_utc) VALUES (?,?,?,?)',
                                       (row['id'], revision, payload, now))
                    updated += 1
            # Commit source replacement and SQL within the same guarded operation.
            temporary.replace(source_file)
            source_written = True
            connection.commit()
    except Exception:
        if source_written:
            shutil.copy2(backup_dir / 'sources.json', source_file)
        raise
    finally:
        temporary.unlink(missing_ok=True)
    print(f'Source entries relabelled: {source_changes}')
    print(f'Permanent branch records relabelled: {updated}')
    print(f'Branches with archived legacy categories: {legacy}')
    print('Original captures, links, earlier reviews and earlier branch revisions preserved.')
    print('Categories: strength, mobility, recovery, longevity clinics')
    print(f'Backup: {backup_dir}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as error:
        print(f'Migration failed: {error}')
        raise SystemExit(1)
