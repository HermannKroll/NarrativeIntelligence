import logging

from narraint.entity.entityresolver import EntityResolver
from narraint.entity.enttypes import GENE, SPECIES
from narraint.queryengine.engine import QueryEngine


class EntityTagger:

    def __init__(self):
        self.resolver = EntityResolver.instance()
        self.term2entity = {}
        self._create_reverse_index()

    def _add_to_reverse_index(self, items, e_type, id_prefix=''):
        for e_id, e_term in items:
            term = e_term.lower().strip()
            self.term2entity[term] = (id_prefix+e_id, e_type)

    def _create_reverse_index(self):
        self._add_to_reverse_index(self.resolver.mesh.supplement_desc2heading.items(), 'MESH', id_prefix='MESH:')
        self._add_to_reverse_index(self.resolver.mesh.desc2heading.items(), 'MESH', id_prefix='MESH:')
        for e_term, e_id in self.resolver.gene.get_reverse_index().items():
            self.term2entity[e_term.strip().lower()] = (e_id, GENE)
        for e_term, e_id in self.resolver.species.get_reverse_index().items():
            self.term2entity[e_term.strip().lower()] = (e_id, SPECIES)
        self._add_to_reverse_index(self.resolver.dosageform.fid2name.items(), 'DosageForm')

        logging.info('{} different terms map to entities'.format(len(self.term2entity)))

    def tag_entity(self, term: str):
        return self.term2entity[term.lower().strip()]


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


