import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ColumnInfo:
    """Represents column information from database schema."""

    name: str
    type: str
    not_null: bool
    default_value: Optional[str]
    primary_key: bool


@dataclass
class ForeignKeyInfo:
    """Represents foreign key constraint information."""

    from_column: str
    to_table: str
    to_column: str


class SQLiteDatabase:
    """A comprehensive SQLite database interface for structure analysis and query execution."""

    def __init__(self, database_path: str, auto_connect: bool = True):
        """Initialize with database path."""
        self.database_path = database_path
        self.connection = None
        self.is_connected = False
        if auto_connect:
            self.connect()

    def connect(self) -> None:
        """Connect to the SQLite database."""
        if self.is_connected:
            return

        try:
            self.connection = sqlite3.connect(self.database_path)
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.is_connected = True
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Error connecting to database: {e}")

    def disconnect(self) -> None:
        """Close the database connection."""
        if self.connection and self.is_connected:
            self.connection.close()
            self.is_connected = False

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def ensure_connected(self) -> None:
        """Ensure database connection is active."""
        if not self.is_connected:
            self.connect()

    def _get_table_names(self) -> list[str]:
        """Get all table names from the database."""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [row[0] for row in cursor.fetchall()]

    def _get_column_info(self, table_name: str) -> list[ColumnInfo]:
        """Get column information for a specific table."""
        cursor = self.connection.cursor()
        cursor.execute(f"PRAGMA table_info(`{table_name}`)")

        columns = []
        for row in cursor.fetchall():
            columns.append(
                ColumnInfo(
                    name=row[1],
                    type=row[2],
                    not_null=bool(row[3]),
                    default_value=row[4],
                    primary_key=bool(row[5]),
                )
            )

        return columns

    def _get_foreign_keys(self, table_name: str) -> list[ForeignKeyInfo]:
        """Get foreign key information for a specific table."""
        cursor = self.connection.cursor()
        cursor.execute(f"PRAGMA foreign_key_list(`{table_name}`)")

        foreign_keys = []
        for row in cursor.fetchall():
            foreign_keys.append(
                ForeignKeyInfo(
                    from_column=row[3],
                    to_table=row[2],
                    to_column=row[4],
                )
            )

        return foreign_keys

    def _get_unique_constraints(self, table_name: str) -> dict[str, list[str]]:
        """Get unique constraints for a specific table."""
        cursor = self.connection.cursor()
        cursor.execute(f"PRAGMA index_list(`{table_name}`)")

        unique_constraints = {}
        for row in cursor.fetchall():
            if row[2]:
                index_name = row[1]
                cursor.execute(f"PRAGMA index_info(`{index_name}`)")
                columns = [col_row[2] for col_row in cursor.fetchall()]
                unique_constraints[index_name] = columns

        return unique_constraints

    def _format_create_table(self, table_name: str) -> str:
        """Format a CREATE TABLE statement for a specific table."""
        columns = self._get_column_info(table_name)
        foreign_keys = self._get_foreign_keys(table_name)
        unique_constraints = self._get_unique_constraints(table_name)

        lines = [f"CREATE TABLE {table_name} ("]

        max_name_length = max(len(col.name) for col in columns)
        max_type_length = max(len(col.type) for col in columns)

        column_lines = []
        primary_key_columns = []

        for col in columns:
            line_parts = []
            line_parts.append(f"    {col.name.ljust(max_name_length)}")
            line_parts.append(f"{col.type.ljust(max_type_length)}")

            if col.not_null:
                line_parts.append("NOT NULL")

            if col.default_value:
                line_parts.append(f"DEFAULT {col.default_value}")

            if col.primary_key:
                primary_key_columns.append(col.name)

            column_lines.append("  ".join(line_parts))

        lines.extend(column_lines)

        for constraint_name, constraint_columns in unique_constraints.items():
            if len(constraint_columns) == 1 and constraint_columns[0] not in [
                col.name for col in columns if col.primary_key
            ]:
                column_name = constraint_columns[0]
                for i, line in enumerate(lines[1:], 1):
                    if line.strip().startswith(column_name):
                        if "UNIQUE" not in line:
                            lines[i] = line.rstrip() + " UNIQUE"
                        break
            else:
                constraint_line = f"    CONSTRAINT {constraint_name} UNIQUE ({', '.join(constraint_columns)})"
                lines.append(constraint_line)

        for fk in foreign_keys:
            fk_line = f"    FOREIGN KEY ({fk.from_column}) REFERENCES {fk.to_table} ({fk.to_column})"
            lines.append(fk_line)

        if len(primary_key_columns) > 1:
            pk_line = f"    PRIMARY KEY ({', '.join(primary_key_columns)})"
            lines.append(pk_line)
        elif len(primary_key_columns) == 1:
            for i, line in enumerate(lines[1:], 1):
                if line.strip().startswith(primary_key_columns[0]):
                    if "PRIMARY KEY" not in line:
                        lines[i] = (
                            line.rstrip()
                            + ",\n    PRIMARY KEY ("
                            + primary_key_columns[0]
                            + ")"
                        )
                    break

        for i in range(1, len(lines) - 1):
            if not lines[i].rstrip().endswith(","):
                lines[i] = lines[i].rstrip() + ","

        lines.append(")")

        return "\n".join(lines)

    def structure(self) -> str:
        """Return the complete database structure as formatted CREATE TABLE statements."""
        self.ensure_connected()

        table_names = self._get_table_names()
        create_statements = []

        for table_name in table_names:
            create_statement = self._format_create_table(table_name)
            create_statements.append(create_statement)

        return ";\n".join(create_statements) + ";"

    def query(self, sql: str) -> tuple[list[str], list[tuple]]:
        """Execute a SELECT query and return results."""
        self.ensure_connected()

        cursor = self.connection.cursor()
        cursor.execute(sql)

        headers = (
            [description[0] for description in cursor.description]
            if cursor.description
            else []
        )
        rows = cursor.fetchall()

        return headers, rows


def main():
    """Main function to demonstrate usage."""
    path_to_db = os.path.join("data", "northwind.db")

    db = SQLiteDatabase(path_to_db)

    print("=== DATABASE STRUCTURE ===")
    structure = db.structure()
    print(structure)

    print("\n")
    print("=== SAMPLE QUERIES ===")
    try:
        headers, rows = db.query(
            "SELECT COUNT(*) as table_count FROM sqlite_master WHERE type='table'"
        )
        print(f"Headers: {headers}")
        print(f"Number of tables: {rows}")

        print("\n")
        headers, rows = db.query(
            "SELECT CustomerID, CompanyName FROM Customers LIMIT 3"
        )
        print(f"Headers: {headers}")
        print(f"First 3 customers: {rows}")

    except Exception as e:
        print(f"Query error: {e}")


if __name__ == "__main__":
    main()
