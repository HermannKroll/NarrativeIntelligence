import logging

from narraint.entity.entityresolver import EntityResolver
from narraint.entity.enttypes import GENE, SPECIES
from narraint.queryengine.engine import QueryEngine


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    resolver = EntityResolver()
    entities = QueryEngine.query_entities()
    written_entity_ids = set()
    ignored = []
    with open('ac_entities.txt', 'wt') as f:
        counter, notfound = 0, 0
        for e_id, e_str, e_type in entities:
            if (e_id, e_type) in written_entity_ids:
                continue
            written_entity_ids.add((e_id, e_type))
            try:
                heading = resolver.get_name_for_var_ent_id(e_id, e_type)

                if e_type in [GENE, SPECIES]:
                    if '//' in heading:
                        names = heading.split('//')
                        if len(names) != 2:
                            raise ValueError('Species and Gene should have 2 names at max: {} ({})'.format(heading,
                                                                                                           names))
                        parts = []
                        for n in names:
                            parts.append('{}\t{}'.format(n, e_id))
                        result = '\n'.join(parts)
                else:
                    result = '{}\t{}'.format(heading, e_id)
                if counter == 0:
                    f.write(result)
                else:
                    f.write('\n' + result)
                counter += 1
            except KeyError:
                ignored.append((e_id, e_type))
                notfound += 1
    logging.info('The following entities are not in index: {}'.format(ignored))
    logging.info('{} entity ids are not in index'.format(notfound))
    logging.info('{} entity information written'.format(counter))


if __name__ == "__main__":
    main()

