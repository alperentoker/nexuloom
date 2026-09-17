import re
from typing import Tuple


class SQLSafetyError(Exception):
    """Raised when an unsafe or non-read-only SQL query is detected."""
    pass


# Disallowed keywords anywhere as top-level DDL/DML tokens
DISALLOWED_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE",
    "REPLACE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "CALL", "MERGE",
    "UPSERT", "ATTACH", "DETACH", "SHUTDOWN", "KILL", "LOCK", "RENAME"
}

# Regex to strip comments
SQL_COMMENT_PATTERN = re.compile(r"(--[^\n]*|\/\*[\s\S]*?\*\/)", re.MULTILINE)


class SQLSafetyValidator:
    """Validates that SQL queries are strictly read-only and safe to execute."""

    @classmethod
    def clean_sql(cls, query: str) -> str:
        """Strips comments and normalizes whitespace."""
        no_comments = SQL_COMMENT_PATTERN.sub(" ", query)
        return " ".join(no_comments.strip().split())

    @classmethod
    def validate_read_only(cls, query: str) -> Tuple[bool, str]:
        """Validates query is purely read-only (SELECT / WITH / EXPLAIN).
        Returns (is_valid, error_message).
        """
        if not query or not query.strip():
            return False, "Query cannot be empty."

        clean = cls.clean_sql(query)
        if not clean:
            return False, "Query contains only comments or whitespace."

        # Check multiple statements (semicolon separating multiple queries)
        # Semicolon at the very end is allowed, but not inside separating statements
        stripped_semicolon = clean.rstrip(";").strip()
        if ";" in stripped_semicolon:
            return False, "Multiple SQL statements are strictly forbidden for safety."

        tokens = re.findall(r"\b[A-Za-z_]+\b", clean)
        if not tokens:
            return False, "No valid SQL tokens found."

        first_token = tokens[0].upper()
        if first_token not in ("SELECT", "WITH", "EXPLAIN"):
            return False, f"Only SELECT or WITH queries are permitted. Got '{first_token}'."

        upper_tokens = {t.upper() for t in tokens}
        forbidden_found = upper_tokens.intersection(DISALLOWED_KEYWORDS)
        if forbidden_found:
            return False, f"Query contains forbidden modification keywords: {', '.join(forbidden_found)}."

        # Additional regex checks for destructive patterns
        dangerous_patterns = [
            r"\bINTO\s+OUTFILE\b",
            r"\bLOAD_FILE\b",
            r"\bINFORMATION_SCHEMA\.USER_PRIVILEGES\b",
            r"\bPG_SLEEP\b",
            r"\bWAITFOR\s+DELAY\b",
            r"\bBENCHMARK\b",
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, clean, re.IGNORECASE):
                return False, f"Query matches forbidden pattern '{pattern}'."

        return True, "Valid read-only query."

    @classmethod
    def validate_identifier(cls, name: str) -> str:
        """Validates a single SQL identifier (table, column, or schema name).
        Raises SQLSafetyError if invalid. Returns validated identifier.
        """
        if not name or not isinstance(name, str):
            raise SQLSafetyError("SQL identifier cannot be empty.")
        clean = name.strip()
        if "." in clean:
            parts = clean.split(".")
            for p in parts:
                if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", p):
                    raise SQLSafetyError(f"Invalid SQL identifier component: '{p}'.")
            return clean
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", clean):
            raise SQLSafetyError(f"Invalid SQL identifier: '{name}'. Identifiers must contain only alphanumeric characters and underscores.")
        return clean

    @classmethod
    def validate_table_identifier(cls, table_name: str) -> str:
        """Validates a table name, supporting optional schema prefix ('schema.table' or 'table').
        Raises SQLSafetyError if invalid.
        """
        if not table_name or not isinstance(table_name, str):
            raise SQLSafetyError("Table name cannot be empty.")
        clean = table_name.strip()
        if "." in clean:
            parts = clean.split(".")
            if len(parts) != 2:
                raise SQLSafetyError(f"Invalid qualified table identifier: '{table_name}'.")
            s = cls.validate_identifier(parts[0])
            t = cls.validate_identifier(parts[1])
            return f"{s}.{t}"
        return cls.validate_identifier(clean)

    @classmethod
    def quote_identifier(cls, name: str) -> str:
        """Safely quotes an identifier after validation."""
        validated = cls.validate_table_identifier(name)
        if "." in validated:
            s, t = validated.split(".")
            return f'"{s}"."{t}"'
        return f'"{validated}"'

    @classmethod
    def validate_kpi_formula(cls, formula: str) -> Tuple[bool, str, list]:
        """Validates that a KPI formula is strictly composed of allowed aggregate functions,
        valid column identifiers, arithmetic operators, numbers, and parentheses.
        Returns (is_valid, error_message, list_of_column_names).
        """
        if not formula or not isinstance(formula, str) or not formula.strip():
            return False, "KPI formula cannot be empty.", []

        clean = formula.strip()
        # Disallow semicolons, comments, or quotes
        if any(c in clean for c in (";", "--", "/*", "*/", "'", '"', "`", "\\")):
            return False, "KPI formula contains invalid characters or SQL injection patterns.", []

        # Check for disallowed modification keywords and SQL query structure keywords
        forbidden_formula_keywords = {
            "SELECT", "FROM", "WHERE", "UNION", "JOIN", "HAVING", "GROUP", "ORDER",
            "LIMIT", "CASE", "WHEN", "THEN", "ELSE", "END", "TABLE", "INTO", "VALUES",
            "WITH", "ALL", "DISTINCT", "ON", "OR", "AND", "NOT", "NULL", "IS", "IN",
            "EXISTS", "BETWEEN", "LIKE", "AS"
        }
        upper_tokens = set(re.findall(r"\b[A-Za-z_]+\b", clean.upper()))
        forbidden = upper_tokens.intersection(DISALLOWED_KEYWORDS.union(forbidden_formula_keywords))
        if forbidden:
            return False, f"KPI formula contains forbidden keywords: {', '.join(forbidden)}.", []

        # Allowed aggregate functions
        allowed_funcs = {"SUM", "AVG", "COUNT", "MIN", "MAX"}

        # Extract all identifier tokens
        identifiers = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", clean)
        column_names = []
        for ident in identifiers:
            ident_upper = ident.upper()
            if ident_upper in allowed_funcs:
                continue
            # Otherwise, it must be a valid column name
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", ident):
                return False, f"Invalid column name '{ident}' in formula.", []
            if ident not in column_names:
                column_names.append(ident)

        # Ensure balanced parentheses
        open_parens = clean.count("(")
        close_parens = clean.count(")")
        if open_parens != close_parens:
            return False, f"Mismatched parentheses in formula: {open_parens} open vs {close_parens} close.", []

        # Verify formula matches aggregate expressions pattern
        # Allowed chars: letters, digits, underscores, spaces, +, -, *, /, (, ), .
        if not re.match(r"^[a-zA-Z0-9_\s\+\-\*\/\(\)\.]+$", clean):
            return False, "KPI formula contains unauthorized special characters.", []

        return True, "Valid KPI formula.", column_names

    @classmethod
    def validate_condition_sql(cls, condition: str) -> Tuple[bool, str]:
        """Validates that a business rule condition SQL is safe (read-only, no multi-statements, no DDL/DML)."""
        if not condition or not condition.strip():
            return False, "Condition cannot be empty."

        # Reject semicolons, comments, or quotes escaping before normalization
        if any(tok in condition for tok in (";", "--", "/*", "*/")):
            return False, "Condition contains forbidden characters (semicolons or comments)."

        clean = cls.clean_sql(condition)
        # Test within a dummy SELECT
        dummy_query = f"SELECT 1 FROM tbl WHERE {clean}"
        return cls.validate_read_only(dummy_query)

    @classmethod
    def enforce_safety_and_limit(cls, query: str, max_rows: int = 50000, default_limit: int = 1000) -> str:
        """Validates the query and appends a safe LIMIT if none exists."""
        is_valid, err = cls.validate_read_only(query)
        if not is_valid:
            raise SQLSafetyError(err)

        clean = query.strip().rstrip(";")
        # Check if query already has a LIMIT or TOP clause
        limit_match = re.search(r"\bLIMIT\s+(\d+)\b", clean, re.IGNORECASE)
        if limit_match:
            existing_limit = int(limit_match.group(1))
            if existing_limit > max_rows:
                # Replace with max allowed
                clean = re.sub(r"\bLIMIT\s+\d+\b", f"LIMIT {max_rows}", clean, flags=re.IGNORECASE)
            return clean

        # If no limit found, append default limit
        return f"{clean} LIMIT {default_limit}"

