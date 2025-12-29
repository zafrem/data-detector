# Golang Regex Compatibility Guide

## Overview
This document outlines regex compatibility issues between Python's `re` module and Golang's `regexp` package, and provides solutions for the patterns in this project.

## Key Differences

### 1. **Lookahead and Lookbehind Assertions**

**Python**: Supports both lookahead and lookbehind
```python
(?<!\d)[0-9]{5}(?!\d)  # ✓ Supported
```

**Golang**: **NOT SUPPORTED**
```go
// ❌ ERROR: error parsing regexp: invalid or unsupported Perl syntax: `(?<!`
regexp.MustCompile(`(?<!\d)[0-9]{5}(?!\d)`)
```

#### Affected Patterns

| Pattern ID | Current Regex | Issue |
|------------|---------------|-------|
| `cn/zipcode_01` | `(?<!\d)[0-9]{6}(?!\d)` | Lookbehind/lookahead |
| `kr/landline_03` | `(?<!\d)(02\|...)(?!\d)` | Lookbehind/lookahead |
| `us/zipcode_01` | `(?<![A-Za-z0-9])[0-9]{5}...` | Lookbehind/lookahead |
| `kr/business_registration_01` | `(?<!\d)[0-9]{3}-[0-9]{2}...` | Lookbehind/lookahead |
| `kr/driver_license_01` | `(?<!\d)[0-9]{2}-[0-9]{6}...` | Lookbehind/lookahead |
| `kr/zipcode_01` | `(?<![A-Za-z0-9])[0-9]{5}...` | Lookbehind/lookahead |
| `jp/bank_account_01` | `(?<!\d)[0-9]{7}(?!\d)` | Lookbehind/lookahead |
| `jp/my_number_01` | `(?<!\d)[0-9]{4}-?...` | Lookbehind/lookahead |
| `jp/driver_license_01` | `(?<!\d)[0-9]{4}-?...` | Lookbehind/lookahead |
| `jp/zipcode_01` | `(?<!\d)[0-9]{3}-?[0-9]{4}(?!\d)` | Lookbehind/lookahead |
| `jp/generic_japanese_bank_account_01` | `(?<!\d)[0-9]{4}-?...` | Lookbehind/lookahead |
| `tw/passport_01` | `(?<!\d)[0-9]{9}(?!\d)` | Lookbehind/lookahead |
| `tw/business_id_01` | `(?<!\d)[0-9]{8}(?!\d)` | Lookbehind/lookahead |
| `tw/zipcode_01` | `(?<!\d)[0-9]{3}(?:[0-9]{2})?(?!\d)` | Lookbehind/lookahead |
| `tw/generic_taiwan_bank_account_01` | `(?<!\d)[0-9]{3}-?...` | Lookbehind/lookahead |

### 2. **Named Groups**

**Python**: `(?P<name>...)` or `(?<name>...)`
**Golang**: `(?P<name>...)` only

✓ **Compatible** - Our patterns don't use named groups extensively, and when they do, we can standardize on `(?P<...>)`

### 3. **Unicode Properties**

**Python (re module)**: Limited support, requires `\u` ranges
**Python (regex module)**: `\p{Han}`, `\p{Script=Han}`
**Golang**: `\p{Han}` (without `Script=`)

✓ **Compatible** - We use `\u` ranges like `[\u4e00-\u9fff]`

## Solutions

### Solution 1: Word Boundaries (Best for most cases)

Replace lookahead/lookbehind with `\b` where appropriate:

**Before (Python only)**:
```regex
(?<!\d)[0-9]{5}(?!\d)
```

**After (Golang compatible)**:
```regex
\b[0-9]{5}\b
```

**Limitations**: `\b` matches between alphanumeric and non-alphanumeric, which may not work for all cases (e.g., "ABC12345" would match "12345").

### Solution 2: Verification Functions

Use simpler regex + verification function:

**Golang**:
```go
// Simpler regex
pattern := regexp.MustCompile(`[0-9]{5}`)

// Verification function
func isValidZipcode(match string, fullText string, start, end int) bool {
    // Check if preceded/followed by digit
    if start > 0 && unicode.IsDigit(rune(fullText[start-1])) {
        return false
    }
    if end < len(fullText) && unicode.IsDigit(rune(fullText[end])) {
        return false
    }
    return true
}
```

### Solution 3: Dual Patterns

Maintain two pattern sets:

```
patterns/
├── python/     # Python-optimized patterns (with lookahead/lookbehind)
└── golang/     # Golang-compatible patterns (without lookahead/lookbehind)
```

## Recommended Approach

For this project, we recommend **Solution 2: Verification Functions**:

1. **Keep existing patterns** for Python (optimal performance)
2. **For Golang ports**, use:
   - Simpler regex without lookahead/lookbehind
   - Verification functions to check context
   - This aligns with existing architecture (`verification` field in patterns)

## Pattern Conversion Reference

### Example 1: Zipcode

**Python (Current)**:
```yaml
pattern: '(?<![A-Za-z0-9])[0-9]{5}(?![A-Za-z0-9])'
```

**Golang-Compatible**:
```yaml
pattern: '[0-9]{5}'
verification: zipcode_not_embedded  # Custom verification function
```

**Golang Implementation**:
```go
func zipcodeNotEmbedded(match string, fullText string, start, end int) bool {
    // Check left boundary
    if start > 0 {
        prev := rune(fullText[start-1])
        if unicode.IsLetter(prev) || unicode.IsDigit(prev) {
            return false
        }
    }
    // Check right boundary
    if end < len(fullText) {
        next := rune(fullText[end])
        if unicode.IsLetter(next) || unicode.IsDigit(next) {
            return false
        }
    }
    return true
}
```

### Example 2: Bank Account

**Python (Current)**:
```yaml
pattern: '(?<!\d)[0-9]{3}-?[0-9]{6}-?[0-9]{4,5}(?!\d)'
```

**Golang-Compatible**:
```yaml
pattern: '[0-9]{3}-?[0-9]{6}-?[0-9]{4,5}'
verification: bank_account_boundaries
```

## Testing Golang Compatibility

To test patterns in Golang:

```go
package main

import (
    "fmt"
    "regexp"
)

func main() {
    // Test pattern compilation
    patterns := []string{
        `\b[0-9]{5}\b`,                    // ✓ Works
        `[6-9][0-9]{9}`,                   // ✓ Works
        `(?<!\d)[0-9]{5}(?!\d)`,           // ❌ Fails
    }

    for _, p := range patterns {
        _, err := regexp.Compile(p)
        if err != nil {
            fmt.Printf("❌ Pattern failed: %s\n   Error: %v\n", p, err)
        } else {
            fmt.Printf("✓ Pattern OK: %s\n", p)
        }
    }
}
```

## Summary

| Feature | Python `re` | Python `regex` | Golang `regexp` | Solution |
|---------|-------------|----------------|-----------------|----------|
| `(?<=...)` | ✓ | ✓ | ❌ | Verification function |
| `(?<!...)` | ✓ | ✓ | ❌ | Verification function |
| `(?=...)` | ✓ | ✓ | ❌ | Usually not needed |
| `(?!...)` | ✓ | ✓ | ❌ | Verification function |
| `\b` | ✓ | ✓ | ✓ | Use where possible |
| `\p{Han}` | ❌ | ✓ | ✓ | Use `[\u4e00-\u9fff]` |
| `(?P<name>...)` | ✓ | ✓ | ✓ | Compatible |

## Conversion Priority

**High Priority** (Most used):
- [ ] Zipcode patterns (US, KR, CN, JP, TW, IN)
- [ ] Bank account patterns with lookahead/lookbehind
- [ ] Generic number patterns

**Medium Priority**:
- [ ] ID numbers (Aadhaar, PAN, etc.)
- [ ] Driver license patterns

**Low Priority** (Less affected):
- [ ] Phone numbers (mostly use simple patterns)
- [ ] Email, IP addresses (no lookahead/lookbehind)

## References

- [Go regexp syntax](https://pkg.go.dev/regexp/syntax)
- [Python re module](https://docs.python.org/3/library/re.html)
- [Python regex module](https://pypi.org/project/regex/)
