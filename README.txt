# Singapore Fitness Hub Research Agent

A Python prototype for collecting and organising information about Singapore’s fitness and wellness facilities, using a locally hosted large language model for structured information extraction.

The project supports research into a network of complementary facilities across four categories: **strength, mobility, recovery and longevity clinics**.

## Project purpose

Information about facilities, locations, services and memberships is spread across individual websites. This project brings that information into a consistent format while retaining source text and evidence for inspection.

The longer-term goal is to support ecosystem mapping, nearby facility discovery and potential partnerships between complementary service providers.

## Current features

- **Batch collection:** Collect information from a configurable list of webpages.
- **Local LLM extraction:** Use Ollama to extract structured information about services, programmes, branches, packages and deals.
- **Schema validation:** Validate model responses using Pydantic.
- **Evidence checks:** Check supporting excerpts against collected webpage text and flag unsupported items.
- **Historical storage:** Preserve timestamped captures in SQLite.
- **Manual review:** Correct extracted information through a Streamlit interface while retaining earlier reviews.
- **Latest-capture overview:** Group repeated captures by webpage and make historical records accessible.
- **Permanent branch register:** Maintain persistent records for physical locations and link repeated observations to existing branches.
- **Change detection:** Compare consecutive captures and distinguish changes in webpage text from changes in model output.

## Categories

| Category | Examples |
|---|---|
| Strength | Gyms, resistance training and strength coaching |
| Mobility | Yoga, stretching and mobility training |
| Recovery | Sauna, cold plunge and contrast therapy facilities |
| Longevity clinics | Clinics offering longevity-focused assessment and care |

A branch can belong to more than one category.

## How it works

1. Read enabled webpages from the source register.
2. Download HTML and extract readable text using BeautifulSoup.
3. Send a bounded amount of text to a local Ollama model.
4. Validate the structured response and check supporting evidence.
5. Save the extraction and collected text as timestamped captures.
6. Import captures into SQLite.
7. Inspect results through the overview, review and registry interfaces.
8. Compare successive captures to flag potential changes.

The system distinguishes between:

| Record | Purpose |
|---|---|
| Source | A webpage selected for collection |
| Capture | A timestamped observation of that webpage |
| Review | Corrections or assessments attached to a capture |
| Branch | A persistent record representing a physical location |

Repeated captures are retained as history and do not automatically create new branch records.

## Technology

- Python
- Ollama for local model inference
- Pydantic for structured-response validation
- BeautifulSoup for HTML text extraction
- SQLite for persistent storage
- Streamlit for local interfaces

The current model configuration uses `qwen3.5:4b`. The model name and extraction settings are managed through configuration.

## Main files

| File | Responsibility |
|---|---|
| `collector.py` | Webpage collection, model extraction, evidence checks and capture saving |
| `test_website.py` | Single-page collection |
| `run_batch.py` | Batch collection and automatic import |
| `import_captures.py` | Import saved captures into SQLite |
| `settings.py` | Configuration and source validation |
| `config.json` | Model settings, timeouts and text limits |
| `sources.json` | Registered webpages |
| `register_source.py` | Interactive source registration |
| `overview_app.py` | Latest captures and historical observations |
| `review_app.py` | Capture review and corrections |
| `registry_store.py` | Permanent brand and branch storage |
| `registry_app.py` | Branch registration and observation linking |
| `check_changes.py` | Generate change reports |
| `changes_app.py` | Display capture comparisons |

## Running locally

The commands below assume Windows CMD, a project folder named `fitness-agent`, and a Python virtual environment named `.venv313`.

### 1. Prepare Python

From the project folder:

```cmd
python -m venv .venv313
.venv313\Scripts\python.exe -m pip install --upgrade pip
.venv313\Scripts\python.exe -m pip install beautifulsoup4 requests httpx ollama pydantic streamlit pandas
```

This is an initial dependency list. Dependency versions are not yet pinned.

### 2. Prepare Ollama

Install Ollama and download the configured model:

```cmd
ollama pull qwen3.5:4b
```

Ensure Ollama is running before collecting pages.

### 3. Register a webpage

```cmd
.venv313\Scripts\python.exe register_source.py
```

Follow the prompts to enter the brand name, webpage URL, category and page type.

Additional pages can be registered for the same brand, such as locations, pricing or promotions pages.

### 4. Validate the setup

```cmd
.venv313\Scripts\python.exe run_batch.py --dry-run
```

The dry run validates configuration and lists enabled sources without collecting webpages or writing database records.

### 5. Collect registered pages

```cmd
.venv313\Scripts\python.exe run_batch.py
```

Pages are processed sequentially. Failed pages are recorded, and collection continues for the remaining sources. Successful captures are imported automatically.

### 6. Open the overview

```cmd
.venv313\Scripts\python.exe -m streamlit run overview_app.py
```

Open the local URL printed in the terminal.

Other interfaces can be launched similarly:

```cmd
.venv313\Scripts\python.exe -m streamlit run review_app.py
.venv313\Scripts\python.exe -m streamlit run registry_app.py
.venv313\Scripts\python.exe -m streamlit run changes_app.py
```

Run one interface at a time, or assign different ports when running several.

### 7. Compare captures

```cmd
.venv313\Scripts\python.exe check_changes.py
```

This compares stored captures. Run collection first when fresh observations are required.

## Data and evidence

Original captures, later reviews and permanent branch details are stored separately to retain the history of observations and corrections.

Evidence checks establish whether an excerpt occurs in the supplied text. They do not prove that the model interpreted it correctly.

For example:

- A weekly price must not be interpreted as a monthly price.
- A member benefit may have eligibility conditions.
- A missing branch in an extraction does not establish closure.
- A successful collection does not establish that a business is operating.

New branch records start with unknown operating status. Collection and change detection do not automatically update that status.

## Current limitations

- Collection visits registered URLs and does not yet discover new hubs automatically.
- The collector does not automatically follow links to additional pages.
- Content loaded through JavaScript, images or PDFs may be missed.
- The default model input is limited to the first 12,000 characters of extracted text.
- Model output can vary even when source text is unchanged.
- Service and programme classifications can require correction.
- Branch matching still involves manual confirmation.
- Dashboard counts describe the registered inventory, rather than a comprehensive count of Singapore facilities.
- Setup and execution have primarily been developed for a local Windows environment.

## Planned development

- Search-based discovery of additional brands and branches.
- Duplicate suggestions using names, addresses and postcodes.
- Discovery on six days of the week, with existing sources checked weekly.
- Explicit extraction of opening, relocation and closure announcements.
- Coordinates and proximity ranking between physical branches.
- Identification of complementary facilities within local clusters.
- More consistent representation of prices, billing periods and eligibility conditions.

These features are planned and are not part of the current discovery workflow.

## Repository contents

The repository contains source code and configuration without credentials.

Local environments, databases, collected webpage text, exports, logs and backups are excluded through `.gitignore`. API credentials should be supplied locally through environment variables or ignored configuration files.

## Project status

This is an early-stage, working prototype developed to explore LLM-assisted information extraction and fitness ecosystem research.

The focus is on traceable observations, persistent location records and a workflow that can expand as collection and discovery capabilities improve.
