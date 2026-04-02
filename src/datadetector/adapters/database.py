"""Database adapter using SQLAlchemy for RDBMS scanning.

Supports PostgreSQL, MySQL, SQLite, MSSQL, Oracle, and any other
database supported by SQLAlchemy.

Install: pip install data-detector[database]
"""

import fnmatch
import logging
from typing import Any, List, Optional

from datadetector.resource_adapter import ResourceAdapter
from datadetector.resource_models import (
    ContainerInfo,
    ContainerType,
    DataResource,
    FieldInfo,
    FieldRelationship,
    RelationshipType,
)

logger = logging.getLogger(__name__)

_sqlalchemy: Optional[Any] = None


def _get_sqlalchemy() -> Any:
    """Lazy-load sqlalchemy with clear error message."""
    global _sqlalchemy
    if _sqlalchemy is None:
        try:
            import sqlalchemy

            _sqlalchemy = sqlalchemy
        except ImportError:
            raise ImportError(
                "sqlalchemy is required for database scanning. "
                "Install with: pip install data-detector[database]"
            )
    return _sqlalchemy


class DatabaseAdapter(ResourceAdapter):
    """SQLAlchemy-based adapter for RDBMS scanning.

    ConnectionConfig usage:
        uri: SQLAlchemy connection string (e.g., "sqlite:///mydb.db",
             "postgresql://user:pass@host/dbname")
        params:
            schema: Schema name for multi-schema databases (default: None)
            include_views: Whether to include views (default: True)

    Example:
        >>> resource = DataResource(
        ...     name="my-postgres",
        ...     resource_type=ResourceType.DATABASE,
        ...     connection=ConnectionConfig(
        ...         uri="postgresql://user:pass@localhost/mydb",
        ...         params={"schema": "public", "include_views": True},
        ...     ),
        ... )
        >>> with DatabaseAdapter(resource) as adapter:
        ...     tables = adapter.list_containers()
    """

    def __init__(self, resource: DataResource) -> None:
        super().__init__(resource)
        self._engine: Optional[Any] = None
        self._inspector: Optional[Any] = None

    def connect(self) -> None:
        """Create SQLAlchemy engine and inspector."""
        sa = _get_sqlalchemy()
        uri = self.resource.connection.uri
        if not uri:
            raise ConnectionError("Database connection URI is required.")

        try:
            self._engine = sa.create_engine(uri)
            self._inspector = sa.inspect(self._engine)
            self._connected = True
            logger.info(f"Connected to database: {self.resource.name}")
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to database '{self.resource.name}': {e}"
            ) from e

    def close(self) -> None:
        """Dispose SQLAlchemy engine."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._inspector = None
        self._connected = False
        logger.info(f"Disconnected from database: {self.resource.name}")

    def list_containers(
        self,
        pattern: Optional[str] = None,
    ) -> List[ContainerInfo]:
        """List tables and optionally views.

        Args:
            pattern: Optional glob pattern to filter table/view names.

        Returns:
            List of ContainerInfo objects.
        """
        self._ensure_connected()
        schema = self.resource.connection.params.get("schema")
        include_views = self.resource.connection.params.get("include_views", True)

        containers: List[ContainerInfo] = []

        # Tables
        table_names = self._inspector.get_table_names(schema=schema)
        for name in table_names:
            if pattern and not fnmatch.fnmatch(name, pattern):
                continue
            containers.append(
                ContainerInfo(
                    name=name,
                    container_type=ContainerType.TABLE,
                    metadata={"schema": schema},
                )
            )

        # Views
        if include_views:
            try:
                view_names = self._inspector.get_view_names(schema=schema)
                for name in view_names:
                    if pattern and not fnmatch.fnmatch(name, pattern):
                        continue
                    containers.append(
                        ContainerInfo(
                            name=name,
                            container_type=ContainerType.VIEW,
                            metadata={"schema": schema},
                        )
                    )
            except Exception as e:
                logger.warning(f"Could not list views: {e}")

        return containers

    def list_fields(self, container_name: str) -> List[FieldInfo]:
        """List columns of a table or view.

        Args:
            container_name: Table or view name.

        Returns:
            List of FieldInfo objects.
        """
        self._ensure_connected()
        schema = self.resource.connection.params.get("schema")
        columns = self._inspector.get_columns(container_name, schema=schema)

        fields: List[FieldInfo] = []
        for col in columns:
            fields.append(
                FieldInfo(
                    name=col["name"],
                    container_name=container_name,
                    data_type=str(col.get("type", "unknown")),
                    nullable=col.get("nullable", True),
                    description=col.get("comment", "") or "",
                    metadata={
                        k: str(v) for k, v in col.items() if k not in ("name", "type", "nullable")
                    },
                )
            )

        return fields

    def sample_values(
        self,
        container_name: str,
        field_name: str,
        limit: int = 100,
    ) -> List[str]:
        """Sample distinct non-null values from a column.

        Args:
            container_name: Table or view name.
            field_name: Column name.
            limit: Maximum number of sample values.

        Returns:
            List of string-coerced values.
        """
        self._ensure_connected()
        sa = _get_sqlalchemy()

        schema = self.resource.connection.params.get("schema")
        quoted_table = container_name
        quoted_col = field_name
        if schema:
            quoted_table = f"{schema}.{container_name}"

        query = sa.text(
            f'SELECT DISTINCT "{quoted_col}" FROM "{quoted_table}" '
            f'WHERE "{quoted_col}" IS NOT NULL LIMIT :limit'
        )

        values: List[str] = []
        with self._engine.connect() as conn:
            result = conn.execute(query, {"limit": limit})
            for row in result:
                val = row[0]
                if val is not None:
                    values.append(str(val))

        return values

    def get_relationships(self) -> List[FieldRelationship]:
        """Discover foreign key relationships.

        Returns:
            List of FieldRelationship objects for all FK relationships.
        """
        self._ensure_connected()
        schema = self.resource.connection.params.get("schema")
        relationships: List[FieldRelationship] = []

        table_names = self._inspector.get_table_names(schema=schema)
        for table_name in table_names:
            try:
                fks = self._inspector.get_foreign_keys(table_name, schema=schema)
                for fk in fks:
                    referred_table = fk.get("referred_table", "")
                    constrained_cols = fk.get("constrained_columns", [])
                    referred_cols = fk.get("referred_columns", [])

                    for src_col, tgt_col in zip(constrained_cols, referred_cols):
                        relationships.append(
                            FieldRelationship(
                                source_resource=self.resource.name,
                                source_field=f"{table_name}.{src_col}",
                                target_resource=self.resource.name,
                                target_field=f"{referred_table}.{tgt_col}",
                                relationship_type=RelationshipType.FOREIGN_KEY,
                                metadata={
                                    "constraint_name": fk.get("name", ""),
                                    "referred_schema": fk.get("referred_schema"),
                                },
                            )
                        )
            except Exception as e:
                logger.warning(f"Could not get FKs for {table_name}: {e}")

        return relationships

    def get_row_count(self, container_name: str) -> int:
        """Get approximate row count for a table.

        Args:
            container_name: Table name.

        Returns:
            Row count.
        """
        self._ensure_connected()
        sa = _get_sqlalchemy()

        query = sa.text(f'SELECT COUNT(*) FROM "{container_name}"')
        with self._engine.connect() as conn:
            result = conn.execute(query)
            row = result.fetchone()
            return row[0] if row else 0

    def get_view_definition(self, view_name: str) -> Optional[str]:
        """Get the SQL definition of a view.

        Args:
            view_name: View name.

        Returns:
            View SQL definition, or None if not available.
        """
        self._ensure_connected()
        schema = self.resource.connection.params.get("schema")
        try:
            return self._inspector.get_view_definition(view_name, schema=schema)
        except Exception as e:
            logger.warning(f"Could not get view definition for {view_name}: {e}")
            return None
