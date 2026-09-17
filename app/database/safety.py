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
