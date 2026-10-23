FOUR-CATEGORY UPDATE

New categories: strength, mobility, recovery, longevity clinics.
Mappings: gym -> strength; yoga/stretching -> mobility;
longevity -> longevity clinics; recovery -> recovery.

INSTALL AND MIGRATE
1. Stop all Streamlit apps, collection runs and source registration commands.
2. Copy the five Python files in this ZIP into C:\Users\arnab\fitness-agent.
   Replace settings.py, registry_store.py and review_app.py.
   The uploaded review_app(1).py is delivered here as review_app.py.
   Add categories.py and migrate_categories.py.
   Keep registry_app.py, overview_app.py and every other project file.
3. Run:
   .venv313\Scripts\python.exe migrate_categories.py
4. After successful migration, check:
   .venv313\Scripts\python.exe run_batch.py --dry-run
5. Restart your register:
   .venv313\Scripts\python.exe -m streamlit run registry_app.py

Migration edits your actual local sources.json rather than replacing it with a
stale copy. Your brand names, source IDs, URLs, enabled flags and page types remain.
It automatically saves database and source-register backups in data\backups.
Current permanent branch categories are relabelled with new revision records.
Original captures, observation links, old review rows and old revision rows remain
unchanged. No operating-status or evidence claims are added by relabelling.

Old branch categories displayed in review_app.py are translated on load. Saving a
review creates a new review version. Sports/recreation and unknown historical
branch labels are retained under legacy_categories; they are outside the four
current categories. An unsupported source-register category stops migration before
writes so it can be resolved explicitly; your three supplied sources are supported.
Historical JSON may still show old names intentionally. Source-list categories are
organisational labels, not confirmed services for every branch.

The category rename does not implement service-level discount eligibility.
Existing partnership logic must later operate on the service being redeemed.

TESTED
Syntax checks, source mapping/validation, database backup, branch revision history,
preservation of captures/reviews, archived legacy categories, and idempotent reruns
were tested on a temporary database. Live Windows UI needs checking after install.
