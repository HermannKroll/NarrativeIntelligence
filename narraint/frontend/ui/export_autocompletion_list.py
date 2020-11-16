import itertools
import logging

from narraint.entity.entityresolver import EntityResolver
from narraint.entity.entitytagger import DosageFormTaggerVocabulary
from narraint.entity.enttypes import GENE, SPECIES, CHEMICAL, DISEASE, DOSAGE_FORM
from narraint.entity.meshontology import MeSHOntology
from narraint.extraction.predicate_vocabulary import create_predicate_vocab
from narraint.queryengine.engine import QueryEngine


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    resolver = EntityResolver()
    logging.info('Query entities in Predication...')
    entities = QueryEngine.query_entities()
    writen_entity_terms = set()
    ignored = []
    predicates = create_predicate_vocab()
    with open('static/ac_predicates.txt', 'wt') as f_pred:
        for idx, pred in enumerate(predicates.keys()):
            if pred != 'PRED_TO_REMOVE':
                if idx == 0:
                    f_pred.write('{}'.format(pred))
                else:
                    f_pred.write(',{}'.format(pred))

    mesh_ontology = MeSHOntology.instance()
    with open('static/ac_all.txt', 'wt') as f, open('static/ac_entities.txt', 'wt') as f_ent:
        for pred in predicates.keys():
            if pred != 'PRED_TO_REMOVE':
                f.write('{}\tpredicate\n'.format(pred))
        notfound = 0

        # Write dosage form terms + synonyms
        for df_id, terms in DosageFormTaggerVocabulary.get_dosage_form_vocabulary_terms().items():
            for t in terms:
                if not t.endswith('s'):
                    t = '{}s'.format(t)
                t = t.replace('-', ' ')
                if df_id.startswith('D'):
                    df_id = 'MESH:{}'.format(df_id)
                if t not in writen_entity_terms:
                    writen_entity_terms.add(t)
                    result = '{}\t{}'.format(t, df_id)
                    f.write('\n' + result)
                    f_ent.write('\n' + result)

        # check all known mesh entities
        known_mesh_prefixes = set()
        for e_id, e_str, e_type in entities:
            if e_type in [CHEMICAL, DISEASE, DOSAGE_FORM] and not e_id.startswith('MESH:') and not e_id.startswith('DB'):
                # Split MeSH Tree No by .
                split_tree_number = e_id.split('.')
                # add all known concepts and superconcepts to our index
                # D02
                # D02.255
                # D02.255.234
                for x in range(0, len(split_tree_number)):
                    known_prefix = '.'.join(split_tree_number[0:x+1])
                    known_mesh_prefixes.add(known_prefix)

        # write the mesh tree C and D
        mesh_descs_to_export = itertools.chain(mesh_ontology.find_descriptors_start_with_tree_no("D"),
                                               mesh_ontology.find_descriptors_start_with_tree_no("C"))
        for d_id, d_heading in mesh_descs_to_export:
            export_desc = False
            for tn in mesh_ontology.get_tree_numbers_for_descriptor(d_id):
                if tn in known_mesh_prefixes:
                    export_desc = True
                    break
            e_id = 'MESH:{}'.format(d_id)
            if export_desc and d_heading not in writen_entity_terms:
                writen_entity_terms.add(d_heading)
                result = '{}\t{}'.format(d_heading, e_id)
                f.write('\n' + result)
                f_ent.write('\n' + result)

        written_entity_ids = set()
        for e_id, e_str, e_type in entities:
            try:
                # Convert MeSH Tree Numbers to MeSH Descriptors
                if e_type in [CHEMICAL, DISEASE, DOSAGE_FORM] and not e_id.startswith('MESH:'):
                    e_id = 'MESH:{}'.format(mesh_ontology.get_descriptor_for_tree_no(e_id)[0])
                    if e_id.startswith('FID'):
                        e_type = 'FID'
                    else:
                        e_type = 'MESH'
                # Skip duplicated entries
                if (e_id, e_type) in written_entity_ids:
                    continue
                written_entity_ids.add((e_id, e_type))

                heading = resolver.get_name_for_var_ent_id(e_id, e_type, resolve_gene_by_id=False)
                if e_type in [GENE, SPECIES]:
                    if '//' in heading:
                        names = heading.split('//')
                        if len(names) != 2:
                            raise ValueError('Species should have 2 names at max: {} ({})'.format(heading,
                                                                                                  names))
                        parts = []
                        for n in names:
                            parts.append('{}\t{}'.format(n, e_id))
                        result = '\n'.join(parts)
                        f.write('\n' + result)
                        f_ent.write('\n' + result)
                    else:
                        if heading not in writen_entity_terms:
                            writen_entity_terms.add(heading)
                            result = '{}\t{}'.format(heading, e_id)
                            f.write('\n' + result)
                            f_ent.write('\n' + result)
                else:
                    if heading not in writen_entity_terms:
                        writen_entity_terms.add(heading)
                        result = '{}\t{}'.format(heading, e_id)
                        f.write('\n' + result)
                        f_ent.write('\n' + result)

            except KeyError:
                ignored.append((e_id, e_type))
                notfound += 1
    logging.info('The following entities are not in index: {}'.format(ignored))
    logging.info('{} entity ids are not in index'.format(notfound))


if __name__ == "__main__":
    main()
