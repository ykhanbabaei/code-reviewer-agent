import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.state import PRState, PRData, ChangedFile, PRMetadata


@pytest.mark.asyncio
async def test_file_reviewer_node(mocker):
    # all valid calls
    mock_agent = MagicMock()

    async def mock_ainvoke(arg):
        return {
            "structured_response": mocker.MagicMock(
            model_dump=mocker.MagicMock(return_value={"review": "LGTM!"})
        )}

    mock_agent.ainvoke = AsyncMock(side_effect=mock_ainvoke)

    mocker.patch('app.agents.nodes.file_reviewer_node.create_agent', return_value=mock_agent)

    pr_data = mock_build_pr_data_from()
    changed_files = [
        f for f in pr_data.files_changed
    ]

    state = PRState(
        current_file_index=0,
        files_to_review=changed_files,
        pr_data=pr_data,
    )

    from app.agents.nodes.file_reviewer_node import file_reviewer_node
    result = await file_reviewer_node(state, MagicMock())
    mock_agent.ainvoke.assert_called_once()
    assert result.update["current_file_index"] == 1
    assert result.update["file_reviews"][0]["review"]["review"] == "LGTM!"
    assert result.goto == "file_reviewer_node"
    print(result)


def mock_build_pr_data_from() -> PRData:
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
    pr_data_dict = json.loads(json_string)
    pr_data_dict["pr_metadata"]["labels"] = []
    pr_data_dict["files_changed"] = [ChangedFile(**file) for file in pr_data_dict["files_changed"]]
    pr_data_dict["pr_metadata"] = PRMetadata(**pr_data_dict["pr_metadata"])
    return PRData(**pr_data_dict)
