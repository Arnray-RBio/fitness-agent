"""Permanent branch records, explicit capture links and append-only revisions."""
import json
import sqlite3
from datetime import date, datetime, timezone
from urllib.parse import urlsplit

from categories import CATEGORIES
STATUSES = ['unknown', 'opening_soon', 'operating', 'temporarily_closed', 'permanently_closed']


def normalized(value):
    return ' '.join(value.casefold().split())


def connect(path):
    connection = sqlite3.connect(path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    return connection


def initialize(path):
    with connect(path) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS registry_brands (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            name_key TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS registry_branches (
            id INTEGER PRIMARY KEY,
            brand_id INTEGER NOT NULL REFERENCES registry_brands(id),
            name TEXT NOT NULL,
            name_key TEXT NOT NULL,
            details_json TEXT NOT NULL,
            revision INTEGER NOT NULL,
            updated_at_utc TEXT NOT NULL,
            UNIQUE(brand_id, name_key)
        );
        CREATE TABLE IF NOT EXISTS registry_links (
            id INTEGER PRIMARY KEY,
            branch_id INTEGER NOT NULL REFERENCES registry_branches(id),
            capture_id INTEGER NOT NULL REFERENCES captures(id),
            review_version INTEGER NOT NULL,
            branch_index INTEGER NOT NULL,
            snapshot_json TEXT NOT NULL,
            linked_at_utc TEXT NOT NULL,
            UNIQUE(capture_id, review_version, branch_index)
        );
        CREATE TABLE IF NOT EXISTS registry_revisions (
            id INTEGER PRIMARY KEY,
            branch_id INTEGER NOT NULL REFERENCES registry_branches(id),
            revision INTEGER NOT NULL,
            details_json TEXT NOT NULL,
            saved_at_utc TEXT NOT NULL,
            UNIQUE(branch_id, revision)
        );
        ''')


def validate(details):
    if not details.get('name', '').strip():
        raise ValueError('A branch needs a name.')
    if details.get('operating_status') not in STATUSES:
        raise ValueError('Invalid operating status.')
    if any(c not in CATEGORIES for c in details.get('categories', [])):
        raise ValueError('Invalid category.')
    if details.get('address') and not details.get('address_evidence', '').strip():
        raise ValueError('Supply address evidence, or leave the address blank.')
    if not details.get('name_evidence', '').strip():
        raise ValueError('Supply evidence identifying this branch.')
    checked = details.get('verified_on')
    if checked:
        value = date.fromisoformat(checked)
        if value > datetime.now().astimezone().date():
            raise ValueError('Verification date cannot be in the future.')
    if details['operating_status'] != 'unknown':
        url = urlsplit(details.get('verification_source_url', ''))
        if not checked or not details.get('status_evidence', '').strip():
            raise ValueError('Operating status requires evidence and a verification date.')
        if url.scheme not in {'http', 'https'} or not url.netloc:
            raise ValueError('Operating status requires a complete verification source URL.')
    if details.get('categories') and not details.get('category_evidence', '').strip():
        raise ValueError('Supply evidence that these services are available at this branch.')


def get_branches(path):
    with connect(path) as db:
        rows = db.execute('''SELECT b.*, r.name AS brand_name,
            (SELECT COUNT(*) FROM registry_links l WHERE l.branch_id=b.id) AS observations
            FROM registry_branches b JOIN registry_brands r ON b.brand_id=r.id
            ORDER BY r.name,b.name''').fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item['details'] = json.loads(item['details_json'])
        result.append(item)
    return result


def get_brands(path):
    with connect(path) as db:
        return [dict(row) for row in db.execute('SELECT * FROM registry_brands ORDER BY name')]


def get_links(path):
    with connect(path) as db:
        return [dict(row) for row in db.execute('SELECT * FROM registry_links ORDER BY id')]


def check_candidate(db, candidate):
    capture_id, version, index = candidate['capture_id'], candidate['review_version'], candidate['branch_index']
    if version:
        row = db.execute('SELECT corrected_venue_json FROM capture_reviews WHERE id=? AND capture_id=?',
                         (version, capture_id)).fetchone()
        if row is None:
            raise ValueError('The selected review no longer exists.')
        venue = json.loads(row[0])
    else:
        row = db.execute('SELECT extraction_json FROM captures WHERE id=?', (capture_id,)).fetchone()
        if row is None:
            raise ValueError('The selected capture no longer exists.')
        venue = json.loads(row[0])['venue']
    branches = venue.get('branches', [])
    if index < 0 or index >= len(branches) or branches[index] != candidate['snapshot']:
        raise ValueError('Candidate changed. Refresh and select it again.')
    return db.execute('SELECT branch_id FROM registry_links WHERE capture_id=? AND review_version=? AND branch_index=?',
                      (capture_id, version, index)).fetchone()


def add_link(db, branch_id, candidate):
    db.execute('''INSERT INTO registry_links
        (branch_id,capture_id,review_version,branch_index,snapshot_json,linked_at_utc)
        VALUES (?,?,?,?,?,?)''', (branch_id,candidate['capture_id'],candidate['review_version'],
        candidate['branch_index'],json.dumps(candidate['snapshot'],ensure_ascii=False),datetime.now(timezone.utc).isoformat()))


def create_branch(path, brand_name, details, candidate):
    validate(details)
    if not brand_name.strip():
        raise ValueError('Enter a brand name.')
    with connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        if check_candidate(db, candidate):
            raise ValueError('This observation is already linked. No branch was created.')
        db.execute('INSERT INTO registry_brands(name,name_key) VALUES (?,?) ON CONFLICT(name_key) DO NOTHING',
                   (brand_name.strip(),normalized(brand_name)))
        brand_id = db.execute('SELECT id FROM registry_brands WHERE name_key=?', (normalized(brand_name),)).fetchone()[0]
        if db.execute('SELECT id FROM registry_branches WHERE brand_id=? AND name_key=?',
                      (brand_id,normalized(details['name']))).fetchone():
            raise ValueError('That branch name already exists for this brand. Link to the existing branch, or use a distinct location name.')
        address = normalized(details.get('address') or '')
        if address:
            for row in db.execute('SELECT details_json FROM registry_branches WHERE brand_id=?', (brand_id,)):
                if normalized(json.loads(row[0]).get('address') or '') == address:
                    raise ValueError('This brand already has a branch with the same address. Link to it instead.')
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(details, ensure_ascii=False)
        cursor = db.execute('''INSERT INTO registry_branches
            (brand_id,name,name_key,details_json,revision,updated_at_utc) VALUES (?,?,?,?,1,?)''',
            (brand_id,details['name'].strip(),normalized(details['name']),payload,now))
        branch_id = cursor.lastrowid
        add_link(db,branch_id,candidate)
        db.execute('INSERT INTO registry_revisions(branch_id,revision,details_json,saved_at_utc) VALUES (?,1,?,?)',
                   (branch_id,payload,now))
        return branch_id


def link_existing(path, branch_id, candidate):
    with connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute('SELECT id FROM registry_branches WHERE id=?', (branch_id,)).fetchone():
            raise ValueError('Branch does not exist.')
        existing = check_candidate(db,candidate)
        if existing:
            if existing[0] == branch_id:
                return False
            raise ValueError('Observation already belongs to another branch. It was not reassigned.')
        add_link(db,branch_id,candidate)
        return True


def update_branch(path, branch_id, expected_revision, details):
    validate(details)
    with connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM registry_branches WHERE id=?', (branch_id,)).fetchone()
        if row is None or row['revision'] != expected_revision:
            raise ValueError('This branch changed in another session. Refresh before editing.')
        address = normalized(details.get('address') or '')
        if address:
            for other in db.execute('SELECT details_json FROM registry_branches WHERE brand_id=? AND id<>?', (row['brand_id'],branch_id)):
                if normalized(json.loads(other[0]).get('address') or '') == address:
                    raise ValueError('Another branch of this brand has the same address. Resolve that match before saving.')
        payload = json.dumps(details,ensure_ascii=False)
        now = datetime.now(timezone.utc).isoformat()
        revision = expected_revision + 1
        db.execute('''UPDATE registry_branches SET name=?,name_key=?,details_json=?,revision=?,updated_at_utc=? WHERE id=?''',
                   (details['name'].strip(),normalized(details['name']),payload,revision,now,branch_id))
        db.execute('INSERT INTO registry_revisions(branch_id,revision,details_json,saved_at_utc) VALUES (?,?,?,?)',
                   (branch_id,revision,payload,now))
