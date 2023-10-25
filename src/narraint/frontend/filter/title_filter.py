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
            search_str = search_str.strip()

            # remove duplicated white spaces
            while '  ' in search_str:
                search_str = search_str.replace('  ', ' ')

            # only replace space by and if boolean operators are not explicitly searched
            if ' and ' not in search_str and ' or ' not in search_str:
                search_str = search_str.replace(' ', ' and ')

            search_str = search_str.replace('+', ' ')
            search_str = search_str.strip()
            print(search_str)
            eldar_q = Query(search_str, match_word=False, ignore_case=True)
            return list([r for r in results if eldar_q(r.title)])


