"""Custom exceptions classes."""

class BadAESDetection(Exception):
    """Wrong AES detection for a trace."""
    pass

class BadTrace(Exception):
    """Trace should be classifed as a bad trace."""
    pass
