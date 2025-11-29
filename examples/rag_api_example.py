"""
Example of using the RAG security API endpoints.

Start the server first:
    data-detector serve --port 8080

Then run this example:
    python examples/rag_api_example.py
"""

import json

import requests

# Base URL for the data-detector server
BASE_URL = "http://localhost:8080"


def print_section(title):
    """Print section header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def scan_query(query, action="sanitize", severity="medium"):
    """Layer 1: Scan user query."""
    response = requests.post(
        f"{BASE_URL}/rag/scan-query",
        json={
            "query": query,
            "namespaces": ["comm", "us"],
            "action": action,
            "severity_threshold": severity,
        },
    )
    return response.json()


def scan_document(document, action="sanitize", use_tokenization=True):
    """Layer 2: Scan document before indexing."""
    response = requests.post(
        f"{BASE_URL}/rag/scan-document",
        json={
            "document": document,
            "namespaces": ["comm", "us"],
            "action": action,
            "use_tokenization": use_tokenization,
        },
    )
    return response.json()


def scan_response(llm_response, action="block", severity="high", token_map=None):
    """Layer 3: Scan LLM response."""
    response = requests.post(
        f"{BASE_URL}/rag/scan-response",
        json={
            "response": llm_response,
            "namespaces": ["comm", "us"],
            "action": action,
            "severity_threshold": severity,
            "token_map": token_map,
        },
    )
    return response.json()


def main():
    print_section("RAG SECURITY API - QUICK START")

    # ============================================================
    # LAYER 1: Scan User Query
    # ============================================================
    print_section("[LAYER 1] INPUT SCANNING")

    query = "What's the email for john@example.com?"
    print(f"\nQuery: {query}")

    result = scan_query(query, action="sanitize")

    print(f"PII detected: {result['pii_detected']}")
    print(f"Sanitized: {result['sanitized_text']}")
    print(f"Matches: {result['match_count']}")
    print(f"Action: {result['action_taken']}")

    # ============================================================
    # LAYER 2: Scan Document (with tokenization)
    # ============================================================
    print_section("[LAYER 2] STORAGE SCANNING")

    document = """
    Customer: John Doe
    Email: john@example.com
    Phone: 555-0123
    SSN: 123-45-6789
    """

    print(f"\nOriginal document:{document}")

    result = scan_document(document, use_tokenization=True)

    print(f"\nPII detected: {result['pii_detected']}")
    print(f"Matches: {result['match_count']}")
    print(f"Sanitized for vector DB:\n{result['sanitized_text']}")

    # Save token map for later
    token_map = result.get("token_map")
    if token_map:
        print(f"\nToken map stored ({len(token_map)} tokens)")

    # ============================================================
    # LAYER 3: Scan LLM Response (strict blocking)
    # ============================================================
    print_section("[LAYER 3] OUTPUT SCANNING")

    llm_response = "The customer SSN is 123-45-6789"
    print(f"\nLLM Response: {llm_response}")

    result = scan_response(llm_response, action="block", severity="high")

    print(f"\nPII detected: {result['pii_detected']}")
    print(f"Blocked: {result['blocked']}")
    print(f"Response to user: {result['sanitized_text']}")

    if result["blocked"]:
        print(f"⚠ WARNING: {result['reason']}")

    # ============================================================
    # Test Different Policies
    # ============================================================
    print_section("TESTING DIFFERENT POLICIES")

    # Test 1: Strict blocking on input
    print("\n[TEST 1] Strict blocking on sensitive query")
    query = "Process payment for SSN 123-45-6789"
    result = scan_query(query, action="block", severity="high")
    print(f"Query: {query}")
    print(f"Blocked: {result['blocked']}")
    print(f"Reason: {result.get('reason', 'N/A')}")

    # Test 2: Warning mode
    print("\n[TEST 2] Warning mode (allow with logging)")
    result = scan_query(query, action="warn", severity="low")
    print(f"Query: {query}")
    print(f"Blocked: {result['blocked']}")
    print(f"Action: {result['action_taken']}")
    print(f"Sanitized: {result['sanitized_text']}")

    # Test 3: Masking instead of tokenization
    print("\n[TEST 3] Document with masking (non-reversible)")
    result = scan_document(document, use_tokenization=False)
    print(f"Sanitized (masked):\n{result['sanitized_text']}")

    print_section("✓ ALL TESTS COMPLETE")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server.")
        print("Please start the server first:")
        print("    data-detector serve --port 8080")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
