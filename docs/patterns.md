# Pattern Structure

## Pattern File Format

Patterns are defined in YAML files with the following structure:

```yaml
namespace: kr
description: Korean (South Korea) PII patterns

patterns:
  - id: mobile_01              # Required: Pattern ID with 2-digit suffix
    location: kr               # Required: Location identifier (kr, us, comm, etc.)
    category: phone            # Required: PII category
    description: Korean mobile phone number (010/011/016/017/018/019)
    pattern: '01[016-9]-?\d{3,4}-?\d{4}'  # Required: Regex pattern
    flags: [IGNORECASE]        # Optional: Regex flags
    mask: "***-****-****"      # Optional: Default mask template
    verification: iban_mod97   # Optional: Verification function name
    examples:                  # Optional but recommended
      match: ["010-1234-5678", "01012345678"]
      nomatch: ["012-999-9999"]
    policy:                    # Optional: Privacy and action policies
      store_raw: false
      action_on_match: redact
      severity: high
    metadata:                  # Optional: Additional metadata
      note: "Additional information"
```

## Required Fields

- **`id`**: Unique identifier with 2-digit suffix (e.g., `mobile_01`, `ssn_02`)
- **`location`**: Location/region code (2-4 lowercase letters: `kr`, `us`, `comm`, `intl`)
- **`category`**: PII category from: `phone`, `ssn`, `rrn`, `email`, `bank`, `passport`, `address`, `credit_card`, `ip`, `iban`, `name`, `other`
- **`pattern`**: Regular expression pattern for matching

## Optional Fields

### Flags
Regex flags to apply:
- `IGNORECASE` - Case-insensitive matching
- `MULTILINE` - `^` and `$` match line boundaries
- `DOTALL` - `.` matches newlines
- `UNICODE` - Unicode matching
- `VERBOSE` - Allow comments in regex

### Mask
Default mask template for redaction (e.g., `"***-****-****"`)

### Verification
Name of verification function to apply after regex matching. See [Verification Functions](verification.md) for details.

Built-in verification functions:
- `iban_mod97` - IBAN Mod-97 checksum
- `luhn` - Luhn algorithm (credit cards, etc.)

### Examples
Test cases for pattern validation:
- `match` - Examples that should match the pattern
- `nomatch` - Examples that should NOT match

### Policy
Privacy and action configuration:
- `store_raw` (boolean) - Whether raw matched text can be stored
- `action_on_match` (string) - Action: `redact`, `report`, `tokenize`, `ignore`
- `severity` (string) - Severity level: `low`, `medium`, `high`, `critical`

### Metadata
Arbitrary additional data as key-value pairs.

## Location Codes

The `location` field identifies the geographic or categorical scope:

- **`co`** - Common/International patterns
- **`kr`** - South Korea
- **`us`** - United States
- **`tw`** - Taiwan (Republic of China)
- **`jp`** - Japan
- **`cn`** - China (People's Republic of China)
- **`in`** - India
- **`eu`** - European Union (future)
- **`intl`** - International (multi-region)

**Note**: Pattern files can have any name. The system uses the `location` field to organize patterns.

## Pattern Naming Best Practices

- **ID Format**: `{name}_{NN}` where NN is a 2-digit number (e.g., `mobile_01`, `mobile_02`)
- **Location Codes**: Use 2-4 lowercase letters (e.g., `kr`, `us`, `comm`, `myorg`)
- **Versioning**: Increment the number suffix for pattern variations (e.g., `ssn_01`, `ssn_02`)
