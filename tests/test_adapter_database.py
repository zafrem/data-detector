"""Tests for DatabaseAdapter using SQLite in-memory."""

import pytest

from datadetector.resource_models import (
    ConnectionConfig,
    ContainerType,
    DataResource,
    ResourceType,
)

# Skip all tests if sqlalchemy is not installed
sqlalchemy = pytest.importorskip("sqlalchemy")

from datadetector.adapters.database import DatabaseAdapter  # noqa: E402


@pytest.fixture
def sample_db():
    """Create an in-memory SQLite DB with PII-containing tables."""
    engine = sqlalchemy.create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(
            sqlalchemy.text(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT,
                    ssn TEXT,
                    phone TEXT,
                    age INTEGER
                )
                """
            )
        )
        conn.execute(
            sqlalchemy.text(
                """
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    billing_address TEXT,
                    credit_card TEXT,
                    amount REAL
                )
                """
            )
        )
        conn.execute(
            sqlalchemy.text(
                """
                CREATE TABLE logs (
                    id INTEGER PRIMARY KEY,
                    ip_address TEXT,
                    user_agent TEXT,
                    timestamp TEXT
                )
                """
            )
        )
        # Insert synthetic test data
        conn.execute(
            sqlalchemy.text(
                """
                INSERT INTO users (name, email, ssn, phone, age) VALUES
                ('John Doe', 'john@example.com', '123-45-6789', '010-1234-5678', 30),
                ('Jane Smith', 'jane@example.com', '987-65-4321', '010-9876-5432', 25),
                ('Bob Lee', 'bob@test.org', '111-22-3333', '010-1111-2222', 40)
                """
            )
        )
        conn.execute(
            sqlalchemy.text(
                """
                INSERT INTO orders (user_id, billing_address, credit_card, amount) VALUES
                (1, '123 Main St, NY 10001', '4111-1111-1111-1111', 99.99),
                (2, '456 Oak Ave, CA 90210', '5500-0000-0000-0004', 149.99)
                """
            )
        )
        conn.execute(
            sqlalchemy.text(
                """
                INSERT INTO logs (ip_address, user_agent, timestamp) VALUES
                ('192.168.1.1', 'Mozilla/5.0', '2024-01-01'),
                ('10.0.0.1', 'Chrome/120', '2024-01-02')
                """
            )
        )
        conn.commit()
    engine.dispose()

    return DataResource(
        name="test-sqlite",
        resource_type=ResourceType.DATABASE,
        connection=ConnectionConfig(uri="sqlite:///:memory:"),
    )


@pytest.fixture
def populated_adapter():
    """Create adapter with pre-populated SQLite DB."""
    resource = DataResource(
        name="test-db",
        resource_type=ResourceType.DATABASE,
        connection=ConnectionConfig(uri="sqlite:///:memory:"),
    )
    adapter = DatabaseAdapter(resource)
    adapter.connect()

    sa = sqlalchemy
    with adapter._engine.connect() as conn:
        conn.execute(
            sa.text(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, "
                "name TEXT, email TEXT, ssn TEXT, phone TEXT)"
            )
        )
        conn.execute(
            sa.text(
                "CREATE TABLE orders (id INTEGER PRIMARY KEY, "
                "user_id INTEGER REFERENCES users(id), "
                "credit_card TEXT, amount REAL)"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO users (name, email, ssn, phone) VALUES "
                "('John', 'john@example.com', '123-45-6789', '010-1234-5678')"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO orders (user_id, credit_card, amount) VALUES "
                "(1, '4111-1111-1111-1111', 99.99)"
            )
        )
        conn.commit()

    yield adapter
    adapter.close()


class TestDatabaseAdapterConnection:
    def test_connect_and_close(self):
        resource = DataResource(
            name="test",
            resource_type=ResourceType.DATABASE,
            connection=ConnectionConfig(uri="sqlite:///:memory:"),
        )
        adapter = DatabaseAdapter(resource)
        adapter.connect()
        assert adapter._connected is True
        adapter.close()
        assert adapter._connected is False

    def test_context_manager(self):
        resource = DataResource(
            name="test",
            resource_type=ResourceType.DATABASE,
            connection=ConnectionConfig(uri="sqlite:///:memory:"),
        )
        with DatabaseAdapter(resource) as adapter:
            assert adapter._connected is True
        assert adapter._connected is False

    def test_missing_uri_raises(self):
        resource = DataResource(
            name="test",
            resource_type=ResourceType.DATABASE,
            connection=ConnectionConfig(),
        )
        adapter = DatabaseAdapter(resource)
        with pytest.raises(ConnectionError):
            adapter.connect()

    def test_not_connected_raises(self):
        resource = DataResource(
            name="test",
            resource_type=ResourceType.DATABASE,
            connection=ConnectionConfig(uri="sqlite:///:memory:"),
        )
        adapter = DatabaseAdapter(resource)
        with pytest.raises(RuntimeError, match="not connected"):
            adapter.list_containers()


class TestDatabaseAdapterOperations:
    def test_list_containers(self, populated_adapter):
        containers = populated_adapter.list_containers()
        names = [c.name for c in containers]
        assert "users" in names
        assert "orders" in names

    def test_list_containers_with_pattern(self, populated_adapter):
        containers = populated_adapter.list_containers(pattern="user*")
        assert len(containers) == 1
        assert containers[0].name == "users"

    def test_container_type_is_table(self, populated_adapter):
        containers = populated_adapter.list_containers()
        for c in containers:
            assert c.container_type == ContainerType.TABLE

    def test_list_fields(self, populated_adapter):
        fields = populated_adapter.list_fields("users")
        names = [f.name for f in fields]
        assert "id" in names
        assert "email" in names
        assert "ssn" in names
        assert "phone" in names

    def test_field_info_properties(self, populated_adapter):
        fields = populated_adapter.list_fields("users")
        email_field = next(f for f in fields if f.name == "email")
        assert email_field.container_name == "users"
        assert email_field.qualified_name == "users.email"

    def test_sample_values(self, populated_adapter):
        values = populated_adapter.sample_values("users", "email", limit=10)
        assert len(values) == 1  # One distinct value inserted
        assert "john@example.com" in values

    def test_sample_values_skips_nulls(self, populated_adapter):
        # Insert a row with null email
        sa = sqlalchemy
        with populated_adapter._engine.connect() as conn:
            conn.execute(sa.text("INSERT INTO users (name) VALUES ('NullUser')"))
            conn.commit()
        values = populated_adapter.sample_values("users", "email", limit=10)
        assert all(v is not None and v != "None" for v in values)

    def test_sample_values_empty_table(self, populated_adapter):
        sa = sqlalchemy
        with populated_adapter._engine.connect() as conn:
            conn.execute(sa.text("CREATE TABLE empty_table (col TEXT)"))
            conn.commit()
        values = populated_adapter.sample_values("empty_table", "col", limit=10)
        assert values == []

    def test_get_relationships(self, populated_adapter):
        rels = populated_adapter.get_relationships()
        # SQLite may or may not enforce FK references in inspector,
        # but the method should not crash
        assert isinstance(rels, list)

    def test_get_row_count(self, populated_adapter):
        count = populated_adapter.get_row_count("users")
        assert count >= 1
