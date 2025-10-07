"""
Constants for the comment application.

This module contains all constant values used across the comment application
to maintain consistency and ease of maintenance.
"""

# Comment text validation
MIN_COMMENT_LENGTH = 1
MAX_COMMENT_LENGTH = 5000

# MPTT tree depth
MAX_REPLY_DEPTH = 3

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Cache timeouts (in seconds)
COMMENT_CACHE_TIMEOUT = 300  # 5 minutes