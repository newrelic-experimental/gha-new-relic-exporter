from fastcore.xtras import obj2dict
from ghapi.all import GhApi


def create_github_api_client(owner, repo, token):
    return GhApi(owner=owner, repo=repo, token=str(token), sync=True)


def list_all_jobs_for_workflow_run(api, run_id, per_page=100):
    jobs = []
    total_count = None
    page = 1
    while True:
        resp = obj2dict(
            api.actions.list_jobs_for_workflow_run(run_id, page=page, per_page=per_page)
        )
        if total_count is None:
            total_count = resp.get("total_count")
        page_jobs = resp["jobs"]
        jobs.extend(page_jobs)
        if len(page_jobs) < per_page or (
            total_count is not None and len(jobs) >= total_count
        ):
            break
        page += 1
    return {"total_count": total_count, "jobs": jobs}
