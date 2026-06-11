from dataclasses import dataclass




@dataclass
class ContextRepoInfo:
    """
    ContextRepoInfo is a data class that holds the context information for a request.
    """
    token: str
    user_name: str
    repository: str
    pull_number: int
    retrieval_used_count: int  = 0
