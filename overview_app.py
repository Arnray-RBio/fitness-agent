"""Read-only overview of latest webpage captures and their history."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_DIR / 'data' / 'fitness_agent.db'
TRACKING_KEYS = {'gclid', 'fbclid', 'msclkid', 'gad_source', 'gad_campaignid', 'gbraid', 'wbraid'}


def page_key(url):
    parsed = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
             if k.lower() not in TRACKING_KEYS and not k.lower().startswith('utm_')]
    # Preserve scheme, path case and meaningful query parameters.
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(),
                      parsed.path.rstrip('/') or '/', urlencode(sorted(query)), ''))


def capture_time(row):
    value = datetime.fromisoformat(row['checked_at_utc'].replace('Z', '+00:00'))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc), row['id']


def group_captures(rows):
    """Link old URL-only captures to source IDs seen in newer captures."""
    prepared = []
    aliases = {}
    for row in rows:
        item = dict(row)
        item['extraction'] = json.loads(row['extraction_json'])
        source = item['extraction'].get('registered_source') or {}
        item['registered'] = source
        item['urls'] = {page_key(url) for url in (
            source.get('url'), item['extraction'].get('requested_url'), row['source_url']
        ) if url}
        prepared.append(item)
        if source.get('source_id'):
            for url in item['urls']:
                aliases.setdefault(url, set()).add(source['source_id'])
    groups = {}
    for item in prepared:
        identifier = item['registered'].get('source_id')
        possible = set().union(*(aliases.get(url, set()) for url in item['urls']))
        if identifier:
            key = 'source:' + identifier
        elif len(possible) == 1:
            key = 'source:' + next(iter(possible))
        else:
            key = 'url:' + page_key(item['source_url'])
        groups.setdefault(key, []).append(item)
    for history in groups.values():
        history.sort(key=capture_time, reverse=True)
    return dict(sorted(groups.items(), key=lambda pair: capture_time(pair[1][0]), reverse=True))


def load_data():
    with sqlite3.connect(DATABASE_PATH.as_uri() + '?mode=ro', uri=True) as connection:
        connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in connection.execute('SELECT * FROM captures')]
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        reviews = {}
        if 'capture_reviews' in tables:
            for review in connection.execute('SELECT * FROM capture_reviews ORDER BY id'):
                reviews[review['capture_id']] = dict(review)
    return rows, reviews


def main():
    st.set_page_config(page_title='Fitness research overview', layout='wide')
    st.title('Fitness research overview')
    st.caption('Latest capture per webpage. Historical captures and reviews are preserved.')
    if not DATABASE_PATH.exists():
        st.error('Database not found. Run import_captures.py or run_batch.py first.')
        st.stop()
    try:
        rows, reviews = load_data()
        groups = group_captures(rows)
    except (sqlite3.Error, ValueError, KeyError, TypeError) as error:
        st.error(f'Could not load captures: {error}')
        st.stop()
    if not groups:
        st.info('No captures yet.')
        st.stop()
    latest = [history[0] for history in groups.values()]
    first, second, third = st.columns(3)
    first.metric('Tracked webpage groups', len(groups))
    second.metric('Stored captures', len(rows))
    third.metric('Latest captures without reviews', sum(row['id'] not in reviews for row in latest))
    st.info('These are webpage groups and capture snapshots, not unique brands or operating-venue counts.')
    summaries = []
    for key, history in groups.items():
        row = history[0]
        review = reviews.get(row['id'])
        venue = json.loads(review['corrected_venue_json']) if review else row['extraction']['venue']
        summaries.append({'Capture ID': row['id'], 'Brand': venue.get('name') or row['brand_name'] or 'Unknown',
                          'Page type': row['registered'].get('page_type', 'unregistered'),
                          'Latest checked (UTC)': row['checked_at_utc'],
                          'Review': review['status'] if review else 'not_reviewed',
                          'Branch candidates': len(venue.get('branches', [])),
                          'Snapshots': len(history), 'URL': row['source_url']})
    st.dataframe(summaries, width='stretch', hide_index=True)
    keys = list(groups)
    labels = {key: f"{summary['Brand']} | {summary['Page type']} | {summary['URL']}" for key, summary in zip(keys, summaries)}
    chosen = st.selectbox('Choose a webpage group', keys, format_func=lambda key: labels[key])
    history = groups[chosen]
    view = st.radio('View', ['Latest capture', 'History'], horizontal=True)
    if view == 'History':
        selected = st.selectbox('Historical capture', [row['id'] for row in history],
            format_func=lambda identifier: next(
                f"Capture {row['id']} | {row['checked_at_utc']}" for row in history if row['id'] == identifier))
        row = next(row for row in history if row['id'] == selected)
    else:
        row = history[0]
    review = reviews.get(row['id'])
    venue = json.loads(review['corrected_venue_json']) if review else row['extraction']['venue']
    st.subheader(f"Capture {row['id']}: {venue.get('name') or 'Unknown brand'}")
    st.write('Source:', row['source_url'])
    st.caption(f"Checked: {row['checked_at_utc']} | Review: {review['status'] if review else 'not_reviewed'}")
    st.caption('Showing the latest saved review for this capture, if available. Otherwise showing the original extraction.')
    if row['extraction'].get('input_truncated'):
        st.warning('Model input was truncated for this capture.')
    a, b = st.columns(2)
    with a:
        st.write('Services', venue.get('services', []))
    with b:
        st.write('Programmes', venue.get('programmes', []))
    for field in ('branches', 'packages', 'deals'):
        st.subheader(field.capitalize())
        if venue.get(field):
            st.json(venue[field])
        else:
            st.caption('No items recorded. This does not prove that none exist.')
    if review:
        st.subheader('Review notes')
        st.text(review['notes'] or 'No notes.')
    with st.expander('Flagged extraction items'):
        st.json(row['extraction'].get('rejected_items', {}))
    with st.expander('Full saved webpage text'):
        st.text_area('Source text', row['webpage_text'], height=450, disabled=True, key=f"text_{row['id']}")
    st.caption(f"To edit: open review_app.py and choose Capture {row['id']}.")
    st.code('.venv313\\Scripts\\python.exe -m streamlit run review_app.py --server.port 8502', language='text')


if __name__ == '__main__':
    main()
