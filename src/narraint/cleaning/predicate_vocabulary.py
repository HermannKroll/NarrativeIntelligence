import csv
import re
from collections import defaultdict


class RelationVocabulary:

    def __init__(self):
        self.relation_dict = defaultdict(set)

    def load_from_tsv_file(self, relation_vocab_file: str):
        self.relation_dict.clear()
        with open(relation_vocab_file, 'rt') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for line in reader:
                relation = line['relation']
                synonyms = line['synonyms']
                for s in synonyms.split(';'):
                    self.relation_dict[relation.strip()].add(s.strip())
        self._verify_integrity()

    def _verify_integrity(self):
        star_regex = re.compile(r'\w\*\w')
        for relation, synonyms in self.relation_dict.items():
            if '*' in relation:
                raise ValueError(f'* are not allowed in a relation (found {relation})')
            for syn in synonyms:
                if star_regex.match(syn):
                    raise ValueError('the * operator can only be used as a start or end character '
                                     f'(found {syn} for relation {relation}')



def create_predicate_vocab():
    return dict(administered=['receiv*', 'administrat*'],
                associated=['associat*', 'contain', 'produce', 'convert', 'yield', 'isolate', 'generate', 'synthesize',
                            'grow', 'occures', 'evaluat*', 'augment', 'effect', 'develop*', 'affect', 'contribut*',
                            'involve', 'isa', 'same as', 'coexists with', 'process', 'part of', 'associate',
                            'play', 'limit', 'show', 'present', 'exhibit', 'find', 'form'],
                compares=['compar*', 'correlate*', 'correspond*'],
                induces=['stimulat*', 'increas*', 'potentiat*', 'enhanc*' , 'activat*', 'lead', 'cause', 'side effect*',
                         'adverse', 'complication*', 'drug toxicit*', 'drug injur*', 'upregulat*', 'up regulat*',
                         'up-regulat*'],
                decreases=['reduc*', 'lower*', 'attenuat*', 'mediate', 'downregulat*', 'down-regulat*', 'down regulat*'],
                interacts=['bind', 'interact*', 'target*', 'regulat*', 'block*'],
                metabolises=["metabol*"],
                inhibits=['disrupt*', 'suppres*', 'inhibit*', 'disturb*'],
                treats=['prevent*', 'use', 'improv*', 'promot*', 'sensiti*', 'aid', 'treat*', '*therap*'],
                method=['method*'])


PRED_TO_REMOVE = "PRED_TO_REMOVE"
DOSAGE_FORM_PREDICATE = "administered"
METHOD_PREDICATE = "method"
ASSOCIATED_PREDICATE = "associated"
ASSOCIATED_PREDICATE_UNSURE = ASSOCIATED_PREDICATE
