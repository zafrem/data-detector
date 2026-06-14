# Data Detector: Architecture & Implementation Workbook

This workbook provides practical, hands-on guidance for working with the stabilized Data Detector workspace. Use this as a reference for understanding the unified architecture and implementing new features.

---

## 1. Workspace Layout Recap

The project is organized into four main modules, now with a clear dependency flow:

*   **`Data-detector`**: The core Python engine. Contains all PII detection logic, regex patterns (via submodule), and **shared resource adapters**.
*   **`Data-detector-collector`**: A lightweight Python module for raw data collection. It depends on `Data-detector` for its adapters but focuses on sending raw samples to the classifier.
*   **`Data-detector-classifier-helper`**: A Go service that orchestrates scans. It takes raw data from the Collector, runs it through the Detector API, and saves results.
*   **`Data-detector-platform`**: The web UI and main backend for user interaction.

---

## 2. Working with Adapters

We have consolidated all resource adapters (Database, Kafka, API, etc.) into `Data-detector`. 

### How to use a shared adapter:
```python
from datadetector.adapters.database import DatabaseAdapter
from datadetector.resource_models import DataResource, ResourceType, ConnectionConfig

# Define the resource
resource = DataResource(
    name="my_db",
    resource_type=ResourceType.DATABASE,
    connection=ConnectionConfig(uri="sqlite:///data.db")
)

# Use the adapter
with DatabaseAdapter(resource) as adapter:
    containers = adapter.list_containers()
    fields = adapter.list_fields(containers[0].name)
    samples = adapter.sample_values(containers[0].name, fields[0].name, limit=10)
```

---

## 3. Managing Patterns (`pii-pattern-engine`)

The pattern engine is a Git submodule located in `Data-detector/pii-pattern-engine` and `Data-detector-classifier-helper/pii-pattern-engine`.

### Essential Commands:

*   **Initialize everything**: 
    `git submodule update --init --recursive`
*   **Update patterns**: 
    `git submodule update --remote pii-pattern-engine`
*   **Sync for Vercel**: 
    `bash scripts/sync-patterns.sh` (This copies patterns to the `api/` directory for serverless deployment).

---

## 4. Reporting & Inventory

You can generate comprehensive PII inventory reports using the CLI. This involves two stages: scanning a resource and then generating a report from the results.

### Stage 1: Scan a Resource
```bash
# Scan a database and save the raw result
data-detector resource scan --type database --uri "sqlite:///my_data.db" --name prod-db --out scan_prod.json

# Scan a file directory
data-detector resource scan --type file_storage --uri "/path/to/docs" --name docs-folder --out scan_docs.json
```

### Stage 2: Generate Inventory Report
```bash
# Generate a unified HTML report from multiple scan results
data-detector resource inventory --in scan_prod.json --in scan_docs.json --format html --out pii_inventory.html

# Export to CSV for spreadsheet analysis
data-detector resource inventory --in scan_prod.json --format csv --out inventory.csv
```

---

## 5. Development Workflow

### Adding a New PII Pattern:
1.  Navigate to `Data-detector/pii-pattern-engine/regex/pii/<country>/`.
2.  Add your YAML pattern definition.
3.  Add a test case in `Data-detector/pii-pattern-engine/tests/`.
4.  Run `sync-patterns.sh` in the root `Data-detector` directory to update the API's local copy.

### Adding a New Collector Output:
1.  Navigate to `Data-detector-collector/src/datadetector_collector/outputs/`.
2.  Create a new class inheriting from `OutputAdapter`.
3.  Implement the `send(result: CollectedResourceData)` method.

---

## 5. Verification Checklist

When making changes, ensure:
- [ ] All code in `Data-detector-collector` imports shared logic from `datadetector`.
- [ ] Symlinks in `Data-detector/src/` (like `verification`) are resolved.
- [ ] Submodule pointers are updated in both the Detector and the Classifier Helper.
- [ ] Any new Go code in the Helper or Platform is placed in the `backend/` directory for consistency.
