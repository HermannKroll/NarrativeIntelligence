import ast

from kgextractiontoolbox.progress import Progress
from narraint.backend.database import SessionExtended
from narraint.backend.models import EntityKeywords


STOPWORD_COUNT = 200


def retrieve_keyword_list(entity_type: str="Drug") -> list[str]:
    """
    Function extracts the top STOPWORD_COUNT words contained in the table
    EntityKeywords

    @param entity_type: str
    @return: list[str]
    """
    keyword_list = dict()
    session = SessionExtended.get()
    try:

        q = session.query(EntityKeywords.keyword_data)
        q = q.filter(EntityKeywords.entity_type == entity_type)

        keyword_strings = q.all()
        idx = 0
        p = Progress(total=len(keyword_strings))
        p.start_time()

        for keyword_string in keyword_strings:
            keywords = ast.literal_eval(keyword_string[0])

            for keyword in keywords:
                key = list(keyword.keys())[0]

                if not key in keyword_list:
                    keyword_list[key] = 1
                else:
                    keyword_list[key] += 1
            idx += 1
            p.print_progress(idx)
        p.done()

        sorted_top_hundred = sorted(
            keyword_list.items(),
            key=lambda x: x[1],
            reverse=True)[:STOPWORD_COUNT]

        keyword_list = [kw[0] for kw in sorted_top_hundred]

    except Exception as e:
        print(e)
        session.remove()
        exit(-1)
    finally:
        session.remove()

    return keyword_list


def main(file_name):
    keywords = retrieve_keyword_list()

    with open(file_name, "w") as file:
        file.write('\n'.join(keywords))
        file.close()


if __name__ == "__main__":
    main("stopword_list.txt")