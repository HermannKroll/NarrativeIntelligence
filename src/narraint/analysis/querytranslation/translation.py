import logging

from narraint.frontend.entity.entitytagger import EntityTagger
from narraint.frontend.entity.query_translation import QueryTranslation
from narraint.queryengine.query import GraphQuery

QUERY_1 = "Metformin Diabetes"
QUERY_2 = "Metformin treats Diabetes"
QUERY_3 = "Metformin mtor Injection DiaBeTes"
QUERY_4 = 'Mass Spectrometry method Simvastatin'
QUERY_5 = "Simvastatin Rhabdomyolysis Target"
QUERIES = [QUERY_1, QUERY_2, QUERY_3, QUERY_4, QUERY_5]


class QueryTranslationToGraph:

    def __init__(self):
        logging.info('Init query translation...')
        self.tagger = EntityTagger.instance()
        self.__load_schema_graph()
        self.data_graph = None
        logging.info('Query translation ready')

    def __load_schema_graph(self):
        translation = QueryTranslation()
        self.entity_types = translation.variable_type_mappings
        self.allowed_predicates = translation.allowed_predicates
        self.max_spaces_in_entity_types = max([len(t.split(' ')) - 1 for t in self.entity_types])
        logging.info(f'Longest entity type has {self.max_spaces_in_entity_types} spaces')

    def __greedy_find_entity_types_in_keyword_query(self, keyword_query):
        keywords = keyword_query.split(' ')
        term2entitytypes = list()
        for i in range(self.max_spaces_in_entity_types, 0, -1):
            for j in range(len(keywords)):
                combined_word = ' '.join([k for k in keywords[j:j + i]])
                if combined_word in self.entity_types:
                    term2entitytypes.append((combined_word, self.entity_types[combined_word]))

        logging.debug('Term2EntityType mapping: ')
        for k, v in term2entitytypes:
            logging.debug(f'    {k} -> {v}')

    def __greedy_find_entities_in_keyword_query(self, keyword_query):
        logging.debug('--' * 60)
        logging.debug('--' * 60)
        keywords_remaining = keyword_query.split(' ')
        keywords_not_mapped = list()
        term2entities = list()
        while keywords_remaining:
            found = False
            i = 0
            for i in range(len(keywords_remaining), 0, -1):
                current_part = ' '.join([k for k in keywords_remaining[:i]])
                # logging.debug(f'Checking query part: {current_part}')
                try:
                    entities_in_part = self.tagger.tag_entity(current_part)
                    term2entities.append((current_part, entities_in_part))
                    # logging.debug(f'Found: {entities_in_part}')
                    found = True
                    break
                except KeyError:
                    pass
            # Have we found an entity?
            if found:
                # Only consider the remaining rest for the next step
                keywords_remaining = keywords_remaining[i:]
            else:
                # logging.debug(f'Not found entity in part {keywords_remaining} - Ignoring {keywords_remaining[0]}')
                # then ignore the current word
                keywords_not_mapped.append(keywords_remaining[0])
                if len(keywords_remaining) > 1:
                    keywords_remaining = keywords_remaining[1:]
                else:
                    keywords_remaining = None
        terms_mapped = ' '.join([t[0] for t in term2entities])
        logging.debug(f'Found entities in part: {terms_mapped}')
        logging.debug(f'Cannot find entities in part: {keywords_not_mapped}')
        logging.debug('Term2Entity mapping: ')
        for k, v in term2entities:
            logging.debug(f'    {k} -> {v}')

        logging.debug('--' * 60)
        logging.debug('--' * 60)

    def translate_keyword_query(self, keyword_query) -> GraphQuery:
        keyword_query = keyword_query.lower().strip()
        self.__greedy_find_entity_types_in_keyword_query(keyword_query)
        self.__greedy_find_entities_in_keyword_query(keyword_query)
        return GraphQuery()


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    trans = QueryTranslationToGraph()
    for q in QUERIES:
        logging.info('==' * 60)
        logging.info(f'Translating query: {q}')
        graph_q = trans.translate_keyword_query(q)
        logging.info('==' * 60)


if __name__ == "__main__":
    main()
