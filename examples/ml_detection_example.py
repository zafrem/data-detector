"""
ML-Enhanced PII Detection Example — Scoring Trace

Shows exactly how each match gets its final score through the pipeline:

  Initial score (regex match)      = 0.500
       |
  Step 3a: Keyword proximity       ±0.10 ~ +0.45
       |
  Step 3b-1: Binary classifier     +0.35*conf  or  -0.20
       |
  Step 3b-2: Category classifier   +0.15*conf  or  log mismatch
       |
  Final score (clamped 0.01–0.99)

Requirements:
  pip install data-detector[transformer]
"""

import sys
from copy import deepcopy
from pathlib import Path

from datadetector import Engine, ScoringConfig, TransformerConfig, load_registry
from datadetector.analysis import ContextAnalyzer
from datadetector.models import RedactionStrategy

SEP = "-" * 72


def check_prerequisites():
    """Check models and transformers are available."""
    model_base = Path(__file__).parent.parent / "pii-ml-engine" / "models" / "transformer"
    binary_ok = (model_base / "binary_classifier" / "model.safetensors").exists()
    cat_ok = (model_base / "category_classifier" / "model.safetensors").exists()

    if not binary_ok or not cat_ok:
        print("  Models not found in pii-ml-engine/models/transformer/")
        print("  Train first:  python -m datadetector.training.train_pii_classifier ...")
        sys.exit(1)

    try:
        import transformers  # noqa: F401
    except ImportError:
        print("  pip install data-detector[transformer]")
        sys.exit(1)


def build_engines():
    """Create regex-only and regex+ML engines."""
    registry = load_registry()
    engine_regex = Engine(registry)

    ml_config = TransformerConfig(enable_context_classifier=True)
    engine_ml = Engine(registry, transformer_config=ml_config)

    return engine_regex, engine_ml


def trace_scoring(engine_regex, engine_ml, text, namespaces=None):
    """
    Run the same text through regex-only and ML engines,
    then print a side-by-side scoring trace for each match.
    """
    kwargs = {"namespaces": namespaces} if namespaces else {}

    # Step 1+2: regex + verification only (no context analysis)
    result_regex = engine_regex.find(text, **kwargs)

    # Full pipeline: regex + verification + keyword + ML
    result_ml = engine_ml.find(text, **kwargs)

    # Build lookup from (start,end) -> ml match
    ml_map = {(m.start, m.end): m for m in result_ml.matches}

    print(f"\n  Input: \"{text}\"\n")
    print(f"  {'Matched':22s} {'Category':15s} {'Initial':>8s} {'Keyword':>8s} "
          f"{'Binary':>8s} {'Category':>10s} {'Final':>8s}")
    print(f"  {SEP}")

    for rm in result_regex.matches:
        matched = text[rm.start : rm.end]
        initial = rm.score  # 0.5 default

        mm = ml_map.get((rm.start, rm.end))
        if mm is None:
            # ML pipeline dropped or repositioned this match
            print(f"  {matched:22s} {rm.category.value:15s} {initial:8.3f} {'—':>8s} "
                  f"{'—':>8s} {'—':>10s} {'—':>8s}")
            continue

        # Parse evidence to extract individual contributions
        kw_boost = 0.0
        bin_delta = 0.0
        cat_delta = 0.0
        bin_detail = ""
        cat_detail = ""

        for ev in mm.context_evidence:
            if ev.startswith("ML-binary:pii"):
                # "ML-binary:pii (conf=0.999, boost=+0.350)"
                bin_delta = float(ev.split("boost=+")[1].rstrip(")"))
                bin_detail = f"+{bin_delta:.3f}"
            elif ev.startswith("ML-binary:non_pii"):
                # "ML-binary:non_pii (conf=0.999, penalty=-0.200)"
                bin_delta = -float(ev.split("penalty=-")[1].rstrip(")"))
                bin_detail = f"{bin_delta:.3f}"
            elif ev.startswith("ML-category:") and "boost" in ev:
                cat_delta = float(ev.split("boost=+")[1].rstrip(")"))
                cat_detail = f"+{cat_delta:.3f}"
            elif "ML-category-mismatch" in ev:
                cat_detail = "mismatch"
            elif not ev.startswith("ML-"):
                # Keyword evidence: "phone (dist: -4)"
                # Reconstruct keyword boost from score difference
                pass

        # Keyword contribution = final - initial - binary - category
        kw_boost = mm.score - initial - bin_delta - cat_delta
        # Clamp artifacts from min/max capping
        if mm.score >= 0.99:
            kw_boost = max(0.0, kw_boost)
        kw_str = f"+{kw_boost:.3f}" if kw_boost > 0 else ("" if kw_boost == 0 else f"{kw_boost:.3f}")

        if not bin_detail:
            bin_detail = ""
        if not cat_detail:
            cat_detail = ""

        print(f"  {matched:22s} {rm.category.value:15s} {initial:8.3f} {kw_str:>8s} "
              f"{bin_detail:>8s} {cat_detail:>10s} {mm.score:8.3f}")

    # Print raw evidence for full detail
    print(f"\n  Evidence detail:")
    for mm in result_ml.matches:
        matched = text[mm.start : mm.end]
        print(f"    {matched}: {mm.context_evidence}")


# ===========================================================================
# Example 1: Score trace for typical PII
# ===========================================================================
def example_1(engine_regex, engine_ml):
    print(f"\n{'=' * 72}")
    print("  Example 1: Typical PII — phone and email with keyword context")
    print(f"{'=' * 72}")

    trace_scoring(
        engine_regex, engine_ml,
        "Phone: 010-1234-5678, email: test@example.com",
        namespaces=["kr", "common"],
    )


# ===========================================================================
# Example 2: False positive suppression
# ===========================================================================
def example_2(engine_regex, engine_ml):
    print(f"\n{'=' * 72}")
    print("  Example 2: False positive — number in non-PII context")
    print(f"{'=' * 72}")

    trace_scoring(
        engine_regex, engine_ml,
        "Order number 123-45-6789 has been shipped via FedEx.",
    )


# ===========================================================================
# Example 3: Multiple PII types
# ===========================================================================
def example_3(engine_regex, engine_ml):
    print(f"\n{'=' * 72}")
    print("  Example 3: Multiple PII types in one sentence")
    print(f"{'=' * 72}")

    trace_scoring(
        engine_regex, engine_ml,
        "SSN: 123-45-6789, Credit Card: 4111-1111-1111-1111, IP: 192.168.1.1",
    )


# ===========================================================================
# Example 4: Category mismatch
# ===========================================================================
def example_4(engine_regex, engine_ml):
    print(f"\n{'=' * 72}")
    print("  Example 4: Category agreement vs mismatch")
    print(f"{'=' * 72}")

    # Regex matches as one category, ML may predict differently
    trace_scoring(
        engine_regex, engine_ml,
        "Reference code 4111111111111111 and phone 010-9999-8888",
        namespaces=["kr", "common"],
    )


# ===========================================================================
# Example 5: Keyword distance effect
# ===========================================================================
def example_5(engine_regex, engine_ml):
    print(f"\n{'=' * 72}")
    print("  Example 5: Keyword distance affects boost size")
    print(f"  (closer keyword = higher boost)")
    print(f"{'=' * 72}")

    # Close keyword (dist < 10)
    trace_scoring(
        engine_regex, engine_ml,
        "SSN:123-45-6789",
    )

    # Far keyword (dist > 30)
    trace_scoring(
        engine_regex, engine_ml,
        "Please enter the following identification number carefully: 123-45-6789",
    )


# ===========================================================================
# Example 6: Redaction uses final score
# ===========================================================================
def example_6(engine_regex, engine_ml):
    print(f"\n{'=' * 72}")
    print("  Example 6: Redaction result (all matches are redacted)")
    print(f"{'=' * 72}")

    text = "Customer phone: 010-1234-5678, email: user@corp.com"

    result = engine_ml.redact(text, namespaces=["kr", "common"], strategy=RedactionStrategy.MASK)
    print(f"\n  Original: {text}")
    print(f"  Redacted: {result.redacted_text}")
    print(f"  Count:    {result.redaction_count}")

    # Show what a score-based filter would keep
    find_result = engine_ml.find(text, namespaces=["kr", "common"])
    print(f"\n  Score-based filtering example:")
    for threshold in [0.3, 0.5, 0.7, 0.9]:
        kept = [text[m.start:m.end] for m in find_result.matches if m.score >= threshold]
        print(f"    score >= {threshold}: {kept}")


# ===========================================================================
# Example 7: Config tuning comparison
# ===========================================================================
def example_7(engine_regex, engine_ml):
    print(f"\n{'=' * 72}")
    print("  Example 7: Effect of TransformerConfig tuning")
    print(f"{'=' * 72}")

    registry = load_registry()
    text = "ID: 123-45-6789"

    configs = {
        "Default   (boost=0.35, penalty=0.20, threshold=0.5)": TransformerConfig(
            enable_context_classifier=True,
        ),
        "Strict    (boost=0.20, penalty=0.35, threshold=0.8)": TransformerConfig(
            enable_context_classifier=True,
            context_max_boost=0.20,
            context_penalty=0.35,
            context_confidence_threshold=0.8,
        ),
        "Permissive(boost=0.45, penalty=0.10, threshold=0.3)": TransformerConfig(
            enable_context_classifier=True,
            context_max_boost=0.45,
            context_penalty=0.10,
            context_confidence_threshold=0.3,
        ),
    }

    print(f"\n  Input: \"{text}\"\n")
    for label, cfg in configs.items():
        eng = Engine(registry, transformer_config=cfg)
        result = eng.find(text)
        scores = [(text[m.start:m.end], m.category.value, m.score) for m in result.matches]
        print(f"  {label}")
        for matched, cat, score in scores:
            print(f"    {matched:22s} {cat:15s} score={score:.3f}")
        print()


# ===========================================================================
# Example 8: ScoringConfig — centralized weight tuning
# ===========================================================================
def example_8(engine_regex, engine_ml):
    print(f"\n{'=' * 72}")
    print("  Example 8: ScoringConfig — centralized weight tuning")
    print(f"{'=' * 72}")

    registry = load_registry()
    text = "전화번호: 01098765432"

    configs = {
        "Default": ScoringConfig(),
        "High-precision (min_score=0.7, low keyword boost)": ScoringConfig(
            min_score=0.7,
            keyword_pre_close_boost=0.20,
            keyword_pre_far_boost=0.10,
            keyword_pre_weak_boost=0.05,
        ),
        "Verified-only (initial_unverified=0.2, min_score=0.5)": ScoringConfig(
            initial_unverified=0.20,
            min_score=0.5,
        ),
    }

    print(f"\n  Input: \"{text}\"\n")
    for label, sc in configs.items():
        eng = Engine(registry, scoring_config=sc)
        result = eng.find(text, namespaces=["kr"])
        print(f"  {label}")
        if result.matches:
            for m in result.matches:
                matched = text[m.start:m.end]
                print(f"    {matched:22s} verified={m.verified}  score={m.score:.3f}")
        else:
            print("    (all matches filtered out)")
        print()

    # min_score filtering demo
    print("  --- min_score filtering ---")
    text2 = "some data 01098765432 and more 12345"
    for min_s in [0.0, 0.5, 0.8, 0.95]:
        sc = ScoringConfig(min_score=min_s)
        eng = Engine(registry, scoring_config=sc)
        r = eng.find(text2, namespaces=["kr"])
        labels = [f"{text2[m.start:m.end]}(v={m.verified},s={m.score:.2f})" for m in r.matches]
        print(f"    min_score={min_s}: {len(r.matches)} matches  {labels}")


# ===========================================================================
# Main
# ===========================================================================
def main():
    print("\n  Data Detector — ML Scoring Trace Example")
    print(f"  {SEP}")
    print("  Pipeline:  Regex(0.5) -> Keyword(±boost) -> Binary(±) -> Category(±) -> Final")
    print(f"  {SEP}")

    check_prerequisites()
    engine_regex, engine_ml = build_engines()

    example_1(engine_regex, engine_ml)
    example_2(engine_regex, engine_ml)
    example_3(engine_regex, engine_ml)
    example_4(engine_regex, engine_ml)
    example_5(engine_regex, engine_ml)
    example_6(engine_regex, engine_ml)
    example_7(engine_regex, engine_ml)
    example_8(engine_regex, engine_ml)

    print(f"\n{'=' * 72}")
    print("  Scoring Reference")
    print(f"{'=' * 72}")
    print("""
  Step           | Source                  | Default  | ScoringConfig field
  ---------------|-------------------------|----------|-----------------------------
  Initial(verif) | Regex + verification    | = 0.950  | initial_verified
  Initial(unreif)| Regex only              | = 0.500  | initial_unverified
  Keyword(<10ch) | Anchor keyword nearby   | + 0.450  | keyword_pre_close_boost
  Keyword(<30ch) | Anchor keyword mid-dist | + 0.300  | keyword_pre_far_boost
  Keyword(<60ch) | Anchor keyword far      | + 0.100  | keyword_pre_weak_boost
  Binary(pii)    | ML conf * max_boost     | + 0.350  | TransformerConfig.context_max_boost
  Binary(non_pii)| ML penalty              | - 0.200  | TransformerConfig.context_penalty
  Category(match)| ML conf * boost         | + 0.150  | ml_category_boost
  Category(miss) | Log only                |   0.000  | (no score change)
  NER corroborate| Regex+NER agree         | + 0.150  | ner_corroboration_boost
  ---------------|-------------------------|----------|-----------------------------
  min_score      | Post-pipeline filter    |   0.000  | min_score
  placeholders   | Filter test data        |   True   | filter_placeholders
  Final          | Clamped                 | [0.01, 0.99]
""")


if __name__ == "__main__":
    main()
