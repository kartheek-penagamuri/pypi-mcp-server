from .version import __version__

# Core models
from .models import (
    Dependency,
    PackageInfo,
    PackageSearchResult,
    ProjectInfo,
)

# Migration models
from .migration_models import (
    APIElement,
    APISurface,
    APIChange,
    VersionComparison,
    MigrationResource,
    MigrationResources,
)

# Core components
from .package_manager import PackageManager

# Migration components
from .migration_guide_finder import MigrationGuideFinder

# Error classes
from .errors import (
    MCPServerError,
    NetworkError,
    FileSystemError,
    ParsingError,
    # Migration errors
    MigrationAnalysisError,
    PackageAnalysisError,
    VersionComparisonError,
    MigrationResourceError,
    APIExtractionError,
)
