import itertools

from narraint.entity.entity import TranslatedEntity
from narraint.queryengine.query import GraphQuery


class AnalyzedQuery(GraphQuery):

    def __init__(self, query: GraphQuery):
        super().__init__(fact_patterns=query.fact_patterns)

        self.entity2score = {}
        for fp in self.fact_patterns:
            for ent in itertools.chain(fp.subjects, fp.objects):
                if not isinstance(ent, TranslatedEntity):
                    raise TypeError(f"Expected TranslatedEntity, got {type(ent)}")

                ent_key = ent.get_unique_key()
                if ent_key not in self.entity2score:
                    self.entity2score[ent_key] = ent.translation_score
                else:
                    self.entity2score[ent_key] = max(ent.translation_score, self.entity2score[ent_key])
