"""
Quick start example for RAG security integration.

This example demonstrates the three-layer security approach:
1. Input Layer: Scan user queries
2. Storage Layer: Scan documents before indexing
3. Output Layer: Scan LLM responses

Run with:
    python examples/rag_quickstart.py
"""

import asyncio

from datadetector import Engine, load_registry
from datadetector.rag_middleware import RAGSecurityMiddleware
from datadetector.rag_models import SecurityAction, SecurityLayer, SecurityPolicy, SeverityLevel


async def main():
    # Initialize
    print("Loading patterns...")
    registry = load_registry()
    engine = Engine(registry)
    security = RAGSecurityMiddleware(engine)

    print("\n" + "=" * 70)
    print("RAG SECURITY - THREE-LAYER PROTECTION")
    print("=" * 70)

    # ============================================================
    # LAYER 1: INPUT SCANNING (User Queries)
    # ============================================================
    print("\n[LAYER 1] INPUT SCANNING - User Query")
    print("-" * 70)

    query = "What's the email address for customer john.doe@company.com?"
    print(f"Original query: {query}")

    result = await security.scan_query(
        query,
        namespaces=["comm"],  # Only scan for email, phone, etc.
    )

    print(f"PII detected: {result.has_pii}")
    print(f"Action taken: {result.action_taken.value}")
    print(f"Sanitized query: {result.sanitized_text}")
    print(f"Matches found: {result.match_count}")

    # ============================================================
    # LAYER 2: STORAGE SCANNING (Document Indexing)
    # ============================================================
    print("\n[LAYER 2] STORAGE SCANNING - Document Indexing")
    print("-" * 70)

    document = """
    Customer Information:
    Name: John Doe
    Email: john.doe@company.com
    Phone: 555-123-4567
    SSN: 123-45-6789

    Account Details:
    The customer requested support for their premium account.
    """

    print(f"Original document:\n{document}")

    # Use tokenization for reversible PII masking
    result = await security.scan_document(
        document,
        namespaces=["comm", "us"],
    )

    print(f"\nPII detected: {result.has_pii}")
    print(f"Action taken: {result.action_taken.value}")
    print(f"Matches found: {result.match_count}")
    print(f"\nSanitized document (for vector DB):\n{result.sanitized_text}")

    # Store token map securely for later reversal
    if result.token_map:
        print(f"\nToken map (store securely):")
        for token, original in list(result.token_map.tokens.items())[:3]:
            print(f"  {token} -> [REDACTED]")
        print(f"  ... and {len(result.token_map.tokens) - 3} more")

    # ============================================================
    # LAYER 3: OUTPUT SCANNING (LLM Responses)
    # ============================================================
    print("\n[LAYER 3] OUTPUT SCANNING - LLM Response")
    print("-" * 70)

    # Simulate LLM response that leaks PII
    llm_response = "The customer's SSN is 123-45-6789 and email is john.doe@company.com"
    print(f"LLM response: {llm_response}")

    # Use strict blocking policy for output
    output_policy = SecurityPolicy(
        layer=SecurityLayer.OUTPUT,
        action=SecurityAction.BLOCK,
        severity_threshold=SeverityLevel.HIGH,
    )

    result = await security.scan_response(
        llm_response,
        namespaces=["comm", "us"],
        policy=output_policy,
    )

    print(f"\nPII detected: {result.has_pii}")
    print(f"Blocked: {result.blocked}")
    print(f"Action taken: {result.action_taken.value}")
    print(f"Response to user: {result.sanitized_text}")

    if result.reason:
        print(f"Reason: {result.reason}")

    # ============================================================
    # EXAMPLE: Different Security Policies
    # ============================================================
    print("\n" + "=" * 70)
    print("CUSTOM SECURITY POLICIES")
    print("=" * 70)

    # Strict policy: Block everything
    print("\n[POLICY 1] Strict blocking (HIGH severity)")
    strict_policy = SecurityPolicy(
        layer=SecurityLayer.INPUT,
        action=SecurityAction.BLOCK,
        severity_threshold=SeverityLevel.HIGH,
    )

    query_with_ssn = "What's the status for SSN 123-45-6789?"
    result = await security.scan_query(query_with_ssn, policy=strict_policy)
    print(f"Query: {query_with_ssn}")
    print(f"Blocked: {result.blocked}")
    print(f"Reason: {result.reason}")

    # Lenient policy: Just warn
    print("\n[POLICY 2] Lenient warning")
    lenient_policy = SecurityPolicy(
        layer=SecurityLayer.INPUT,
        action=SecurityAction.WARN,
        severity_threshold=SeverityLevel.LOW,
    )

    result = await security.scan_query(query_with_ssn, policy=lenient_policy)
    print(f"Query: {query_with_ssn}")
    print(f"Blocked: {result.blocked}")
    print(f"Action: {result.action_taken.value}")
    print(f"Allowed to proceed: Yes (with warning)")

    # ============================================================
    # EXAMPLE: Tokenization and Reversal
    # ============================================================
    print("\n" + "=" * 70)
    print("TOKENIZATION & REVERSAL")
    print("=" * 70)

    text = "Contact john@example.com or call 555-0123"
    print(f"Original: {text}")

    # Tokenize
    from datadetector.tokenization import SecureTokenizer

    tokenizer = SecureTokenizer(engine)
    sanitized, token_map = tokenizer.tokenize_with_map(text, namespaces=["comm"])

    print(f"Tokenized: {sanitized}")
    print(f"Token map hash: {token_map.hash[:16]}...")

    # Store sanitized version in vector DB
    print("\n→ Store in vector DB: {sanitized}")

    # Later, reverse if authorized
    detokenized = tokenizer.detokenize(sanitized, token_map)
    print(f"Detokenized (authorized): {detokenized}")

    print("\n" + "=" * 70)
    print("✓ RAG Security Integration Complete")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
