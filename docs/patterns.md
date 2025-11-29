# Pattern Structure Guide

This document provides a detailed reference for the structure of the YAML files that define detection patterns. Understanding this structure is essential for creating new patterns or modifying existing ones.

## Pattern File Format

All patterns are defined in YAML files. Each file contains a `namespace` and a list of `patterns`.

```yaml
# The namespace is a unique identifier for this group of patterns.
namespace: kr
description: "PII patterns for South Korea"

# Each file contains a list of pattern definitions.
patterns:
  - id: mobile_01              # Required: A unique ID for the pattern.
    location: kr               # Required: The geographical or logical location of the pattern.
    category: phone            # Required: The category of PII this pattern represents.
    description: "Korean mobile phone number (010/011/016/017/018/019)" # A human-readable description.
    pattern: '01[016-9]-?\d{3,4}-?\d{4}'  # Required: The regular expression used for detection.
    flags: [IGNORECASE]        # Optional: Flags to modify the regex behavior.
    mask: "***-****-****"      # Optional: The template to use when masking this pattern.
    verification: iban_mod97   # Optional: A function to run for extra validation after a regex match.
    examples:                  # Optional but highly recommended for testing.
      match: ["010-1234-5678", "01012345678"]
      nomatch: ["012-999-9999"]
    policy:                    # Optional: Rules for handling matches of this pattern.
      store_raw: false
      action_on_match: redact
      severity: high
    metadata:                  # Optional: Any other key-value data you want to associate with the pattern.
      note: "This is a common format for mobile numbers in South Korea."
```

## Field Reference

### Core Fields

These fields are required for every pattern.

- **`id`** (string, required): A unique identifier for the pattern within its namespace. By convention, it should end with a two-digit suffix (e.g., `mobile_01`, `ssn_02`).
- **`location`** (string, required): The geographical or organizational code this pattern belongs to (e.g., `kr`, `us`, `comm`, `myorg`). This is used for filtering.
- **`category`** (string, required): The type of PII. This is used for grouping and reporting. Supported categories include: `phone`, `ssn`, `email`, `bank`, `credit_card`, `ip`, `iban`, `name`, and `other`.
- **`pattern`** (string, required): The regular expression used to find matches.

### Optional Fields

These fields allow for more advanced control over matching, redaction, and validation.

- **`description`** (string): A human-readable description of what the pattern detects.
- **`flags`** (list of strings): A list of flags to modify the behavior of the regular expression.
    - `IGNORECASE`: Makes the pattern case-insensitive.
    - `MULTILINE`: Allows `^` and `$` to match at the beginning and end of each line, not just the whole string.
    - `DOTALL`: Allows `.` to match any character, including newlines.
    - `UNICODE`: Enables Unicode-aware matching.
    - `VERBOSE`: Allows you to write more readable regexes with comments and whitespace.
- **`mask`** (string): A template to use for the `mask` redaction strategy. If not provided, a default mask will be used.
- **`verification`** (string): The name of a registered verification function to run after a regex match. This is for logic that can't be expressed in a regex, like a checksum. See the [Verification Functions](verification.md) guide for more details.
- **`examples`** (object): A set of test cases used to validate the pattern. Providing examples is highly recommended.
    - `match`: A list of strings that **should** match the pattern.
    - `nomatch`: A list of strings that **should not** match the pattern.
- **`policy`** (object): Defines the security policy for handling matches.
    - `store_raw` (boolean, default: `false`): If `true`, allows the raw matched text to be stored or logged. For security, this should usually be `false`.
    - `action_on_match` (string, default: `redact`): The default action to take. Options are `redact` (mask it), `report` (just report it), `tokenize` (replace with a token), or `ignore`.
    - `severity` (string, default: `medium`): The severity level of a match, used for reporting and prioritization. Options are `low`, `medium`, `high`, and `critical`.
- **`metadata`** (object): A place to store any other key-value data you want to associate with the pattern.

## Location Codes

The `location` field is used to group patterns by country or organization. This allows you to search for PII only in relevant regions, which improves performance and accuracy.

- **`comm`**: Common patterns that are international (e.g., `email`, `ip_address`).
- **`kr`**: South Korea
- **`us`**: United States
- **`jp`**: Japan
- **`cn`**: China
- And others. You can also define your own for custom patterns (e.g., `myorg`).

## Putting It All Together

When the `Engine` searches for PII, it first filters the patterns by the requested locations (e.g., `kr`, `us`). Then, for each piece of text, it applies the `pattern` (regex) of each filtered pattern. If a match is found, it runs the `verification` function (if any). If that also passes, a `Match` object is created. When it's time to redact, the `policy` and `mask` fields are used to determine how the matched text should be replaced.