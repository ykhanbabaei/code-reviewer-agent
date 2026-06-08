from dataclasses import dataclass




@dataclass
class ContextRepoInfo:
    """
    ContextRepoInfo is a data class that holds the context information for a request.
    """
    user_name: str
    repository: str
    pull_number: int
