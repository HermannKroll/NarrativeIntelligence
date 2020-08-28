import logging

from narraint.entity.entityresolver import EntityResolver
from narraint.entity.enttypes import GENE, SPECIES, CHEMICAL, DISEASE
from narraint.entity.meshontology import MeSHOntology
from narraint.extraction.predicate_vocabulary import create_predicate_vocab
from narraint.queryengine.engine import QueryEngine


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    resolver = EntityResolver()
    entities = QueryEngine.query_entities()
    mesh_ontology = MeSHOntology().instance()
    written_entity_ids = set()
    ignored = []
    with open('static/ac_all.txt', 'wt') as f:
        predicates = create_predicate_vocab()
        for pred in predicates.keys():
            f.write('{}\tpredicate\n'.format(pred))
        f.write('dosageform\tpredicate\n')
        counter, notfound = 0, 0
        for e_id, e_str, e_type in entities:
            try:
                # Convert MeSH Tree Numbers to MeSH Descriptors
                if e_type in [CHEMICAL, DISEASE] and not e_id.startswith('MESH:'):
                    mesh_ontology = MeSHOntology.instance()
                    e_id = 'MESH:{}'.format(mesh_ontology.get_descriptor_for_tree_no(e_id)[0])

                # Skip duplicated entries
                if (e_id, e_type) in written_entity_ids:
                    continue
                written_entity_ids.add((e_id, e_type))

                # if entity is a gene - the entity is already the gene symbol
                if e_type == GENE:
                    heading = e_id
                else:
                    heading = resolver.get_name_for_var_ent_id(e_id, e_type)
                if e_type in SPECIES:
                    if '//' in heading:
                        names = heading.split('//')
                        if len(names) != 2:
                            raise ValueError('Species should have 2 names at max: {} ({})'.format(heading,
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

