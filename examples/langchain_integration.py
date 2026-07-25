"""
LangChain integration example with data-detector RAG security.

This shows how to integrate PII protection into a LangChain RAG pipeline.

Install dependencies:
    pip install langchain openai chromadb

Note: This is a conceptual example. Actual implementation may vary
based on LangChain version and your specific use case.
"""

import asyncio
from typing import List

from datadetector import Engine, load_registry
from datadetector.rag_middleware import RAGSecurityMiddleware
from datadetector.rag_models import SecurityAction, SecurityLayer, SecurityPolicy, SeverityLevel


class SecureLangChainWrapper:
    """
    Wrapper for LangChain RAG with three-layer PII protection.

    Protects:
    1. Input: User queries before retrieval
    2. Storage: Documents before indexing
    3. Output: LLM responses before returning
    """

    def __init__(self, chain, security_middleware: RAGSecurityMiddleware):
        """
        Initialize secure wrapper.

        Args:
            chain: LangChain chain or retriever
            security_middleware: Data-detector RAG security middleware
        """
        self.chain = chain
        self.security = security_middleware

    async def secure_query(self, query: str) -> str:
        """
        Process query with input and output scanning.

        Args:
            query: User query

        Returns:
            Secure response (PII removed)
        """
        # Layer 1: Scan input query
        input_result = await self.security.scan_query(
            query,
            namespaces=["comm", "us"],
        )

        if input_result.blocked:
            return f"[QUERY BLOCKED] {input_result.reason}"

        # Use sanitized query for RAG
        sanitized_query = input_result.sanitized_text

        # Execute RAG chain (mock for this example)
        # In real implementation:
        # response = await self.chain.ainvoke(sanitized_query)
        response = f"Mock response for: {sanitized_query}"

        # Layer 3: Scan output response
        output_result = await self.security.scan_response(
            response,
            namespaces=["comm", "us"],
        )

        if output_result.blocked:
            return "[RESPONSE BLOCKED] The response contains sensitive information."

        return output_result.sanitized_text

    async def secure_add_documents(self, documents: List[str]) -> List[str]:
        """
        Add documents with PII scanning.

        Args:
            documents: Documents to add

        Returns:
            Sanitized documents with token maps
        """
        sanitized_docs = []
        token_maps = []

        for doc in documents:
            # Layer 2: Scan document before indexing
            result = await self.security.scan_document(
                doc,
                namespaces=["comm", "us"],
            )

            if not result.blocked:
                sanitized_docs.append(result.sanitized_text)
                if result.token_map:
                    token_maps.append(result.token_map)

        # Store token maps securely for later reversal
        # In production: save to encrypted database
        print(f"Stored {len(token_maps)} token maps securely")

        return sanitized_docs


async def main():
    """Example usage."""
    print("=" * 70)
    print("LANGCHAIN + DATA-DETECTOR INTEGRATION")
    print("=" * 70)

    # Initialize security
    registry = load_registry()
    engine = Engine(registry)
    security = RAGSecurityMiddleware(engine)

    # Create mock LangChain chain
    # In real usage, this would be your actual LangChain RAG setup:
    # from langchain.chains import RetrievalQA
    # chain = RetrievalQA.from_chain_type(...)
    chain = None  # Mock for this example

    # Wrap with security
    secure_chain = SecureLangChainWrapper(chain, security)

    # ============================================================
    # Example 1: Secure Document Indexing
    # ============================================================
    print("\n[EXAMPLE 1] Secure Document Indexing")
    print("-" * 70)

    documents = [
        "Customer John Doe, email: john@example.com, phone: 555-0123",
        "Account SSN: 123-45-6789, balance: $1000",
        "Support ticket from jane@example.com regarding billing",
    ]

    print("Original documents:")
    for i, doc in enumerate(documents, 1):
        print(f"  {i}. {doc}")

    sanitized = await secure_chain.secure_add_documents(documents)

    print("\nSanitized documents (for vector DB):")
    for i, doc in enumerate(sanitized, 1):
        print(f"  {i}. {doc}")

    # ============================================================
    # Example 2: Secure Query Processing
    # ============================================================
    print("\n[EXAMPLE 2] Secure Query Processing")
    print("-" * 70)

    queries = [
        "What's the email for customer john@example.com?",
        "Show me details for SSN 123-45-6789",
        "What are the latest support tickets?",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        response = await secure_chain.secure_query(query)
        print(f"Response: {response}")

    # ============================================================
    # Example 3: Custom Policies per Use Case
    # ============================================================
    print("\n[EXAMPLE 3] Custom Security Policies")
    print("-" * 70)

    # Scenario 1: Public chatbot (strict)
    print("\nScenario: Public Chatbot (strict blocking)")
    public_policy = SecurityPolicy(
        layer=SecurityLayer.OUTPUT,
        action=SecurityAction.BLOCK,
        severity_threshold=SeverityLevel.MEDIUM,
    )
    security.update_policy(SecurityLayer.OUTPUT, public_policy)

    query = "General question about products"
    response = await secure_chain.secure_query(query)
    print(f"Public chatbot response: {response}")

    # Scenario 2: Internal tool (lenient)
    print("\nScenario: Internal Tool (warning mode)")
    internal_policy = SecurityPolicy(
        layer=SecurityLayer.INPUT,
        action=SecurityAction.WARN,
        severity_threshold=SeverityLevel.LOW,
    )
    security.update_policy(SecurityLayer.INPUT, internal_policy)

    print("\n" + "=" * 70)
    print("✓ Integration Example Complete")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Replace mock chain with your actual LangChain setup")
    print("2. Implement token map storage (encrypted database)")
    print("3. Add monitoring and alerting for blocked queries")
    print("4. Customize policies per use case")


if __name__ == "__main__":
    asyncio.run(main())
