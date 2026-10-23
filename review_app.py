import copy
import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

DATABASE_PATH = Path(__file__).resolve().parent / 'data' / 'fitness_agent.db'
from categories import CATEGORIES, translate_branch
OPERATING_STATUSES = ['unknown', 'opening_soon', 'operating', 'temporarily_closed', 'permanently_closed']
REVIEW_STATUSES = ['in_progress', 'reviewed', 'rejected']


def valid_url(value):
    parsed = urlparse(value)
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)


def validate_branches(branches):
    for number, branch in enumerate(branches, 1):
        if not branch['name'].strip():
            raise ValueError(f'Branch {number}: enter a name or exclude this branch.')
        status = branch['operating_status']
        checked = branch.get('verified_on')
        if checked:
            verified = date.fromisoformat(checked)
            if verified > datetime.now().astimezone().date():
                raise ValueError(f'Branch {number}: verification date cannot be in the future.')
        if status != 'unknown':
            if not branch['status_evidence'].strip() or not checked:
                raise ValueError(f'Branch {number}: status requires evidence and a verification date.')
            if not valid_url(branch['verification_source_url']):
                raise ValueError(f'Branch {number}: enter a complete verification source URL.')
        if branch['address'] and not branch['address_evidence']:
            raise ValueError(f'Branch {number}: add address evidence, or leave the address blank.')


def lines(value):
    return list(dict.fromkeys(line.strip() for line in value.splitlines() if line.strip()))


def main():
    st.set_page_config(page_title='Review venue records', layout='wide')
    st.title('Review venue records')
    st.caption('Structured branch reviews. Original captures and earlier reviews are preserved.')
    if not DATABASE_PATH.exists():
        st.error('Database not found. Run import_captures.py first.')
        st.stop()

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute('''CREATE TABLE IF NOT EXISTS capture_reviews (
            id INTEGER PRIMARY KEY,
            capture_id INTEGER NOT NULL,
            reviewed_at_utc TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT NOT NULL,
            corrected_venue_json TEXT NOT NULL,
            FOREIGN KEY (capture_id) REFERENCES captures(id)
        )''')
        captures = [dict(row) for row in connection.execute(
            'SELECT * FROM captures ORDER BY checked_at_utc DESC, id DESC'
        )]
    if not captures:
        st.info('No captures available.')
        st.stop()
    capture_by_id = {row['id']: row for row in captures}
    selected_id = st.selectbox(
        'Choose a capture', list(capture_by_id), key='capture_selector',
        format_func=lambda identifier: (
            f"Capture {identifier} | {capture_by_id[identifier]['brand_name']} | "
            f"{capture_by_id[identifier]['checked_at_utc']}"
        ),
    )
    capture = capture_by_id[selected_id]
    extraction = json.loads(capture['extraction_json'])
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        previous = connection.execute(
            'SELECT * FROM capture_reviews WHERE capture_id = ? ORDER BY id DESC LIMIT 1',
            (selected_id,),
        ).fetchone()
    starting = json.loads(previous['corrected_venue_json']) if previous else extraction['venue']
    # Keys include the saved review version, so a successful save reloads its values.
    prefix = f"capture_{selected_id}_review_{previous['id'] if previous else 0}"
    if st.session_state.pop(f'saved_{selected_id}', False):
        st.success('Review saved. Original capture and earlier reviews preserved.')
    # Translate historical labels for display; original reviews stay unchanged.
    starting = dict(starting)
    starting['branches'] = [translate_branch(branch) for branch in starting.get('branches', [])]
    if any(branch.get('legacy_categories') for branch in starting['branches']):
        st.warning('Some previous categories are retained as legacy_categories and are excluded from the four current categories.')

    st.write('Source:', capture['source_url'])
    st.info('A listed branch is not proof that it is operating. These reviews do not yet update counts across captures.')
    if extraction.get('input_truncated'):
        st.warning('The model received only part of this page. The saved text below is the full capture.')
    if previous:
        st.caption(f"Latest saved review: {previous['reviewed_at_utc']} | {previous['status']}")

    left, right = st.columns(2)
    with right:
        st.subheader('Saved source')
        search = st.text_input('Find text in the capture', key=f'search_{selected_id}')
        if search.strip():
            source_lines = capture['webpage_text'].splitlines()
            matches = [i for i, line in enumerate(source_lines) if search.casefold() in line.casefold()]
            st.caption(f'{len(matches)} matching lines; showing up to 20.')
            for i in matches[:20]:
                st.code('\n'.join(source_lines[max(0, i - 2):i + 3]), language=None)
        st.text_area('Full saved webpage text', capture['webpage_text'], height=500,
                     disabled=True, key=f'source_{selected_id}')
        with st.expander('Flagged extraction items'):
            st.json(extraction.get('rejected_items', {}))
        with st.expander('Original extraction'):
            st.json(extraction)

    with left:
        with st.form(f'{prefix}_form'):
            brand = st.text_input('Brand name', starting.get('name') or '', key=f'{prefix}_brand')
            services = st.text_area('Services: one general activity or facility per line',
                                    '\n'.join(starting.get('services', [])), key=f'{prefix}_services')
            programmes = st.text_area('Named programmes: one per line',
                                      '\n'.join(starting.get('programmes', [])), key=f'{prefix}_programmes')
            st.subheader('Branch reviews')
            st.caption('Categories describe services confirmed at this branch. Leave them empty if uncertain. Verification dates use YYYY-MM-DD.')
            edited_branches = []
            excluded_branches = []
            for index, original in enumerate(starting.get('branches', [])):
                key = f'{prefix}_branch_{index}'
                with st.expander(f"Branch {index + 1}: {original.get('name', 'Unnamed')}", expanded=True):
                    include = st.checkbox('Keep this branch candidate', value=True, key=f'{key}_include')
                    branch = copy.deepcopy(original)
                    branch['name'] = st.text_input('Branch name', original.get('name') or '', key=f'{key}_name').strip()
                    branch['address'] = st.text_input('Address (blank if unknown)', original.get('address') or '', key=f'{key}_address').strip() or None
                    branch['name_evidence'] = st.text_area('Name evidence', original.get('name_evidence') or original.get('evidence') or '', key=f'{key}_name_evidence').strip()
                    branch['address_evidence'] = st.text_area('Address evidence (copy supporting text)', original.get('address_evidence') or '', key=f'{key}_address_evidence').strip() or None
                    if not branch['address']:
                        branch['address_evidence'] = None
                    branch['categories'] = st.multiselect('Categories', CATEGORIES,
                        default=[c for c in original.get('categories', []) if c in CATEGORIES], key=f'{key}_categories')
                    old_status = original.get('operating_status', 'unknown')
                    branch['operating_status'] = st.selectbox('Operating status', OPERATING_STATUSES,
                        index=OPERATING_STATUSES.index(old_status) if old_status in OPERATING_STATUSES else 0,
                        key=f'{key}_status')
                    branch['status_evidence'] = st.text_area('Evidence supporting operating status',
                        original.get('status_evidence') or '', key=f'{key}_status_evidence').strip()
                    branch['verification_source_url'] = st.text_input('Verification source URL',
                        original.get('verification_source_url') or '', key=f'{key}_url').strip()
                    branch['verified_on'] = st.text_input('Date you checked the evidence (YYYY-MM-DD)',
                        original.get('verified_on') or '', key=f'{key}_date').strip() or None
                    branch['review_notes'] = st.text_area('Branch notes', original.get('review_notes') or '', key=f'{key}_notes')
                    if include:
                        edited_branches.append(branch)
                    else:
                        excluded_branches.append(branch)
            if not starting.get('branches'):
                st.caption('No branch candidates in this capture. Adding new branches will be a later step.')
            st.caption('Packages and deals are preserved as saved; their terms still need manual review.')
            with st.expander('Packages and deals'):
                st.json({field: starting.get(field, []) for field in ('packages', 'deals')})
            old_review_status = previous['status'] if previous else 'in_progress'
            review_status = st.selectbox('Review status', REVIEW_STATUSES,
                index=REVIEW_STATUSES.index(old_review_status) if old_review_status in REVIEW_STATUSES else 0,
                key=f'{prefix}_status')
            notes = st.text_area('Review notes and outstanding questions',
                previous['notes'] if previous else '', key=f'{prefix}_notes')
            submitted = st.form_submit_button('Save review')
        if submitted:
            try:
                validate_branches(edited_branches)
                corrected = copy.deepcopy(starting)
                corrected.update(name=brand.strip() or None, services=lines(services),
                                 programmes=lines(programmes), branches=edited_branches)
                corrected['excluded_branches'] = starting.get('excluded_branches', []) + excluded_branches
                with sqlite3.connect(DATABASE_PATH) as connection:
                    connection.execute('PRAGMA foreign_keys = ON')
                    connection.execute('''INSERT INTO capture_reviews
                        (capture_id, reviewed_at_utc, status, notes, corrected_venue_json)
                        VALUES (?, ?, ?, ?, ?)''', (selected_id, datetime.now(timezone.utc).isoformat(),
                        review_status, notes, json.dumps(corrected, ensure_ascii=False)))
                st.session_state[f'saved_{selected_id}'] = True
                st.rerun()
            except (ValueError, sqlite3.Error) as error:
                st.error(f'Review not saved: {error}')
        with st.expander('Latest saved review JSON'):
            st.json(starting)


if __name__ == '__main__':
    main()
