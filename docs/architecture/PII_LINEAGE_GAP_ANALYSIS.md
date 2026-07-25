# PII Lineage — Gap Analysis

**Goal:** Detect and classify personal information, then connect it across systems
to build a **lineage of personal information** — a map of where each person's data
comes from, where it flows, and where it ends up.

This document explains, in plain terms, **what the project can already do** and
**what is still missing** to reach that goal. Each gap includes a concrete example
so it is easy to see why it matters.

---

## 1. The pipeline in one picture

Building PII lineage happens in four stages. We already have all four; the question
is how complete each one is.

```
  DETECT          CLASSIFY          INVENTORY            LINEAGE
  -------         ---------         -----------         ---------
  Find PII   -->  Label it    -->  Catalog every  -->  Connect the
  in values       (category,       PII field in a      fields into a
  and fields      severity,        single list         graph: who flows
                  confidence)                          into whom
```

| Stage | Where it lives | Maturity |
|-------|----------------|----------|
| Detect | `engine.py`, `regex/`, `nlp.py`, `transformer_ner.py` | **Strong** |
| Classify | `models.py` (`Category`, `Severity`, `PIIConfidence`) | **Good** |
| Inventory | `data_inventory.py` | **Good** |
| Lineage | `data_lineage.py` | **Early / incomplete** |

The first three stages are in good shape. **Almost all the missing work is in the
lineage stage**, and a few items are in classification.

---

## 2. What already works

- **Detection** — regex patterns for many countries, plus format verification
  (e.g. checksum validation), plus optional NLP and ML/transformer name detection.
- **Classification** — every detected field gets a `Category` (21 of them: email,
  phone, ssn, rrn, credit_card, address, …), a `Severity` (low→critical), a
  `PIIConfidence`, and a recommended `MaskingPolicy`.
- **Resource adapters** — six data sources can be scanned: database, Kafka, API,
  file storage, vector DB, training data. Each can list containers, list fields,
  sample values, and report relationships.
- **Inventory** — `DataInventoryGenerator` rolls all scan results into one catalog
  and exports it as JSON / CSV / YAML / HTML, with snapshot **diffing** and summary
  statistics.
- **Lineage (basic)** — `DataLineageTracer` builds a graph of fields, can trace
  upstream/downstream, find PII sources and sinks, and export to Mermaid / D3 / JSON.
  There is a CLI command (`resource lineage`).

So the **skeleton is real**. The gaps below are about making the lineage trustworthy,
complete, and actually about *people*.

---

## 3. The gaps (ordered by importance)

### Gap 1 — There is no concept of a *person* (data subject) ⭐ most important

**Today:** Lineage connects *fields*, written as `resource.container.field`
(for example `crm-db.users.email`).

**The problem:** "Personal information lineage" is ultimately about a **person**, not
a column. To say *"here is everything we hold about Jane Doe, and where it flows"* you
need a **subject identity** that ties records together across systems. Right now there
is nothing that says *these rows in three different databases are the same person*.

**Example of what you cannot answer today:**
> "A user requested deletion (GDPR erasure). Show me every place their data lives so
> we can delete it."

This is the single most valuable thing a PII lineage gives you, and it is not possible
yet because the graph has no subject key.

**What's needed:** a data-subject / identity layer so nodes and flows can be tied to
an individual (e.g. a subject key derived from a stable identifier).

---

### Gap 2 — Cross-system links are guessed, and have no direction

**Today:** When the same field is *not* explicitly linked, the tracer guesses a link
only when **two fields share the exact same name AND the same category**
(`_infer_cross_resource_links` in `data_lineage.py`).

**The problem — three issues:**

1. **Misses renames.** `users.email` and `contacts.email_address` are the same data,
   but different names, so no link is made.
2. **No direction.** Guessed links pick a direction essentially at random (whichever
   node the loop saw first). So "upstream vs downstream" is unreliable for anything
   that isn't a real database foreign key.
3. **No confidence.** A guessed link looks identical to a verified one.

**Example:**
> `signup-db.users.email` feeds `events-kafka.user_events.email`, which feeds
> `warehouse.fact_users.email_addr`. Because the warehouse renamed the column to
> `email_addr`, the chain breaks and the warehouse copy looks like an unrelated island.

**What's needed:** better matching (value overlap, not just name), **directional**
edges, and a confidence score on each edge.

---

### Gap 3 — No record of *how* data moved (no transformation/process)

**Today:** Edges are pure field-to-field links, mostly database foreign keys.

**The problem:** Real lineage captures the **process** that moved the data — the ETL
job, the SQL query, the pipeline step, the export. A foreign key describes *structure*,
not *flow*. Knowing two columns are joined is not the same as knowing a nightly job
copies one into the other.

**Example:**
> A daily job reads `orders.customer_email`, hashes it, and writes
> `analytics.user_hash`. Today there is no way to represent "this job did this
> transformation" — only that two columns might be related.

**What's needed:** a notion of **transform / job nodes** that sit between inputs and
outputs.

---

### Gap 4 — RAG and training-data provenance is not actually wired (your headline use cases)

**Today:** The relationship types `EMBEDDING_SOURCE` and `TRAINING_SOURCE` exist, but
the adapters use them incorrectly:
- `vector_db` links two **collections** that happen to share a `metadata.*` field.
- `training_data` links two **files** that share a schema.

Neither links a vector or a training row back to the **original document or dataset it
came from**.

**The problem:** The most valuable lineage edge for this project is exactly the one
that is missing:
> "This embedding in the vector store came **from this PII document**."
> "This personal data entered the fine-tuning set **from this database table**."

You already produce a **token map** (original value → token) during RAG sanitization.
That map is a perfect source of provenance and is currently not fed into the lineage
graph.

**What's needed:** emit real `source → embedding` and `source → training-row` edges,
reusing the token map as a provenance signal.

---

### Gap 5 — Nothing is stored, and there is no time dimension

**Today:** The graph is rebuilt **in memory** from inventory JSON files every run.

**The problem:**
- **No persistence / scale.** No graph store, no incremental updates. Re-scanning
  rebuilds everything from scratch.
- **No history.** The inventory can `diff` two snapshots, but the *graph* has no time
  axis. You cannot ask "*when* did PII start flowing into this sink?"

**Example:**
> "Last month this report had no personal data. Now it does. When and how did that
> change?" — answerable for the inventory, not for the lineage graph.

**What's needed:** a durable graph store and versioning/timestamps on nodes and edges.

---

### Gap 6 — Classification is missing fields that compliance lineage needs

**Today:** Each field has category, severity, confidence, and a masking suggestion.

**The problem — two missing ideas:**

1. **Special categories & quasi-identifiers.** There is `MEDICAL`, but no flag for
   GDPR "special categories" (biometric, ethnicity, religion, sexual orientation), and
   no concept of a **quasi-identifier** (zip + birth date + gender can re-identify a
   person *in combination*). Quasi-identifiers matter *specifically in lineage*,
   because the risk appears when several of them flow together into one place.
2. **Privacy metadata on each node.** No legal basis / purpose, retention period, or
   residency / jurisdiction. A personal-information lineage usually needs these to be
   useful for compliance.

**What's needed:** richer labels (special-category flag, quasi-identifier flag) and
per-node privacy attributes.

---

### Gap 7 — No quality/coverage metrics for the graph

**Today:** The graph is produced with no measure of how complete or trustworthy it is.

**The problem:** No detection of orphan nodes (PII with no known origin), no
"verified vs guessed" edge breakdown, no edge confidence. You cannot tell how much of
the picture is real versus inferred.

**What's needed:** coverage and confidence reporting on the finished graph.

---

## 4. Summary table

| # | Gap | Why it matters | Effort focus |
|---|-----|----------------|--------------|
| 1 | No data-subject identity | Can't answer "everything about person X" (DSAR/erasure) | New identity layer |
| 2 | Links guessed & directionless | Lineage is unreliable across systems | Matching + direction + confidence |
| 3 | No transformation/process | Can't show *how* data moved | Transform/job nodes |
| 4 | RAG/training provenance not wired | Your two main use cases lack their key edge | Source→embedding / source→training edges |
| 5 | No storage / no time | No history, no scale | Graph store + versioning |
| 6 | Classification too thin | Misses special categories & quasi-identifiers | Taxonomy + privacy metadata |
| 7 | No graph quality metrics | Can't trust the result | Coverage/confidence reporting |

---

## 5. Recommended order of work

1. **Data-subject identity layer** — unlocks the core value (find/delete everything
   about one person).
2. **Real RAG / training provenance edges** — directly serves the project's two
   headline use cases; reuse the existing token map.
3. **Directional, confidence-scored edges + transform nodes** — make the graph
   trustworthy and represent actual flow.
4. **Persistence + time/versioning.**
5. **Classification enrichment** — special categories, quasi-identifiers, and
   purpose / retention / residency metadata.

---

*Generated as a review of the current `datadetector` codebase
(`data_lineage.py`, `data_inventory.py`, `resource_models.py`, adapters, `models.py`).*
