from github import Github, PullRequest
from langgraph.errors import NodeError
from langgraph.runtime import Runtime
from langgraph.types import Command
from langgraph.constants import END

from app.agents.context import ContextRepoInfo
from app.agents.state import PRState, PRMetadata, PRData, ChangedFile
import logging
from app.config import settings

logger = logging.getLogger(__name__)


def build_pr_data_from(pr: PullRequest) -> PRData:
    # Extract PR metadata

    pr_metadata = PRMetadata(
        title=pr.title,
        description=pr.body or "",
        author=pr.user.login,
        base_branch=pr.base.ref,
        labels=[label.name for label in pr.labels]
    )

    # Extract files changed
    files_changed = []
    for file in pr.get_files():
        files_changed.append(ChangedFile(
            filename=file.filename,
            status=file.status,
            additions=file.additions,
            deletions=file.deletions,
            patch=file.patch or "",
            full_content=file.contents_url if file.contents_url else None
        ))

    # Extract linked issues
    linked_issues = []
    if pr.body:
        # Simple extraction of #<number> from body
        import re
        linked_issues = re.findall(r'#(\d+)', pr.body)
        linked_issues = [f"#{issue}" for issue in linked_issues]

    # Aggregate PR data
    return PRData(
        pr_metadata=pr_metadata,
        files_changed=files_changed,
        linked_issues=linked_issues,
        review_comments=[]
    )

async def data_retriever_node(state: PRState, runtime: Runtime[ContextRepoInfo]):
    """Performs the connecting to remote repository and loading of the PR data."""
    logger.info(f"retrieving PR data for request {runtime.context}")

    if settings.IS_MOCK:
        return {"pr_data": mock_build_pr_data_from()}
    else:
        return await data_retriever(runtime=runtime)

async def data_retriever(runtime: Runtime[ContextRepoInfo]):
    g = Github()
    repo = g.get_user(runtime.context.user_name).get_repo(runtime.context.repository)
    pr = repo.get_pull(number=runtime.context.pull_number)
    return {"pr_data": build_pr_data_from(pr)}


def mock_build_pr_data_from():
    import json
    json_string = '''{
       "files_changed":[
          {
             "additions":7,
             "deletions":0,
             "filename":"src/main/java/org/softmind/urlshortener/controller/UrlShortenerController.java",
             "full_content":"https://api.github.com/repos/ykhanbabaei/url-shortener/contents/src%2Fmain%2Fjava%2Forg%2Fsoftmind%2Furlshortener%2Fcontroller%2FUrlShortenerController.java?ref=0ba3ff92f801b3ae77407120afe1e8fe05bff349",
             "patch":"@@ -25,4 +25,11 @@ public CompletableFuture<String> findUrl(@PathVariable(\\"code\\") String code){\\n         return urlShortenerService.findUrl(code);\\n     }\\n \\n+    @DeleteMapping(path = \\"api/unregister\\")\\n+    public CompletableFuture<Void> unregister(@RequestBody UrlDto urlDto){\\n+        return urlShortenerService.unregister(urlDto.url());\\n+    }\\n+\\n+\\n+\\n }",
             "status":"modified"
          },
          {
             "additions":4,
             "deletions":0,
             "filename":"src/main/java/org/softmind/urlshortener/exception/SaveException.java",
             "full_content":"https://api.github.com/repos/ykhanbabaei/url-shortener/contents/src%2Fmain%2Fjava%2Forg%2Fsoftmind%2Furlshortener%2Fexception%2FSaveException.java?ref=0ba3ff92f801b3ae77407120afe1e8fe05bff349",
             "patch":"@@ -6,4 +6,8 @@ public SaveException(String message, Exception e) {\\n         super(message, e);\\n     }\\n \\n+    public SaveException(String message) {\\n+        super(message);\\n+    }\\n+\\n }",
             "status":"modified"
          },
          {
             "additions":8,
             "deletions":0,
             "filename":"src/main/java/org/softmind/urlshortener/service/UrlShortenerService.java",
             "full_content":"https://api.github.com/repos/ykhanbabaei/url-shortener/contents/src%2Fmain%2Fjava%2Forg%2Fsoftmind%2Furlshortener%2Fservice%2FUrlShortenerService.java?ref=0ba3ff92f801b3ae77407120afe1e8fe05bff349",
             "patch":"@@ -15,6 +15,7 @@\\n import org.springframework.util.StringUtils;\\n \\n import java.time.LocalDate;\\n+import java.util.Optional;\\n import java.util.UUID;\\n import java.util.concurrent.CompletableFuture;\\n \\n@@ -74,4 +75,11 @@ private String createRandomCode() {\\n         return UUID.randomUUID().toString().substring(0, URL_LEN);\\n     }\\n \\n+    public CompletableFuture<Void> unregister(String url) {\\n+        Optional<UrlShortener> urlShortener = urlShortenerRepository.findByUrl(url);\\n+        if(urlShortener.isEmpty()){\\n+            throw new NotFoundException(String.format(\\"Url not found: %s \\", url));\\n+        }\\n+        return CompletableFuture.runAsync(() -> urlShortenerRepository.delete(urlShortener.get()));\\n+    }\\n }",
             "status":"modified"
          }
       ],
       "linked_issues":[],
       "pr_metadata":{
          "author":"ykhanbabaei",
          "base_branch":"main",
          "description":"",
          "labels":[],
          "title":"Feature/unregister"
       },
       "review_comments":[]
    }'''

    # Parse it
    pr_data_dict = json.loads(json_string)
    pr_data_dict["pr_metadata"]["labels"] = []
    pr_data_dict["files_changed"] = [ChangedFile(**file) for file in pr_data_dict["files_changed"]]
    pr_data_dict["pr_metadata"] = PRMetadata(**pr_data_dict["pr_metadata"])
    return PRData(**pr_data_dict)


def data_retriever_error_handler(state: PRState, error: NodeError) -> Command:
    logger.error(f"Error in data retriever node: {error.error}")
    return Command(
        update={"error": f"Error during retrieving data: {error.error}"},
        goto=END
    )