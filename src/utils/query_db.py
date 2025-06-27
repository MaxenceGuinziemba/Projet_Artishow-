#!/usr/bin/env python3
"""
Database query utility for hospital simulation.

This script allows running SQL queries against the hospital simulation database
from the command line with nicely formatted output.

Usage:
    python src/utils/query_db.py "SELECT * FROM simulations LIMIT 5"
    python src/utils/query_db.py "SELECT COUNT(*) as total_patients FROM patient_treated"
    python src/utils/query_db.py --tables  # List all tables
    python src/utils/query_db.py --schema TABLE_NAME  # Show table schema
"""

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import List, Tuple, Any

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import DB_PATH


def format_table(headers: List[str], rows: List[Tuple[Any, ...]], max_width: int = 100) -> str:
    """Format query results as a nice table.
    
    Args:
        headers: Column headers
        rows: Data rows
        max_width: Maximum width for each column
        
    Returns:
        Formatted table string
    """
    if not rows:
        return "No results found."
    
    # Calculate column widths
    col_widths = []
    for i, header in enumerate(headers):
        max_col_width = len(header)
        for row in rows:
            if row[i] is not None:
                max_col_width = max(max_col_width, len(str(row[i])))
        # Limit column width
        col_widths.append(min(max_col_width, max_width // len(headers)))
    
    # Create format string
    format_str = " | ".join(f"{{:<{width}}}" for width in col_widths)
    separator = "-+-".join("-" * width for width in col_widths)
    
    # Build table
    lines = []
    lines.append(format_str.format(*headers))
    lines.append(separator)
    
    for row in rows:
        formatted_row = []
        for i, value in enumerate(row):
            if value is None:
                formatted_row.append("NULL")
            else:
                str_value = str(value)
                if len(str_value) > col_widths[i]:
                    str_value = str_value[:col_widths[i]-3] + "..."
                formatted_row.append(str_value)
        lines.append(format_str.format(*formatted_row))
    
    return "\n".join(lines)


def get_table_list(conn: sqlite3.Connection) -> List[str]:
    """Get list of all tables in the database.
    
    Args:
        conn: Database connection
        
    Returns:
        List of table names
    """
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row[0] for row in cursor.fetchall()]


def get_table_schema(conn: sqlite3.Connection, table_name: str) -> List[Tuple[str, str, str]]:
    """Get schema information for a table.
    
    Args:
        conn: Database connection
        table_name: Name of the table
        
    Returns:
        List of (column_name, data_type, constraints) tuples
    """
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    schema = cursor.fetchall()
    
    # Format as (name, type, constraints)
    formatted_schema = []
    for row in schema:
        cid, name, data_type, not_null, default_value, pk = row
        constraints = []
        if pk:
            constraints.append("PRIMARY KEY")
        if not_null:
            constraints.append("NOT NULL")
        if default_value is not None:
            constraints.append(f"DEFAULT {default_value}")
        
        formatted_schema.append((name, data_type, ", ".join(constraints)))
    
    return formatted_schema


def execute_query(query: str) -> None:
    """Execute a SQL query and print formatted results.
    
    Args:
        query: SQL query to execute
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(query)
        
        if query.strip().upper().startswith('SELECT'):
            rows = cursor.fetchall()
            if rows:
                headers = list(rows[0].keys())
                data_rows = [tuple(row) for row in rows]
                print(format_table(headers, data_rows))
                print(f"\n{len(rows)} row(s) returned.")
            else:
                print("No results found.")
        else:
            # For non-SELECT queries (INSERT, UPDATE, DELETE)
            conn.commit()
            print(f"Query executed successfully. {cursor.rowcount} row(s) affected.")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    """Main entry point for the query utility."""
    parser = argparse.ArgumentParser(
        description="Query the hospital simulation database",
        epilog="""
Examples:
  %(prog)s "SELECT * FROM simulations LIMIT 5"
  %(prog)s "SELECT COUNT(*) as patients FROM patient_treated WHERE sim_id = 1"
  %(prog)s "SELECT disease, COUNT(*) as count FROM patient_treated GROUP BY disease"
  %(prog)s --tables
  %(prog)s --schema simulations
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('query', nargs='?', help='SQL query to execute')
    parser.add_argument('--tables', action='store_true', help='List all tables in the database')
    parser.add_argument('--schema', metavar='TABLE', help='Show schema for a specific table')
    parser.add_argument('--db-path', default=DB_PATH, help=f'Path to database file (default: {DB_PATH})')
    
    args = parser.parse_args()
    
    # Check if database exists
    if not Path(args.db_path).exists():
        print(f"Database file not found: {args.db_path}")
        print("Make sure you've run a simulation first to create the database.")
        sys.exit(1)
    
    # Update DB_PATH if custom path provided
    global DB_PATH
    DB_PATH = args.db_path
    
    try:
        conn = sqlite3.connect(DB_PATH)
        
        if args.tables:
            # List all tables
            tables = get_table_list(conn)
            print("Tables in the database:")
            print("=" * 25)
            for table in tables:
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table:<20} ({count} rows)")
            
        elif args.schema:
            # Show table schema
            schema = get_table_schema(conn, args.schema)
            print(f"Schema for table '{args.schema}':")
            print("=" * 50)
            headers = ["Column", "Type", "Constraints"]
            print(format_table(headers, schema))
            
        elif args.query:
            # Execute the provided query
            execute_query(args.query)
            
        else:
            # No arguments provided, show help
            parser.print_help()
            print("\nQuick examples:")
            print("  List tables:        python src/utils/query_db.py --tables")
            print("  Show simulations:   python src/utils/query_db.py \"SELECT * FROM simulations\"")
            print("  Count patients:     python src/utils/query_db.py \"SELECT COUNT(*) FROM patient_treated\"")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()