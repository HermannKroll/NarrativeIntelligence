import os


def get_matomo_credentials(request):
    base_url = os.environ.get("MATOMO_BASE_URL")
    side_id_search = os.environ.get("MATOMO_SIDE_ID_SEARCH")
    side_id_overview = os.environ.get("MATOMO_SIDE_ID_OVERVIEW")

    return {
        "MATOMO_BASE_URL": base_url,
        "MATOMO_SIDE_ID_SEARCH": side_id_search,
        "MATOMO_SIDE_ID_OVERVIEW": side_id_overview,
    }