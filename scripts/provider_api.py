"""Direct provider APIs, urllib only. Normalized contract is shared with JSON bridges.

Writes have no automatic HTTP retries. Ambiguous failures are reconciled by the
migration journal using remote operation markers before a later resume.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import html
import ipaddress
import socket

from integration_core import digest, normalize, rich_text


def quote(value):
    return urllib.parse.quote(str(value), safe="")


def adf(value):
    return {"version": 1, "type": "doc", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": line}]} if line else {"type": "paragraph", "content": []}
        for line in value.split("\n")]}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward provider credentials to an attachment/CDN redirect.
        return None


class APIError(RuntimeError):
    def __init__(self, provider, status):
        self.status = status
        super().__init__(f"{provider} HTTP {status}; response body withheld")


class API:
    mode = "api"

    def __init__(self, name, config, writing=False):
        self.name, self.config, self.writing = name, config, writing
        self.provider = config["provider"]
        defaults = {"github": "https://api.github.com", "github-actions": "https://api.github.com",
                    "jira": "", "gitlab": "https://gitlab.com", "linear": "https://api.linear.app",
                    "azure-devops": "https://dev.azure.com"}
        self.base = config.get("base_url", defaults[self.provider]).rstrip("/")
        if not self.base.startswith("https://"):
            raise ValueError("API base_url must use HTTPS")
        token = os.environ.get(config.get("token_env", ""))
        if not token:
            raise ValueError("token_env does not reference a populated environment variable")
        self.headers = {"Accept": "application/json", "User-Agent": "project-docs/1"}
        if self.provider == "gitlab":
            self.headers["PRIVATE-TOKEN"] = token
        elif self.provider == "azure-devops" or (self.provider == "jira" and config.get("username_env")):
            username = os.environ.get(config.get("username_env", ""), "")
            self.headers["Authorization"] = "Basic " + base64.b64encode(f"{username}:{token}".encode()).decode()
        elif self.provider == "linear" and config.get("auth") != "bearer":
            self.headers["Authorization"] = token
        else:
            self.headers["Authorization"] = "Bearer " + token
        if self.provider == "linear":
            self.headers["public-file-urls-expire-in"] = "600"
        if self.provider in {"github", "github-actions"}:
            self.headers["X-GitHub-Api-Version"] = "2022-11-28"
        self.opener = urllib.request.build_opener(NoRedirect())

    def asset(self, url, data=None, headers=None):
        """Credential-free asset transfers; validate every redirect destination."""
        for _ in range(6):
            parts = urllib.parse.urlsplit(url)
            if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
                raise ValueError("unsafe asset URL")
            allowed = self.config.get("asset_hosts", [])
            if parts.hostname not in allowed:
                addresses = socket.getaddrinfo(parts.hostname, parts.port or 443, type=socket.SOCK_STREAM)
                if not addresses or any(not ipaddress.ip_address(r[4][0]).is_global for r in addresses):
                    raise ValueError("asset host resolves to a private address; configure asset_hosts explicitly for trusted internal storage")
            try:
                req = urllib.request.Request(url, data=data, headers=headers or {}, method="PUT" if data is not None else "GET")
                with self.opener.open(req, timeout=self.config.get("timeout", 30)) as response:
                    return response.read(), dict(response.headers)
            except urllib.error.HTTPError as exc:
                if data is None and exc.code in {301, 302, 303, 307, 308}:
                    url = urllib.parse.urljoin(url, exc.headers.get("Location", ""))
                    continue
                raise RuntimeError(f"asset transfer HTTP {exc.code}") from None
        raise ValueError("too many asset redirects")

    def request(self, method, path, body=None, content_type=None, binary=False, safe=False):
        url = path if path.startswith("https://") else self.base + path
        if urllib.parse.urlsplit(url).netloc != urllib.parse.urlsplit(self.base).netloc:
            raise ValueError("refusing to send API credentials to another host")
        headers = dict(self.headers)
        data = body
        if body is not None and not isinstance(body, bytes):
            data = json.dumps(body).encode()
            content_type = content_type or "application/json"
        if content_type:
            headers["Content-Type"] = content_type
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method=method)
                with self.opener.open(req, timeout=self.config.get("timeout", 30)) as result:
                    raw = result.read()
                    return (raw if binary else json.loads(raw) if raw else {}), dict(result.headers)
            except urllib.error.HTTPError as exc:
                if exc.code in {301, 302, 303, 307, 308} and binary:
                    target = exc.headers.get("Location", "")
                    if not target.startswith("https://"):
                        raise RuntimeError("unsafe attachment redirect") from None
                    # Signed CDN URL: credentials are intentionally omitted.
                    return self.asset(target)
                if (method == "GET" or safe) and exc.code in {429, 502, 503, 504} and attempt < 3:
                    delay = exc.headers.get("Retry-After", "")
                    delay = float(delay) if delay.replace(".", "", 1).isdigit() else 2 ** attempt
                    if delay > 30:
                        raise RuntimeError("rate limit requires a later retry") from None
                    time.sleep(delay)
                    continue
                raise APIError(self.provider, exc.code) from None
        raise RuntimeError("request retries exhausted")

    def json(self, method, path, body=None, **kwargs):
        return self.request(method, path, body, **kwargs)[0]

    def pages(self, path, key=None):
        records, seen = [], set()
        while path:
            if path in seen:
                raise ValueError("pagination cycle")
            seen.add(path)
            data, headers = self.request("GET", path)
            rows = data.get(key, []) if key else data
            if not isinstance(rows, list):
                raise ValueError("malformed paginated response")
            records.extend(rows)
            links = headers.get("Link", headers.get("link", ""))
            import re
            nxt = re.search(r'<([^>]+)>; rel="next"', links)
            page = headers.get("X-Next-Page", headers.get("x-next-page"))
            if nxt:
                path = nxt[1]
            elif page:
                split = urllib.parse.urlsplit(path)
                query = dict(urllib.parse.parse_qsl(split.query)); query["page"] = page
                path = urllib.parse.urlunsplit(split._replace(query=urllib.parse.urlencode(query)))
            else:
                path = None
        return records

    def graph(self, query, variables=None):
        data = self.json("POST", "/graphql", {"query": query, "variables": variables or {}}, safe=not query.lstrip().startswith("mutation"))
        if data.get("errors"):
            raise RuntimeError("Linear GraphQL operation failed; provider errors withheld")
        if query.lstrip().startswith("mutation") and any(isinstance(v, dict) and v.get("success") is False for v in data.get("data", {}).values()):
            raise RuntimeError("Linear mutation reported failure")
        return data["data"]

    def graph_nodes(self, field, fields, args="", variables=None):
        result, cursor = [], None
        while True:
            decl = "$after: String" + (", $team: ID!" if "$team" in args else "")
            page = self.graph(f"query({decl}) {{ {field}(first: 100, after: $after{', ' + args if args else ''}) {{ nodes {{ {fields} }} pageInfo {{ hasNextPage endCursor }} }} }}",
                              {**(variables or {}), "after": cursor})[field]
            result.extend(page["nodes"])
            if not page["pageInfo"]["hasNextPage"]:
                return result
            next_cursor = page["pageInfo"]["endCursor"]
            if not next_cursor or next_cursor == cursor:
                raise ValueError("invalid Linear pagination cursor")
            cursor = next_cursor

    def prefix(self):
        if self.provider in {"github", "github-actions"}:
            owner, repo = self.config["repository"].split("/", 1)
            return f"/repos/{quote(owner)}/{quote(repo)}"
        if self.provider == "gitlab":
            return "/api/v4/projects/" + quote(self.config["project"])
        if self.provider == "azure-devops":
            return f"/{quote(self.config['organization'])}/{quote(self.config['project'])}/_apis/wit"
        return "/rest/api/3"

    def call(self, operation, **p):
        from integration_transport import READ_OPERATIONS
        if operation not in READ_OPERATIONS and not self.writing:
            raise ValueError("writes require migration apply/resume")
        if operation == "download":
            url = p["url"]
            if not url.startswith("https://"):
                raise ValueError("attachment download must use HTTPS")
            if urllib.parse.urlsplit(url).netloc == urllib.parse.urlsplit(self.base).netloc:
                data = self.request("GET", url, binary=True)[0]
            else:
                # External linked assets receive no provider credentials.
                data = self.asset(url)[0]
            return {"base64": base64.b64encode(data).decode(), "sha256": digest(data)}
        handler = getattr(self, "op_" + operation, None)
        if handler is None:
            raise ValueError(f"unsupported operation: {operation}")
        return handler(**p)

    def op_doctor(self):
        schema = self.op_schema()
        caps = ["list", "get", "schema", "find", "download"]
        if self.provider != "github-actions":
            caps += ["create", "configure", "comment", "comments"]
        if self.provider not in {"github", "github-actions"}:
            caps += ["attach"]
        if self.provider in {"azure-devops", "jira", "linear", "github"}:
            caps += ["parent"]
        return {"capabilities": caps, "read_access": True, "write_access": "unverified until write",
                "schema": schema}

    def op_schema(self):
        p = self.prefix()
        if self.provider == "github-actions":
            self.json("GET", p + "/actions/artifacts?per_page=1")
            return {"types": [], "states": [], "labels": [], "users": []}
        if self.provider in {"github", "github-actions"}:
            repo = self.json("GET", p)
            return {"types": ["Issue"], "states": ["open", "closed"],
                    "labels": [r["name"] for r in self.pages(p + "/labels?per_page=100")],
                    "users": [r["login"] for r in self.pages(p + "/assignees?per_page=100")],
                    "permissions": repo.get("permissions", {})}
        if self.provider == "gitlab":
            self.json("GET", p)
            return {"types": ["Issue"], "states": ["opened", "closed"],
                    "labels": [r["name"] for r in self.pages(p + "/labels?per_page=100")],
                    "users": [str(r["id"]) for r in self.pages(p + "/members/all?per_page=100")]}
        if self.provider == "azure-devops":
            types = self.json("GET", p + "/workitemtypes?api-version=7.1")["value"]
            states = sorted({s["name"] for t in types for s in t.get("states", [])})
            return {"types": [t["name"] for t in types], "states": states, "users": [], "labels": [], "free_labels": True}
        if self.provider == "jira":
            project = self.json("GET", p + "/project/" + quote(self.config["project"]))
            states = self.json("GET", p + "/project/" + quote(self.config["project"]) + "/statuses")
            return {"types": [t["name"] for t in project["issueTypes"]],
                    "parent_types": [t["name"] for t in project["issueTypes"] if t.get("subtask")],
                    "states": sorted({s["name"] for t in states for s in t["statuses"]}),
                    "users": [], "labels": [], "free_labels": True}
        team = self.config["team"]
        data = self.graph("query($id: String!) { team(id: $id) { id states { nodes { id name } } labels { nodes { id name } } members { nodes { id name email } } } }", {"id": team})["team"]
        return {"types": ["Issue"], "states": [s["name"] for s in data["states"]["nodes"]],
                "state_ids": {s["name"]: s["id"] for s in data["states"]["nodes"]},
                "labels": [l["name"] for l in data["labels"]["nodes"]],
                "label_ids": {l["name"]: l["id"] for l in data["labels"]["nodes"]},
                "users": [u["id"] for u in data["members"]["nodes"]]}

    def op_list(self, full=False):
        p = self.prefix()
        if self.provider == "github":
            values = self.pages(p + "/issues?state=all&per_page=100")
            for index, item in enumerate(values):
                if item.get("pull_request"):
                    pull = self.json("GET", p + "/pulls/" + str(item["number"]))
                    pull["pull_request"] = item["pull_request"]
                    values[index] = pull
        elif self.provider == "github-actions":
            values = self.pages(p + "/actions/artifacts?per_page=100", "artifacts")
        elif self.provider == "gitlab":
            values = self.pages(p + "/issues?scope=all&per_page=100")
            values += [{**r, "kind": "change_request"} for r in self.pages(p + "/merge_requests?scope=all&per_page=100")]
        elif self.provider == "azure-devops":
            # WIQL query is read-only POST. Fail on service query limits rather than claim completeness.
            query = {"query": "SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project ORDER BY [System.Id]"}
            ids = self.json("POST", p + "/wiql?api-version=7.1", query, safe=True)["workItems"]
            values = []
            for start in range(0, len(ids), 200):
                batch = self.json("POST", p + "/workitemsbatch?api-version=7.1", {"ids": [i["id"] for i in ids[start:start+200]], "$expand": "All"}, safe=True)
                values.extend(batch["value"])
        elif self.provider == "jira":
            values, token = [], None
            while True:
                body = {"jql": 'project = "' + self.config["project"].replace('"', '\\"') + '" ORDER BY id', "maxResults": 100, "fields": ["*all"]}
                if token:
                    body["nextPageToken"] = token
                page = self.json("POST", p + "/search/jql", body, safe=True)
                values.extend(page["issues"])
                nxt = page.get("nextPageToken")
                if page.get("isLast", not nxt):
                    break
                if not nxt or token == nxt:
                    raise ValueError("invalid Jira pagination token")
                token = nxt
        else:
            fields = "id identifier title description url state { name } parent { id } assignee { id name email } labels { nodes { id name } }"
            values = self.graph_nodes("issues", fields, "filter: { team: { id: { eq: $team } } }", {"team": self.config["team"]})
        snap = normalize(self.name, self.config, values, coverage="complete")
        if full and self.provider != "github-actions":
            snap["items"] = [self.op_get(id=i["id"], raw=i["raw"]) if i["kind"] == "work_item" else i for i in snap["items"]]
        return snap

    def op_get(self, id, raw=None):
        p = self.prefix()
        if self.provider == "github-actions":
            raw = raw or self.json("GET", p + "/actions/artifacts/" + quote(id))
            return normalize(self.name, self.config, [raw])["items"][0]
        if raw is None:
            if self.provider == "github":
                raw = self.json("GET", p + "/issues/" + quote(id))
            elif self.provider == "gitlab":
                raw = self.json("GET", p + "/issues/" + quote(id))
            elif self.provider == "jira":
                raw = self.json("GET", p + "/issue/" + quote(id) + "?fields=*all")
            elif self.provider == "azure-devops":
                raw = self.json("GET", p + "/workitems/" + quote(id) + "?$expand=All&api-version=7.1")
            else:
                raw = self.graph("query($id: String!) { issue(id: $id) { id identifier title description url state { name } parent { id } assignee { id name email } labels { nodes { id name } } } }", {"id": str(id)})["issue"]
        item = normalize(self.name, self.config, [raw])["items"][0]
        item["comments"] = self.op_comments(id)
        if self.provider == "github":
            try:
                parent = self.json("GET", p + "/issues/" + quote(id) + "/parent")
                same_repo = parent.get("repository_url", "").rstrip("/").lower() == (self.base + p).lower()
                item["parent"] = str(parent["number"]) if same_repo else "external:" + parent.get("html_url", str(parent["id"]))
            except APIError as exc:
                if exc.status != 404:
                    raise
        if self.provider == "azure-devops":
            item["attachments"] = [{"id": str(n), "url": r["url"], "name": r.get("attributes", {}).get("name", "attachment")}
                                   for n, r in enumerate(raw.get("relations", [])) if r["rel"] == "AttachedFile"]
            parents = [r for r in raw.get("relations", []) if r["rel"] == "System.LinkTypes.Hierarchy-Reverse"]
            item["parent"] = parents[0]["url"].rsplit("/", 1)[-1] if parents else None
        elif self.provider == "linear":
            # Linked Linear attachments are external URLs, not embedded bytes.
            nodes, cursor = [], None
            while True:
                page = self.graph("query($id: String!, $after: String) { issue(id: $id) { attachments(first: 100, after: $after) { nodes { id title url } pageInfo { hasNextPage endCursor } } } }", {"id": str(id), "after": cursor})["issue"]["attachments"]
                nodes.extend(page["nodes"])
                if not page["pageInfo"]["hasNextPage"]:
                    break
                nxt = page["pageInfo"]["endCursor"]
                if not nxt or nxt == cursor:
                    raise ValueError("invalid attachments cursor")
                cursor = nxt
            item["attachments"] = [{"id": n["id"], "name": n["title"], "url": n["url"]} for n in nodes]
            item["labels"] = [l["name"] for l in raw.get("labels", {}).get("nodes", [])]
        # Images/uploads embedded in markdown remain part of the description;
        # inventory them so migration cannot silently leave private source URLs behind.
        if self.provider in {"github", "gitlab", "linear"}:
            import re
            urls = re.findall(r'!?\[[^\]]*\]\(([^)\s]+)\)', item["description"] + "\n" + "\n".join(c["body"] for c in item["comments"]))
            for url in dict.fromkeys(urls):
                if "/uploads/" in url or "github.com/user-attachments/" in url or "uploads.linear.app/" in url:
                    absolute = urllib.parse.urljoin(self.base + "/", url)
                    if self.provider == "gitlab" and urllib.parse.urlsplit(absolute).netloc == urllib.parse.urlsplit(self.base).netloc:
                        uploaded = re.search(r"/uploads/([^/]+)/(.+)$", urllib.parse.urlsplit(absolute).path)
                        if uploaded:
                            absolute = self.base + p + "/uploads/" + uploaded[1] + "/" + uploaded[2]
                    item["attachments"].append({"id": digest(url), "name": url.rsplit("/", 1)[-1], "url": absolute, "source_link": url})
        item["full"] = True
        return item

    def op_comments(self, id):
        p = self.prefix()
        if self.provider == "github":
            rows = self.pages(p + "/issues/" + quote(id) + "/comments?per_page=100")
        elif self.provider == "gitlab":
            rows = [r for r in self.pages(p + "/issues/" + quote(id) + "/notes?per_page=100&sort=asc") if not r.get("system")]
        elif self.provider == "jira":
            rows, start = [], 0
            while True:
                page = self.json("GET", p + "/issue/" + quote(id) + f"/comment?startAt={start}&maxResults=100")
                rows.extend(page["comments"]); start += len(page["comments"])
                if start >= page["total"]:
                    break
                if not page["comments"]:
                    raise ValueError("incomplete comment pagination")
        elif self.provider == "azure-devops":
            rows, cursor = [], None
            while True:
                url = p + "/workitems/" + quote(id) + "/comments?api-version=7.1-preview.4"
                if cursor:
                    url += "&continuationToken=" + quote(cursor)
                page = self.json("GET", url)
                rows.extend(page.get("comments", []))
                nxt = page.get("continuationToken")
                if not nxt:
                    break
                if nxt == cursor:
                    raise ValueError("invalid comments token")
                cursor = nxt
        else:
            rows, cursor = [], None
            while True:
                page = self.graph("query($id: String!, $after: String) { issue(id: $id) { comments(first: 100, after: $after) { nodes { id body createdAt user { id name } } pageInfo { hasNextPage endCursor } } } }", {"id": str(id), "after": cursor})["issue"]["comments"]
                rows.extend(page["nodes"])
                if not page["pageInfo"]["hasNextPage"]:
                    break
                nxt = page["pageInfo"]["endCursor"]
                if not nxt or nxt == cursor:
                    raise ValueError("invalid comments cursor")
                cursor = nxt
        return [{"id": str(r.get("id", r.get("commentId"))), "body": rich_text(r.get("body", r.get("text", ""))),
                 "author": r.get("user", r.get("author", r.get("createdBy", {}))),
                 "created": r.get("created_at", r.get("created", r.get("createdAt", r.get("createdDate")))), "raw": r} for r in rows]

    def op_find(self, marker, kind="item", item_id=None):
        if kind == "comment":
            return [c for c in self.op_comments(item_id) if marker in c["body"]]
        if kind == "attachment":
            item = self.op_get(item_id)
            return [a for a in item["attachments"] if marker in a.get("name", a.get("filename", ""))]
        return [i for i in self.op_list()["items"] if marker in i.get("description", "")]

    def op_create(self, item, marker):
        p = self.prefix()
        body = item["description"] + "\n\n" + marker
        if self.provider == "github":
            raw = self.json("POST", p + "/issues", {"title": item["title"], "body": body})
        elif self.provider == "gitlab":
            raw = self.json("POST", p + "/issues", {"title": item["title"], "description": body})
        elif self.provider == "jira":
            fields = {"project": {"key": self.config["project"]}, "issuetype": {"name": item["type"]}, "summary": item["title"], "description": adf(body)}
            if item.get("parent_id"):
                fields["parent"] = {"id": str(item["parent_id"])}
            raw = self.json("POST", p + "/issue", {"fields": fields})
        elif self.provider == "azure-devops":
            raw = self.json("POST", p + "/workitems/$" + quote(item["type"]) + "?api-version=7.1", [
                {"op": "add", "path": "/fields/System.Title", "value": item["title"]},
                {"op": "add", "path": "/fields/System.Description", "value": html.escape(body).replace("\n", "<br>")}], content_type="application/json-patch+json")
        else:
            raw = self.graph("mutation($input: IssueCreateInput!) { issueCreate(input: $input) { success issue { id } } }", {"input": {"teamId": self.config["team"], "title": item["title"], "description": body}})["issueCreate"]
            if not raw.get("success"):
                raise RuntimeError("Linear create failed")
            raw = raw["issue"]
        external = raw.get("number", raw.get("iid", raw.get("id")))
        if external is None:
            raise ValueError("create response has no external ID")
        return {"id": str(external)}

    def op_configure(self, id, item):
        p = self.prefix()
        labels = item.get("labels", [])
        user = item.get("assignee")
        if self.provider == "github":
            body = {"state": item["raw_state"], "labels": labels, "assignees": [user] if user else [], "body": item["description"]}
            self.json("PATCH", p + "/issues/" + quote(id), body)
        elif self.provider == "gitlab":
            self.json("PUT", p + "/issues/" + quote(id), {"state_event": "close" if item["raw_state"] == "closed" else "reopen", "labels": ",".join(labels), "assignee_ids": [int(user)] if user else [], "description": item["description"]})
        elif self.provider == "azure-devops":
            fields = {"System.State": item["raw_state"], "System.Tags": "; ".join(labels), "System.Description": html.escape(item["description"]).replace("\n", "<br>")}
            if user:
                fields["System.AssignedTo"] = user
            self.json("PATCH", p + "/workitems/" + quote(id) + "?api-version=7.1", [{"op": "add", "path": "/fields/"+k, "value": v} for k, v in fields.items()], content_type="application/json-patch+json")
        elif self.provider == "jira":
            fields = {"labels": labels, "description": adf(item["description"])}
            if user:
                fields["assignee"] = {"accountId": user}
            self.json("PUT", p + "/issue/" + quote(id), {"fields": fields})
            current = self.op_get(id)
            if current["raw_state"] != item["raw_state"]:
                transitions = self.json("GET", p + "/issue/" + quote(id) + "/transitions")["transitions"]
                target = next((t for t in transitions if t["to"]["name"] == item["raw_state"]), None)
                if not target:
                    raise ValueError("destination status has no available direct transition")
                self.json("POST", p + "/issue/" + quote(id) + "/transitions", {"transition": {"id": target["id"]}})
        else:
            schema = self.op_schema()
            body = {"stateId": schema["state_ids"][item["raw_state"]], "labelIds": [schema["label_ids"][l] for l in labels], "description": item["description"]}
            if user:
                body["assigneeId"] = user
            self.graph("mutation($id: String!, $input: IssueUpdateInput!) { issueUpdate(id: $id, input: $input) { success } }", {"id": str(id), "input": body})
        return {"id": str(id)}

    def op_comment(self, id, body, marker):
        p = self.prefix(); body += "\n\n" + marker
        if self.provider == "github":
            result = self.json("POST", p + "/issues/" + quote(id) + "/comments", {"body": body})
        elif self.provider == "gitlab":
            result = self.json("POST", p + "/issues/" + quote(id) + "/notes", {"body": body})
        elif self.provider == "jira":
            result = self.json("POST", p + "/issue/" + quote(id) + "/comment", {"body": adf(body)})
        elif self.provider == "azure-devops":
            result = self.json("POST", p + "/workitems/" + quote(id) + "/comments?format=markdown&api-version=7.1-preview.4", {"text": body})
        else:
            result = self.graph("mutation($input: CommentCreateInput!) { commentCreate(input: $input) { success comment { id } } }", {"input": {"issueId": str(id), "body": body}})["commentCreate"]["comment"]
        external = result.get("id", result.get("commentId"))
        if external is None:
            raise ValueError("comment response has no external ID")
        return {"id": str(external)}

    def op_parent(self, id, parent_id):
        p = self.prefix()
        if self.provider == "azure-devops":
            parent_url = self.base + p + "/workitems/" + quote(parent_id)
            item = self.op_get(id)
            if item.get("parent") != str(parent_id):
                self.json("PATCH", p + "/workitems/" + quote(id) + "?api-version=7.1", [{"op": "add", "path": "/relations/-", "value": {"rel": "System.LinkTypes.Hierarchy-Reverse", "url": parent_url}}], content_type="application/json-patch+json")
        elif self.provider == "jira":
            self.json("PUT", p + "/issue/" + quote(id), {"fields": {"parent": {"id": str(parent_id)}}})
        elif self.provider == "linear":
            self.graph("mutation($id: String!, $input: IssueUpdateInput!) { issueUpdate(id: $id, input: $input) { success } }", {"id": str(id), "input": {"parentId": str(parent_id)}})
        elif self.provider == "github":
            child = self.json("GET", p + "/issues/" + quote(id))
            current = self.op_get(id)
            if current.get("parent") != str(parent_id):
                self.json("POST", p + "/issues/" + quote(parent_id) + "/sub_issues", {"sub_issue_id": child["id"]})
        else:
            raise ValueError("native parent relationships unsupported by this API adapter")
        return {"id": str(id), "parent": str(parent_id)}

    def op_attach(self, id, name, base64_data, marker):
        data = base64.b64decode(base64_data, validate=True)
        name = marker + "-" + name.replace("/", "_").replace("\\", "_").replace('"', "_").replace("\r", "").replace("\n", "")
        p = self.prefix()
        if self.provider == "azure-devops":
            attachment = self.json("POST", p + "/attachments?fileName=" + quote(name) + "&api-version=7.1", data, content_type="application/octet-stream")
            self.json("PATCH", p + "/workitems/" + quote(id) + "?api-version=7.1", [{"op": "add", "path": "/relations/-", "value": {"rel": "AttachedFile", "url": attachment["url"], "attributes": {"name": name}}}], content_type="application/json-patch+json")
            return {"id": str(attachment["id"]), "name": name, "url": attachment["url"]}
        if self.provider == "linear":
            upload = self.graph("mutation($name: String!, $size: Int!, $type: String!) { fileUpload(filename: $name, size: $size, contentType: $type) { success uploadFile { uploadUrl assetUrl headers { key value } } } }", {"name": name, "size": len(data), "type": mimetypes.guess_type(name)[0] or "application/octet-stream"})["fileUpload"]
            if not upload.get("success"):
                raise RuntimeError("Linear upload negotiation failed")
            file = upload["uploadFile"]
            headers = {"Content-Type": mimetypes.guess_type(name)[0] or "application/octet-stream", "Cache-Control": "public, max-age=31536000"}
            headers.update({h["key"]: h["value"] for h in file["headers"]})
            self.asset(file["uploadUrl"], data=data, headers=headers)
            result = self.graph("mutation($input: AttachmentCreateInput!) { attachmentCreate(input: $input) { success attachment { id url title } } }", {"input": {"issueId": str(id), "title": name, "url": file["assetUrl"]}})["attachmentCreate"]["attachment"]
            return {"id": result["id"], "url": result["url"], "name": name}
        if self.provider not in {"jira", "gitlab"}:
            raise ValueError("no supported attachment upload endpoint; use a capable MCP/CLI bridge or accept an archived-only limitation")
        boundary = "projectdocs" + uuid.uuid4().hex
        field = "file"
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode() + data + f"\r\n--{boundary}--\r\n".encode()
        if self.provider == "jira":
            self.headers["X-Atlassian-Token"] = "no-check"
            result = self.json("POST", p + "/issue/" + quote(id) + "/attachments", body, content_type="multipart/form-data; boundary="+boundary)[0]
            return {"id": str(result["id"]), "name": result["filename"], "url": result["content"]}
        result = self.json("POST", p + "/uploads", body, content_type="multipart/form-data; boundary="+boundary)
        # GitLab uploads are linked from an issue note, making them discoverable after timeout.
        url = result.get("full_path", result["url"])
        self.op_comment(id, result["markdown"], marker)
        return {"id": str(result.get("id", marker)), "name": name, "url": urllib.parse.urljoin(self.base, url)}

    def op_artifact(self, id, attempt=None):
        p = self.prefix()
        artifact = self.json("GET", p + "/actions/artifacts/" + quote(id))
        path = p + "/actions/runs/" + str(artifact["workflow_run"]["id"])
        run = self.json("GET", path + ("/attempts/"+quote(attempt) if attempt else ""))
        from datetime import datetime
        created = datetime.fromisoformat(artifact["created_at"].replace("Z", "+00:00"))
        started = datetime.fromisoformat(run["run_started_at"].replace("Z", "+00:00"))
        ended = datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00"))
        if not started <= created <= ended or artifact["workflow_run"].get("head_sha") != run["head_sha"]:
            raise ValueError("artifact cannot be attributed to this run attempt and commit; specify the original attempt")
        return {"artifact_id": str(id), "run_id": str(run["id"]), "attempt": run["run_attempt"],
                "commit_sha": run["head_sha"], "conclusion": run.get("conclusion"),
                "expired": artifact["expired"], "attempt_verified": True, "download_url": artifact["archive_download_url"], "raw": artifact}
