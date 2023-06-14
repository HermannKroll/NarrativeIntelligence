from eldar import Query

from narraint.queryengine.result import QueryDocumentResult


class TitleFilter:

    @staticmethod
    def filter_documents(results: [QueryDocumentResult], search_str: str):
        if not search_str or not search_str.strip():
            return results
        else:
            # match word will have the same effect
            search_str = search_str.replace('*', '')
            eldar_q = Query(search_str, match_word=False)
            return list([r for r in results if eldar_q(r.title)])


