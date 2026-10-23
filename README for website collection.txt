FITNESS AGENT: BATCH COLLECTION

INSTALL
1. Stop Streamlit using Ctrl+C, if it is running in the terminal you need.
2. In C:\Users\arnab\fitness-agent, back up the current test_website.py:
   copy test_website.py test_website_before_batch.py
3. Copy all files from this package into that same project folder.
   Replace test_website.py. The included import_captures.py is unchanged.
   This package contains no database or captures. Keep your existing data folder.
   Keep app.py and review_app.py.
4. Use the existing .venv313 environment. No new packages are required.

FIRST CHECK
.venv313\Scripts\python.exe run_batch.py --dry-run
This validates settings and lists sources. It does not contact websites or Ollama.

ADD SOURCES
Extreme Fitness's homepage is already registered.
.venv313\Scripts\python.exe register_source.py
Enter a real brand name, its official webpage URL, then choose category/page type.
Repeat for your recovery centre and yoga studio. Add additional locations, pricing
or promotions pages individually when necessary. Duplicate URLs are rejected.
The source category organises collection; it does not verify branch categories.

COLLECT ALL ENABLED SOURCES
.venv313\Scripts\python.exe run_batch.py
Keep Ollama running. Pages run sequentially to limit memory usage.
A failed page is logged and later pages continue. Successful captures are imported.
Reports are stored in data\runs. Return code 1 indicates a failure or import issue.
Review captured_needs_review, input_truncated, errors, and import_output in the report.
Refresh review_app.py to see imported captures.

SINGLE PAGE
.venv313\Scripts\python.exe test_website.py
This still accepts one URL interactively; import it with import_captures.py afterward.

SETTINGS
config.json contains model name, context/output limits, timeouts and host.
sources.json contains URLs, registered source IDs and enabled flags.
To skip a page, change its enabled value to false.
Use one batch at a time. Do not edit sources.json while register_source.py runs.

FILES
collector.py: shared extraction and evidence checks, corrected null-address handling.
settings.py: configuration and source validation.
register_source.py: interactive source registration.
run_batch.py: collection, error reports and automatic import.
test_website.py: single-page interface using the shared collector.
import_captures.py: your unchanged importer.
config.json: model settings.
sources.json: source register, initially Extreme Fitness only.

LIMITS
No crawling, scheduling, change detection or unique-branch counts yet.
A news page can be registered, but the current schema does not extract news events.
Captures are observations, not confirmed venues, closure claims or eligible packages.
Old captures and reviews are preserved. Reviews remain linked to their own capture;
new captures do not automatically inherit past branch corrections.
Failed fetch/extraction attempts are logged but do not create successful captures.
Evidence checks cannot guarantee semantic accuracy or that a page is current.

VALIDATION PERFORMED
Python syntax and configuration validation passed.
Tests with simulated webpage/model responses confirmed: null-address handling,
address evidence rejection, unsupported SGD clearing, continuation after a page
failure, SQLite import compatibility and repeat-import duplicate protection.
Live collection and Ollama inference must still be tested on your Windows computer.
