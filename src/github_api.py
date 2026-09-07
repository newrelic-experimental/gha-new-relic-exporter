from ghapi.all import GhApi


def create_github_api_client(owner, repo, token):
    return GhApi(owner=owner, repo=repo, token=str(token), sync=True)
