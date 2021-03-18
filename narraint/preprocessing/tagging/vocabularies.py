import logging
from collections import defaultdict
from datetime import datetime
from itertools import islice
from typing import List

import lxml.etree as ET

from narraint import config
from narraint.config import MESH_DESCRIPTORS_FILE, METHOD_CLASSIFICATION_FILE
from narraint.entity.enttypes import METHOD, LAB_METHOD
from narraint.mesh.data import MeSHDB
from narraint.preprocessing.tagging.dictagger import clean_vocab_word_by_split_rules
from narraint.progress import print_progress_with_eta


def expand_vocabulary_term(term: str) -> str:
    if term.endswith('y'):
        yield f'{term[:-1]}ies'
    if term.endswith('ies'):
        yield f'{term[:-3]}y'
    if term.endswith('s') or term.endswith('e'):
        yield term[:-1]
    if term.endswith('or') and len(term) > 2:
        yield term[:-2] + "our"
    if term.endswith('our') and len(term) > 3:
        yield term[:-3] + "or"
    yield from [term, f'{term}e', f'{term}s']


class MeSHVocabulary:

    @staticmethod
    def create_mesh_vocab(subtrees: List[str], mesh_file=MESH_DESCRIPTORS_FILE, expand_by_s_and_e=True):
        desc_by_term = defaultdict(set)

        meshdb = MeSHDB.instance()
        meshdb.load_xml(mesh_file)
        logging.info('Extracting MeSH information (terms) ...')
        for desc in meshdb.get_all_descs():
            has_correct_tree = False
            # check if a descriptor's tree matches the allowed subtrees
            for tn in desc.tree_numbers:
                for allowed_tree in subtrees:
                    if tn.startswith(allowed_tree):
                        has_correct_tree = True
            # ignore descriptor
            if not has_correct_tree:
                continue

            mesh_desc = f'MESH:{desc.unique_id}'
            if expand_by_s_and_e:
                for t_e in expand_vocabulary_term(desc.name.lower().strip()):
                    desc_by_term[t_e].add(mesh_desc)
            else:
                desc_by_term[desc.name.lower().strip()].add(mesh_desc)
            for t in desc.terms:
                if expand_by_s_and_e:
                    for t_e in expand_vocabulary_term(t.string.lower().strip()):
                        desc_by_term[t_e].add(mesh_desc)
                else:
                    desc_by_term[t.string.lower().strip()].add(mesh_desc)
        return desc_by_term


class MethodVocabulary:

    @staticmethod
    def read_method_classification(file=METHOD_CLASSIFICATION_FILE):
        desc2class = {}
        with open(file, 'rt') as f:
            for line in f:
                comps = line.strip().split('\t')
                if len(comps) == 2 and comps[0] == 'l':
                    desc2class[comps[1]] = LAB_METHOD
                elif len(comps) == 2 and comps[0] == 'unspezif.':
                    desc2class[comps[1]] = None
                else:
                    desc2class[comps[0]] = METHOD
        return desc2class

    @staticmethod
    def enhance_methods_by_rules(term2desc: {str: str}):
        term2desc_copy = term2desc.copy()
        for term, descs in term2desc.items():
            if 'metric' in term:
                term2desc_copy[term.replace('metric', 'metry')] = descs
            if 'metry' in term:
                term2desc_copy[term.replace('metry', 'metric')] = descs
            if 'stain' in term and not 'staining' in term:
                term2desc_copy[term.replace('stain', 'staining')] = descs
            if 'staining' in term:
                term2desc_copy[term.replace('staining', 'stain')] = descs

        return term2desc_copy

    @staticmethod
    def create_method_vocabulary(mesh_file=MESH_DESCRIPTORS_FILE, expand_terms=True, method_type=METHOD):
        term2desc = MeSHVocabulary.create_mesh_vocab(['E'], mesh_file, expand_terms)
        term2desc = MethodVocabulary.enhance_methods_by_rules(term2desc)
        desc2class = MethodVocabulary.read_method_classification()
        term2methods = {k: list([d for d in descs if desc2class[d] == method_type]) for k, descs in term2desc.items()}
        return {k: v for k, v in term2methods.items() if v and len(v) > 0}


class LabMethodVocabulary:

    @staticmethod
    def create_lab_method_vocabulary(mesh_file=MESH_DESCRIPTORS_FILE, expand_terms=True):
        term2desc = MethodVocabulary.create_method_vocabulary(mesh_file, expand_terms=expand_terms, method_type=LAB_METHOD)
        if 'assay' not in term2desc:
            term2desc['assay'] = ['FIDXLM1']
        else:
            term2desc['assay'].append('FIDXLM1')
        return term2desc


class DiseaseVocabulary:

    @staticmethod
    def create_disease_vocabulary(mesh_file=MESH_DESCRIPTORS_FILE, expand_by_s_and_e=True):
        return MeSHVocabulary.create_mesh_vocab(['C', 'F03'], mesh_file, expand_by_s_and_e)


class DrugBankChemicalVocabulary:

    @staticmethod
    def read_drugbank_chemical_names(drugbank_chemical_list=config.DRUGBANK_CHEMICAL_DATABASE_FILE):
        chemical_mapping = {}
        with open(drugbank_chemical_list, 'rt') as f:
            for line in f:
                chemical = line.strip()
                chemical_mapping[chemical.lower()] = chemical.capitalize()
        return chemical_mapping

    @staticmethod
    def create_drugbank_chemical_vocabulary(drugbank_chemical_list=config.DRUGBANK_CHEMICAL_DATABASE_FILE,
                                            drugbank_db_file=config.DRUGBASE_XML_DUMP):
        # we cannot ignore the excipient terms while reading drugbank here (else our mapping would be empty)
        drugbank_terms = DrugTaggerVocabulary.create_drugbank_vocabulary_from_source(source_file=drugbank_db_file,
                                                                                     ignore_excipient_terms=False,
                                                                                     ignore_drugbank_chemicals=False)
        # drugbank chemicals
        drugbank_chemicals_mapping = DrugBankChemicalVocabulary.read_drugbank_chemical_names(drugbank_chemical_list)
        drugbank_identifiers_for_chemical = set()
        desc_by_term = {}
        # if an chemical term is found in drugbank - use the drugbnak identifier for tagging
        for chemical_term, chemical_heading in drugbank_chemicals_mapping.items():
            # do we find a corresponding term in drugbank
            if chemical_term in drugbank_terms:
                # yes - we take the DrugBank identifier
                drugbank_identifiers_for_chemical.update(drugbank_terms[chemical_term])
            else:
                desc_by_term[chemical_term] = [chemical_heading]

        # search all drugbank terms which map to a chemical drugbank identifier
        for drugbank_term, dbids in drugbank_terms.items():
            for dbid in dbids:
                if dbid in drugbank_identifiers_for_chemical:
                    # the drugbank term will be mapped to its corresponding dbid
                    desc_by_term[drugbank_term] = dbids
                    # stop iteration here
                    break
        return desc_by_term


class DrugTaggerVocabulary:

    @staticmethod
    def create_drugbank_vocabulary_from_source(source_file=config.DRUGBASE_XML_DUMP, drug_min_name_length=3,
                                               check_products=0, drug_max_per_product=2, ignore_excipient_terms=True,
                                               ignore_drugbank_chemicals=True,
                                               expand_term_with_e_and_s=True):
        # TODO real check
        drug_number = 13581  # subprocess.check_output(f"grep -c '^<drug' {self.source_file}")
        start = datetime.now()
        drugs_found = 0
        logging.info(f"")
        pref = '{http://www.drugbank.ca}'
        desc_by_term = {}
        drugs_without_description_and_indication = 0

        # read excipient terms if they should be ignored
        if ignore_excipient_terms:
            excipient_terms = ExcipientVocabulary.read_excipients_names()
        if ignore_drugbank_chemicals:
            drugbank_chemicals = DrugBankChemicalVocabulary.read_drugbank_chemical_names()

        for event, elem in ET.iterparse(source_file, tag=f'{pref}drug'):
            desc = ''
            for dbid in elem.findall(f'{pref}drugbank-id'):
                if dbid.attrib.get('primary'):
                    desc = dbid.text
                    break
            if desc == '':
                continue
            drugs_found += 1
            print_progress_with_eta("building index...", drugs_found, drug_number, start, print_every_k=100)
            description_text = elem.find(f'{pref}description').text
            if description_text and 'allergen' in description_text.lower()[0:30]:
                continue
            indication_text = elem.find(f'{pref}indication').text
            if not description_text and not indication_text:
                drugs_without_description_and_indication += 1
                continue
            name_elements = list(elem.findall(f'{pref}name'))
            synonyms = elem.find(f'{pref}synonyms')
            if synonyms is not None:
                name_elements += list(synonyms.findall(f'{pref}synonym'))
            if check_products > 0:
                products = elem.find(f'{pref}products')
                if products is not None:
                    for product in products.findall(f'{pref}product'):
                        name = product.find(f'{pref}name')
                        if name is not None:
                            name_elements.append(name)
            exp_props = elem.find(f'{pref}experimental-properties')
            if exp_props is not None:
                for exp_prop in exp_props:
                    if exp_prop.find(f'{pref}kind').text == "Molecular Formula":
                        name_elements.append(exp_prop.find(f'{pref}value'))
            names = {ne.text for ne in name_elements if len(ne.text) >= drug_min_name_length}
            names = {clean_vocab_word_by_split_rules(n.lower()) for n in names}

            # ignore dbid if it's already an excipient
            if ignore_excipient_terms and len([n for n in names if n in excipient_terms]) > 0:
                continue
            # ignore dbid if it's already an DrugBankChemical
            if ignore_drugbank_chemicals and len([n for n in names if n in drugbank_chemicals]) > 0:
                continue

            if expand_term_with_e_and_s:
                names = names | {f"{n}s" for n in names} | {f"{n}e" for n in names}
            for n in names:
                if n in desc_by_term:
                    desc_by_term[n].add(desc)
                else:
                    desc_by_term[n] = {desc, }
        if drug_max_per_product > 0:
            desc_by_term = {k: v
                            for k, v in desc_by_term.items()
                            if len(v) <= drug_max_per_product}
        return desc_by_term


class ExcipientVocabulary:

    @staticmethod
    def read_excipients_names(source_file=config.EXCIPIENT_TAGGER_DATABASE_FILE,
                              drugbank_excipient_file=config.EXCIPIENT_TAGGER_DRUGBANK_EXCIPIENT_FILE,
                              expand_terms_by_e_and_s=True):
        excipient_dict = {}
        with open(source_file, 'rt') as f:
            for line in islice(f, 1, None):
                comps = line.split('~')
                excipient = clean_vocab_word_by_split_rules(comps[0].strip().lower())
                excipient_heading = excipient.capitalize()
                if expand_terms_by_e_and_s:
                    excipient_terms = expand_vocabulary_term(excipient)
                else:
                    excipient_terms = [excipient]
                for term in excipient_terms:
                    if term in excipient_dict:
                        excipient_dict[term].add(excipient_heading)
                    else:
                        excipient_dict[term] = {excipient_heading}

        with open(drugbank_excipient_file, 'rt') as f:
            for line in f:
                excipient = line.lower().strip()
                excipient_heading = excipient.capitalize()
                if expand_terms_by_e_and_s:
                    excipient_terms = expand_vocabulary_term(excipient)
                else:
                    excipient_terms = [excipient]
                for term in excipient_terms:
                    if term in excipient_dict:
                        excipient_dict[term].add(excipient_heading)
                    else:
                        excipient_dict[term] = {excipient_heading}
        return excipient_dict

    @staticmethod
    def create_excipient_vocabulary(excipient_database=config.EXCIPIENT_TAGGER_DATABASE_FILE,
                                    drugbank_db_file=config.DRUGBASE_XML_DUMP, ):
        # we cannot ignore the excipient terms while reading drugbank here (else our mapping would be empty)
        drugbank_terms = DrugTaggerVocabulary.create_drugbank_vocabulary_from_source(source_file=drugbank_db_file,
                                                                                     ignore_excipient_terms=False)
        logging.info(f'Reading excipient database: {excipient_database}...')
        excipient_terms = ExcipientVocabulary.read_excipients_names()
        drugbank_identifiers_for_excipients = set()
        desc_by_term = {}
        # extend dict by all excipient terms
        # if an excipient term is found in drugbank - use the drugbnak identifier for tagging
        for excipient_term, excipient_headings in excipient_terms.items():
            # do we find a corresponding term in drugbank
            if excipient_term in drugbank_terms:
                # yes - we take the DrugBank identifier
                drugbank_identifiers_for_excipients.update(drugbank_terms[excipient_term])
            else:
                desc_by_term[excipient_term] = excipient_headings

        # search all drugbank terms which map to excipient drugbank identifier
        for drugbank_term, dbids in drugbank_terms.items():
            for dbid in dbids:
                if dbid in drugbank_identifiers_for_excipients:
                    # the drugbank term will be mapped to its corresponding dbid
                    desc_by_term[drugbank_term] = dbids
                    # stop iteration here
                    break

        return desc_by_term


class PlantFamilyVocabulary:

    @staticmethod
    def read_plant_family_vocabulary(plant_family_database=config.PLANT_FAMILTY_DATABASE_FILE,
                                     expand_terms=True):
        term_to_plant_family = {}
        with open(plant_family_database, 'rt') as f:
            for line in f:
                plant_family = line.strip()
                plant_family_lower = plant_family.lower()
                if expand_terms:
                    plant_family_terms = [plant_family_lower]
                    if plant_family.endswith('a'):
                        plant_family_terms.extend([f'{plant_family_lower}e',
                                                   f'{plant_family_lower}s', # for the stupid ones :)
                                                  f'{plant_family_lower}rum'])
                    if plant_family.endswith('ae'):
                        plant_family_terms.extend([plant_family_lower[:-1],
                                                   f'{plant_family_lower[:-1]}s',
                                                   f'{plant_family_lower}rum'])
                    if plant_family.endswith('us'):
                        plant_family_terms.extend([plant_family_lower[:-1],
                                                   f'{plant_family_lower[:-1]}um'])
                    if plant_family.endswith('um'):
                        plant_family_terms.extend([f'{plant_family_lower[:-2]}i',
                                                   f'{plant_family_lower}s', # for the stupid ones :)
                                                   f'{plant_family_lower[:-2]}a',
                                                   f'{plant_family_lower[:-2]}orum'])
                else:
                    plant_family_terms = [plant_family_lower]
                for term in plant_family_terms:
                    term_to_plant_family[term] = {plant_family.capitalize()}
        return term_to_plant_family
