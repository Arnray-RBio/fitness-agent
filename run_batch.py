import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from settings import PROJECT_DIR, load_config, load_sources


def main():
    parser = argparse.ArgumentParser(description='Collect registered venue pages and import successful captures.')
    parser.add_argument('--dry-run', action='store_true', help='Validate and list pages without fetching, extracting or importing.')
    args = parser.parse_args()
    config = load_config()
    sources = [source for source in load_sources() if source['enabled']]
    print(f"Model: {config['model']} | Enabled pages: {len(sources)}", flush=True)
    for source in sources:
        print(f"  {source['brand_name']} | {source['page_type']} | {source['url']}")
    if args.dry_run:
        print('Validation passed. No webpages fetched or database records written.')
        return 0
    if not sources:
        print('Register a source before running collection.')
        return 1
    # Import only for a real run; dry-run works without Ollama or the scraping packages.
    from collector import collect_page
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    log_dir = PROJECT_DIR / 'data' / 'runs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f'{stamp}.json'
    report = dict(started_at_utc=datetime.now(timezone.utc).isoformat(), model=config['model'],
                  pages=[], import_status='not_started')

    def save_report():
        log_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')

    save_report()
    for number, source in enumerate(sources, 1):
        print(f"\n[{number}/{len(sources)}] {source['brand_name']} — {source['page_type']}", flush=True)
        started = time.monotonic()
        entry = dict(source=source)
        try:
            path = collect_page(source['url'], config, source=source)
            output = json.loads(path.read_text(encoding='utf-8'))
            entry.update(status='captured_needs_review', capture_file=path.name,
                         input_truncated=output['input_truncated'])
        except Exception as error:
            entry.update(status='failed', error_type=type(error).__name__, error=str(error))
            print(f"FAILED: {type(error).__name__}: {error}", flush=True)
        entry['elapsed_seconds'] = round(time.monotonic() - started, 2)
        report['pages'].append(entry)
        save_report()
        if number < len(sources):
            time.sleep(config['pause_seconds'])
    # Reuse the existing importer and its table definition; no database migration.
    imported = subprocess.run([sys.executable, str(PROJECT_DIR / 'import_captures.py')],
                              cwd=PROJECT_DIR, capture_output=True, text=True)
    report['import_output'] = imported.stdout + imported.stderr
    print(report['import_output'], flush=True)
    # The original importer reports invalid files in stdout but returns zero.
    clean_import = imported.returncode == 0 and 'Files needing attention: 0' in imported.stdout
    report['import_status'] = 'completed' if clean_import else 'needs_attention'
    report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    save_report()
    successful = sum(page['status'] == 'captured_needs_review' for page in report['pages'])
    print(f'Pages captured: {successful}; failed: {len(sources) - successful}')
    print(f'Run report: {log_path}')
    print('Refresh the review app. Captures are not verified venues or closure confirmations.')
    return 0 if successful == len(sources) and clean_import else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print(f'Batch could not start: {error}')
        raise SystemExit(1)
