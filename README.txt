WEBPAGE CHANGE DETECTION

Copy the three Python files into C:\Users\arnab\fitness-agent.
Keep overview_app.py in that same folder; this module reuses its grouping logic.
No existing files are replaced. No new packages are required.

COMPARE ALREADY STORED CAPTURES
.venv313\Scripts\python.exe check_changes.py
The command does not fetch websites or call Ollama. It reads the database and
saves a timestamped comparison report under data\changes.

VIEW COMPARISONS
Stop the current Streamlit server with Ctrl+C, then run:
.venv313\Scripts\python.exe -m streamlit run changes_app.py
Open the printed URL. The page computes current comparisons directly from SQLite.
Use Save this comparison report if you want to preserve a report from the UI.

CHECK A FRESH COLLECTION
.venv313\Scripts\python.exe run_batch.py
.venv313\Scripts\python.exe check_changes.py
Refresh the change-review page afterward.

RESULTS
baseline_only: one successful capture; no comparison available.
no_detected_change: normalized source text and selected extracted facts match.
source_changed_needs_review: captured webpage text changed. Verify business meaning.
extraction_variation_on_unchanged_text: model facts differ despite identical
normalized source text. This alone is not evidence of a business change.

Selected facts include brand, services, programmes, branch name/address, package
price/terms/currency/sessions and deals. List ordering, duplicate entries and
supporting excerpt wording are ignored. Renames or changed values appear as one
newly_extracted and one no_longer_extracted item; these are not confirmed openings,
closures, removals or price changes. Whitespace is normalized; case is preserved.

Original model extractions are compared, rather than manual review corrections.
The latest two successful captures of each webpage are compared, not every
intermediate transition. This is not comprehensive news/opening/closure extraction.
The source diff shows at most 160 lines; full sources remain in the overview.

Collection failures and import status from the latest batch report are shown
separately. A failed fetch is never proof of closure or an unchanged page.
A truncated input, rejected evidence or changed/missing model metadata is flagged.
Dynamic testimonials, navigation and other unrelated page text can trigger changes.

No capture, review, registry record, category or operating status is modified.
Review supporting evidence, then update the permanent branch register explicitly.
Reports do not yet have saved acknowledgement/resolution states or notifications.
Scheduling, unchanged-source extraction skipping and automated matching come later.

TESTED
Syntax checks and fixtures confirmed source vs extraction distinctions, latest-pair
grouping, baseline-only pages, ordering/duplicate normalization, text diffs,
collection-failure visibility and an unchanged database. UI still needs checking
on Windows with your actual captures.
