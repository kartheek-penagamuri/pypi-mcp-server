class MCPServerError(Exception):
    pass

class NetworkError(MCPServerError):
    pass

class FileSystemError(MCPServerError):
    pass

class ParsingError(MCPServerError):
    pass


# Migration-specific error classes
class MigrationAnalysisError(MCPServerError):
    """Base exception for migration analysis errors."""
    pass


class PackageAnalysisError(MigrationAnalysisError):
    """Failed to analyze package API surface."""
    pass


class VersionComparisonError(MigrationAnalysisError):
    """Cannot compare specified package versions."""
    pass


class MigrationResourceError(MigrationAnalysisError):
    """Unable to find migration documentation or resources."""
    pass


class APIExtractionError(MigrationAnalysisError):
    """Failed to extract API surface from package."""
    pass
