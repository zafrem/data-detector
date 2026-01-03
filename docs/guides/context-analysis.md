# Contextual Analysis Guide

This guide explains the **Contextual Analysis** feature (Step 3 of the detection pipeline), which significantly improves detection accuracy by analyzing the text surrounding a potential match.

## Overview

The detection engine uses a 3-step pipeline:
1.  **Regex Matching**: Finds candidate strings (e.g., "98004").
2.  **Verification**: Validates the format (e.g., Checksums, Data lookup).
3.  **Context Analysis**: Scores the match based on surrounding "Anchor Keywords" (e.g., "WA", "Zip Code").

Step 3 is crucial for resolving ambiguity. For example, the number `98004` could be a Zip Code or a transaction ID. If it appears as `Bellevue, WA 98004`, Context Analysis boosts the confidence score because valid address anchors are nearby.

## Proximity Scoring

The system uses a **Proximity (Distance)** algorithm rather than simple keyword existence.

### Logic
1.  **Windowing**: Captures a window of text (default ±60 characters) around the candidate match.
2.  **Distance Calculation**: Measures the character distance between the match and the nearest anchor keyword.
3.  **Scoring**:
    *   **High Confidence**: Distance < 10 characters (e.g., `Zip: 90210`). Boost: **+0.45**.
    *   **Medium Confidence**: Distance < 30 characters (e.g., `123 Main St, 90210`). Boost: **+0.30**.
    *   **Low Confidence**: Distance < 60 characters. Boost: **+0.10**.

## Address Detection (US, KR, JP)

The system includes built-in support for address context in three major regions.

### United States (US)
*   **Category**: `address_us`
*   **Anchors**:
    *   **State Abbreviations**: `WA`, `CA`, `NY`, `TX`, etc.
    *   **Street Types**: `St`, `Ave`, `Blvd`, `Rd`, `Dr`, `Lane`, `Apt`, `Suite`.
    *   **Labels**: `Zip`, `Zip Code`, `State`, `Address`.

### South Korea (KR)
*   **Category**: `address_kr`
*   **Anchors**:
    *   **Administrative**: `도`, `시`, `군`, `구`, `읍`, `면`, `동`, `리`.
    *   **Road Names**: `로`, `길`, `번지`.
    *   **Labels**: `우편번호` (Postal Code), `주소` (Address), `배송지` (Shipping Address).
    *   **Cities**: `서울`, `경기`, `부산`, `대구`, etc.

### Japan (JP)
*   **Category**: `address_jp`
*   **Anchors**:
    *   **Symbols**: `〒` (Postal Symbol).
    *   **Administrative**: `都`, `道`, `府`, `県`, `市`, `区`, `町`, `村`.
    *   **Address Components**: `丁目`, `番地`, `号`.
    *   **Labels**: `郵便番号`, `住所`.

## Configuration

Context keywords are defined in YAML files located in `pattern-engine/keyword/`.

### Example: `address.yml`

```yaml
category: address
categories:
  address_us:
    description: US Address indicators
    patterns:
      - WA
      - CA
      - St
      - Ave
      - Zip Code
    contexts:
      - "Zip:"

  address_kr:
    description: Korean Address indicators
    patterns:
      - 서울
      - 경기
      - 우편번호
```

## Adding Custom Contexts

To add context for a new category (e.g., "medical"):

1.  Create `pattern-engine/keyword/medical.yml`.
2.  Define the category and anchor patterns:
    ```yaml
    category: medical
    categories:
      medical_ids:
        patterns:
          - patient
          - mrn
          - diagnosis
          - hospital
    ```
3.  The engine will automatically load this file and apply it to matches with `category: medical`.
