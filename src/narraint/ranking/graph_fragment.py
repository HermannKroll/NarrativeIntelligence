from tqdm.contrib import itertools

from narraint.queryengine.expander import QueryExpander
from narraint.queryengine.query_hints import DO_NOT_CARE_PREDICATE
from narraint.ranking.indexed_document import IndexedDocument, ScoredDocumentStatement
from narraint.ranking.query import AnalyzedQuery


class GraphFragment:

    def __init__(self, statements: [ScoredDocumentStatement]):
        self.statements = statements

    def __getitem__(self, item):
        return self.statements[item]

    def __len__(self):
        return len(self.statements)


class GraphFragmentExtractor:

    @staticmethod
    def matches(query: AnalyzedQuery, document: IndexedDocument) -> [GraphFragment]:
        """
        Computes all distinct subgraph isomorphism between the query q and the document graph of d.
        Each subgraph isomorphism maps a part of the document graph to the query.
        Note that if q asks for two statements, each isomorphism must map two document edges to the
        corresponding query graph edges.

        Given two statements in a query:
        stmt1 maps to which edges of the document graph g? -> given by query engine through predication ids
        stmt2 maps to which edges of the document graph g? -> given by query engine through predication ids
        Cross product between all combinations
        """

        fp2statements = {}

        # query for each fact pattern
        for index, fp in enumerate(query.fact_patterns):
            fp2statements[index] = list()

            subject_ids = set(s.entity_id for s in fp.subjects)
            subject_types = set(s.entity_type for s in fp.subjects)
            predicates = {fp.predicate}
            object_ids = set(o.entity_id for o in fp.objects)
            object_types = set(o.entity_type for o in fp.objects)

            for expanded_fp in QueryExpander.expand_fact_pattern(fp):
                subject_ids.update(s.entity_id for s in expanded_fp.subjects)
                subject_types.update((s.entity_type for s in expanded_fp.subjects))
                predicates.add(expanded_fp.predicate)
                object_ids.update(o.entity_id for o in expanded_fp.objects)
                object_types.update(o.entity_type for o in expanded_fp.objects)

            # ignore predicate when type equals "associated"
            ignore_predicate = (len(predicates) == 1 and list(predicates)[0] == DO_NOT_CARE_PREDICATE)

            # match fact patterns against the scored statements
            # it is enough to match against scored^ statements because they are the only ones relevant for ranking
            for s in document.scored_statements:
                if (s.subject_id in subject_ids and s.subject_type in subject_types
                        and s.object_id in object_ids and s.object_type in object_types
                        and (ignore_predicate or s.relation in predicates)):
                    fp2statements[index].append(s)

        # now we need to compute the cross product
        # cross-product over all statements
        fragments = list(itertools.product(*[v for v in fp2statements.values()]))

        # remove duplicated fragments
        fragments = list(set(fragments))

        return [GraphFragment(f) for f in fragments]
