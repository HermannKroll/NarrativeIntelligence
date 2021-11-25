import argparse
from pathlib import Path
from typing import List, Union

from kgextractiontoolbox.backend.models import Predication, Sentence
from kgextractiontoolbox.entitylinking.export_annotations import create_document_query, create_tag_query
from narraint.backend.database import SessionExtended
from narraint.pollux.util import iter_join, tagged_document_from_iterjoin


def export_doc_tag_pred(out_file: Union[Path, str], collection: str=None, ids: List[int]=None):
    ses = SessionExtended.get()
    doc_query = ses.execute(create_document_query(ses, collection=collection, document_ids=ids))
    tag_query = ses.execute(create_tag_query(ses, collection=collection, document_ids=ids))
    pred_query = ses.execute(ses.query(Predication, Sentence)
                             .filter(Predication.sentence_id == Sentence.id)
                             .yield_per(10_000)
                             .order_by(Predication.document_collection, Predication.document_id))
    with open(out_file, "w+") as f:
        for res in iter_join(doc_query, ["id", "collection"],
                             [tag_query, pred_query], [["document_id", "document_collection"],
                                                       ["document_id", "document_collection"]]):
            tagged_doc = tagged_document_from_iterjoin(res[:-1])
            f.write(f"{tagged_doc}")
            last_s_id = None
            for p in res[2]:
                p, s = p._data
                if p.sentence_id != last_s_id:
                    f.write(f"Sentence {p.sentence_id}: {s.text}\n")
                    last_s_id = p.sentence_id
                f.write(f"<{p.subject_str}({p.subject_type})> {p.predicate} <{p.object_str}({p.object_type})>\n")
            if res[2]:
                f.write("\n")
            f.write("\n")



def main(args=None):
    parser = argparse.ArgumentParser("Export documents from database with tags and predications")
    parser.add_argument("-c", "--collection", help="Document collection")
    parser.add_argument("-i", "--ids", help="Document ids", nargs="*")
    parser.add_argument("output", help="output file")
    args = parser.parse_args(args)

    export_doc_tag_pred(args.output, collection=args.collection, ids=args.ids)


if __name__ == '__main__':
    main()
