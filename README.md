# miami-housing-intelligence
Miami Housing Market Intelligence

An end-to-end data pipeline that ingests, stores, and analyzes 14 years of Miami-metro housing market data — combining Python, SQLite, a locally-run LLM, and n8n workflow automation to generate natural-language pricing insights on a schedule, visualized in an interactive Power BI dashboard.

Built for: Business Analyst roles at Miami-based companies (Lennar, Royal Caribbean, Carnival, and similar) where pricing intelligence and AI-driven automation are becoming core to the analyst function.

![Dashboard Screenshot](dashboard/dashboarddashboardscreenshot.png)


Why this project

Most student portfolios lean on generic practice datasets that don't reflect real analytical work. This project uses real, publicly available housing market data and is built around a question a Miami employer would actually care about: how is the local housing market moving, and can that analysis run itself?

It's also intentionally designed around a constraint many companies operate under: no paid API dependencies. The insight-generation layer runs entirely on a local LLM (Ollama + Llama 3.1 8B), demonstrating that AI-driven analytics doesn't require ongoing API spend — a real cost consideration for any BA team evaluating build-vs-buy on automation.

What it does
Fetches current housing market data for Miami-metro ZIP codes from Redfin's public Data Center
Loads it into a local SQLite database, preserving 14 years of historical trend data (2012–2026)
Generates natural-language market insights using a locally-run LLM — no external API calls, no per-request cost
Automates the entire fetch → load → insight pipeline on a weekly schedule using n8n
Visualizes the results in an interactive Power BI dashboard: KPI summary, AI-generated insights, and ZIP-code-level pricing trends
Architecture
miami-housing-intelligence/
├── data/
│   ├── raw/                    # Cached source file (gitignored)
│   └── processed/              # Filtered Miami-metro dataset
├── scripts/
│   ├── fetch_data.py           # Downloads + filters Redfin data to Miami metro
│   ├── load_db.py              # Loads processed data into SQLite
│   ├── generate_insights.py    # Local LLM generates pricing insights
│   └── export_dashboard_data.py # Prepares summary CSV for Power BI
├── db/
│   └── housing.db              # SQLite: zip_market_data + insights_log tables
├── n8n/
│   └── workflow.json           # Exported automation workflow
├── dashboard/
│   ├── miami_housing_summary.csv
│   └── miami_housing_dashboard.pbix
└── README.md

Stack: Python (pandas) · SQLite · Ollama (Llama 3.1 8B, local) · n8n · Power BI

Data source

Redfin Data Center — a public, official dataset published directly by Redfin, updated weekly. Data is downloaded directly from Redfin's public S3 bucket, with no scraping or Terms-of-Service violations involved.


Known limitation: Redfin does not publish months_of_supply at ZIP-code granularity (only at metro/county level), so this metric is excluded from the dashboard rather than backfilled with a misleading metro-level proxy repeated across ZIP codes.

Technical decisions worth highlighting

Local LLM over a paid API. The insight-generation layer originally targeted the Claude API. It was rearchitected to run on Ollama with Llama 3.1 8B running entirely on local hardware — zero API cost, zero external dependency, full data privacy. For a repeatable, scheduled automation (this pipeline is designed to run weekly, indefinitely), avoiding a per-run API cost is a real architectural consideration, not just a budget workaround.

Chunked, disk-first ingestion. The raw Redfin file is ~1.5GB compressed. An initial approach tried to stream-decompress it directly from the remote URL — pandas does not actually support true streaming reads of remote gzip files over HTTP, causing the process to hang indefinitely. The fix: download once to a local cache, then process in 200,000-row chunks with a restricted column set, avoiding ever loading the full decompressed file into memory.

A silent-failure bug in the automation layer. The insight-generation script worked correctly when run manually but failed silently when triggered from n8n. Root cause: the script used a relative path to the SQLite database, which resolved correctly only when run from the project's root directory — n8n's Execute Command node launches processes from a different working directory, causing SQLite to silently create a new, empty database at the wrong path rather than raising an error. Fixed by resolving all file paths absolutely relative to the script's own location, with explicit error handling added so future failures surface a clear message instead of a bare traceback.

Security-conscious automation. n8n's Execute Command node — which grants arbitrary shell command execution — is disabled by default as of n8n 2.0 due to the security risk it poses in multi-user environments. It was deliberately enabled here only because this instance runs locally, single-user, with no network exposure — the correct trade-off for this deployment context, not a default left unexamined.

Sample output

A real insight generated by the pipeline (Llama 3.1 8B, run against 91 Miami-metro ZIP codes):

"Luxury markets like Coral Gables and Coconut Grove have seen strong price appreciation, while more affordable neighborhoods like Hialeah and Opa-Locka have also seen moderate growth. A small number of zip codes, including 33255 and 33247, have seen relatively slow or even declining median sale prices over the past year, which could indicate market saturation or other underlying issues."

Note on local-model output: insights generated by an 8B-parameter local model are useful directional signals but are reviewed before being presented — smaller local models can produce minor reasoning inconsistencies (e.g., miscategorizing the size of a percentage change) that a larger hosted model would be less prone to. This is a known trade-off of the zero-API-cost architecture, and outputs are treated as a draft-quality first pass rather than a final analyst product.

Automation

The full pipeline (fetch → load → generate insights) is automated with n8n on a weekly schedule (Mondays, 8:00 AM). The exported workflow definition is included at n8n/workflow.json for reference. Since this runs on local infrastructure rather than a hosted server, the workflow is not live 24/7 — the exported JSON, along with the dashboard and insight history in insights_log, serve as evidence of the working automation.

Running it locally
bash
git clone https://github.com/anabelferreiro/miami-housing-intelligence.git
cd miami-housing-intelligence
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Install Ollama (ollama.com) and pull the model
ollama pull llama3.1:8b

python scripts/fetch_data.py
python scripts/load_db.py
python scripts/generate_insights.py
python scripts/export_dashboard_data.py

Open dashboard/miami_housing_dashboard.pbix in Power BI Desktop to view the interactive dashboard.

Author

Anabel Ferreiro — B.S. Business Analytics & Information Systems, University of South Florida Portfolio · LinkedIn