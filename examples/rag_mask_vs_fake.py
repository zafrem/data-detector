"""
Comparison of MASK vs FAKE redaction strategies for RAG systems.

This example demonstrates the difference between:
- MASK: Replace PII with asterisks (e.g., "***@***.com")
- FAKE: Replace PII with realistic fake data (e.g., "fake123@example.com")

For RAG systems, FAKE strategy is often better because:
1. Preserves semantic structure for embeddings
2. More natural for LLM processing
3. Maintains text flow and readability

Run with:
    python examples/rag_mask_vs_fake.py
"""

import asyncio

from datadetector import Engine, load_registry
from datadetector.models import RedactionStrategy
from datadetector.rag_middleware import RAGSecurityMiddleware
from datadetector.rag_models import SecurityLayer, SecurityPolicy


async def main():
    # Initialize
    print("Loading patterns...")
    registry = load_registry()
    engine = Engine(registry)

    print("\n" + "=" * 70)
    print("MASK vs FAKE STRATEGY COMPARISON")
    print("=" * 70)

    # Test document
    document = """
    Customer Support Request

    Name: John Doe
    Email: john.doe@company.com
    Phone: 555-123-4567
    SSN: 123-45-6789

    Issue: Customer reported problems with their account.
    Please contact them at the email above or call 555-123-4567.
    """

    print("\nOriginal Document:")
    print("-" * 70)
    print(document)

    # ============================================================
    # Strategy 1: MASK (Traditional)
    # ============================================================
    print("\n[STRATEGY 1] MASK - Replace with asterisks")
    print("-" * 70)

    result_mask = engine.redact(
        document,
        namespaces=["comm", "us"],
        strategy=RedactionStrategy.MASK,
    )

    print("Redacted with MASK:")
    print(result_mask.redacted_text)
    print(f"\nPII removed: {result_mask.redaction_count} items")

    # ============================================================
    # Strategy 2: FAKE (Realistic Replacement)
    # ============================================================
    print("\n[STRATEGY 2] FAKE - Replace with realistic fake data")
    print("-" * 70)

    result_fake = engine.redact(
        document,
        namespaces=["comm", "us"],
        strategy=RedactionStrategy.FAKE,
    )

    print("Redacted with FAKE:")
    print(result_fake.redacted_text)
    print(f"\nPII removed: {result_fake.redaction_count} items")

    # ============================================================
    # Comparison: Embedding Quality
    # ============================================================
    print("\n" + "=" * 70)
    print("WHY FAKE IS BETTER FOR RAG SYSTEMS")
    print("=" * 70)

    print("\n1. SEMANTIC STRUCTURE")
    print("-" * 70)
    print("MASK:  'Email: ****@*******.***'")
    print("       → Loses email format, affects embeddings")
    print("\nFAKE:  'Email: fake123@example.com'")
    print("       → Preserves email format, better embeddings")

    print("\n2. NATURAL LANGUAGE PROCESSING")
    print("-" * 70)
    print("MASK:  'Call ************' (unnatural)")
    print("FAKE:  'Call 555-0123' (natural)")

    print("\n3. LLM UNDERSTANDING")
    print("-" * 70)
    print("MASK:  LLM may struggle with masked placeholders")
    print("FAKE:  LLM processes realistic text normally")

    # ============================================================
    # Using with RAG Middleware
    # ============================================================
    print("\n" + "=" * 70)
    print("USING WITH RAG MIDDLEWARE")
    print("=" * 70)

    # Policy with FAKE strategy
    fake_policy = SecurityPolicy(
        layer=SecurityLayer.STORAGE,
        redaction_strategy=RedactionStrategy.FAKE,
    )

    middleware = RAGSecurityMiddleware(
        engine,
        storage_policy=fake_policy,
    )

    result = await middleware.scan_document(document, namespaces=["comm", "us"])

    print("\nDocument ready for vector DB:")
    print("-" * 70)
    print(result.sanitized_text)

    # ============================================================
    # Load from YAML Configuration
    # ============================================================
    print("\n" + "=" * 70)
    print("LOADING FROM YAML CONFIGURATION")
    print("=" * 70)

    print("\nEdit config/rag_security_policy.yml:")
    print("-" * 70)
    print(
        """
storage_layer:
  enabled: true
  action: sanitize
  redaction_strategy: fake  # Choose: mask | fake | tokenize | hash
    """
    )

    print("\nThen load and use:")
    print("-" * 70)
    print(
        """
from datadetector.rag_config import load_rag_policy

# Load from YAML
policy_config = load_rag_policy()

# Get policies for each layer
input_policy = policy_config.get_input_policy()
storage_policy = policy_config.get_storage_policy()
output_policy = policy_config.get_output_policy()

# Create middleware with loaded policies
middleware = RAGSecurityMiddleware(
    engine,
    input_policy=input_policy,
    storage_policy=storage_policy,
    output_policy=output_policy
)
    """
    )

    # ============================================================
    # Performance Comparison
    # ============================================================
    print("\n" + "=" * 70)
    print("PERFORMANCE COMPARISON")
    print("=" * 70)

    import time

    # Benchmark MASK
    start = time.perf_counter()
    for _ in range(100):
        engine.redact(document, strategy=RedactionStrategy.MASK)
    mask_time = (time.perf_counter() - start) * 1000 / 100

    # Benchmark FAKE
    start = time.perf_counter()
    for _ in range(100):
        engine.redact(document, strategy=RedactionStrategy.FAKE)
    fake_time = (time.perf_counter() - start) * 1000 / 100

    print(f"\nMASK: {mask_time:.2f}ms per document (faster)")
    print(f"FAKE: {fake_time:.2f}ms per document")
    print(f"\nDifference: {fake_time - mask_time:.2f}ms ({fake_time/mask_time:.1f}x)")

    print("\nRecommendation:")
    print("  • Use FAKE for storage layer (better embeddings)")
    print("  • Use MASK for output layer (faster, simpler)")
    print("  • Use TOKENIZE for reversible masking needs")

    # ============================================================
    # Example Use Cases
    # ============================================================
    print("\n" + "=" * 70)
    print("RECOMMENDED USE CASES")
    print("=" * 70)

    print(
        """
1. PUBLIC CHATBOT
   Input:   FAKE (preserve query structure)
   Storage: FAKE (better semantic search)
   Output:  MASK (fast blocking)

2. INTERNAL KNOWLEDGE BASE
   Input:   TOKENIZE (reversible if needed)
   Storage: FAKE (optimal embeddings)
   Output:  FAKE (natural responses)

3. CUSTOMER SUPPORT SYSTEM
   Input:   MASK (simple, fast)
   Storage: TOKENIZE (audit trail)
   Output:  MASK (strict blocking)

4. MAXIMUM SECURITY
   Input:   MASK
   Storage: TOKENIZE (reversible but secure)
   Output:  MASK
    """
    )

    print("\n" + "=" * 70)
    print("✓ Example Complete")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Edit config/rag_security_policy.yml")
    print("2. Choose mask or fake for each layer")
    print("3. Test with your RAG pipeline")


if __name__ == "__main__":
    asyncio.run(main())
