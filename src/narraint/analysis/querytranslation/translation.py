import logging

from narraint.frontend.entity.entitytagger import EntityTagger
from narraint.queryengine.query import GraphQuery

QUERY_1 = "Metformin Diabetes"
QUERY_2 = "Metformin treats Diabetes"
QUERY_3 = "Metformin mtor Injection DiaBeTes"
QUERY_4 = 'Mass Spectrometry method Simvastatin'
QUERY_5 = "Simvastatin Rhabdomyolysis Target"
QUERIES = [QUERY_1, QUERY_2, QUERY_3, QUERY_4, QUERY_5]


class QueryTranslation:

    def __init__(self):
        logging.info('Init query translation...')
        self.tagger = EntityTagger.instance()
        self.schema_graph = None
        self.data_graph = None
        pass

    def __greedy_find_entities_in_keyword_query(self, keyword_query):
        logging.debug('--'*60)
        logging.debug('--'*60)
        keywords_remaining = keyword_query.strip().split(' ')
        keywords_not_mapped = list()
        term2entities = list()
        while keywords_remaining:
            found = False
            i = 0
            for i in range(len(keywords_remaining), 0, -1):
                current_part = ' '.join([k for k in keywords_remaining[:i]])
                #logging.debug(f'Checking query part: {current_part}')
                try:
                    entities_in_part = self.tagger.tag_entity(current_part)
                    term2entities.append((current_part, entities_in_part))
                    #logging.debug(f'Found: {entities_in_part}')
                    found = True
                    break
                except KeyError:
                    pass
            # Have we found an entity?
            if found:
                # Only consider the remaining rest for the next step
                keywords_remaining = keywords_remaining[i:]
            else:
                #logging.debug(f'Not found entity in part {keywords_remaining} - Ignoring {keywords_remaining[0]}')
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

        logging.debug('--'*60)
        logging.debug('--'*60)

    def translate_keyword_query(self, keyword_query) -> GraphQuery:
        self.__greedy_find_entities_in_keyword_query(keyword_query)
        return GraphQuery()


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    trans = QueryTranslation()
    for q in QUERIES:
        logging.info('==' * 60)
        logging.info(f'Translating query: {q}')
        graph_q = trans.translate_keyword_query(q)
        logging.info('==' * 60)


if __name__ == "__main__":
    main()
