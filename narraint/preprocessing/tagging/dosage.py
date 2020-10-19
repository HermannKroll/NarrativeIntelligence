import os
import pickle
import re

from narraint import config
from narraint.entity import enttypes
from narraint.config import DOSAGE_ADDITIONAL_DESCS, DOSAGE_ADDITIONAL_DESCS_TERMS, DOSAGE_FID_DESCS, \
    DOSAGE_FORM_TAGGER_INDEX_CACHE, TMP_DIR
from narraint.mesh.data import MeSHDB
from narraint.preprocessing.tagging.dictagger import DictTagger



class DosageFormTagger(DictTagger):
    DOSAGE_FORM_TREE_NUMBERS = (
        "D26.255",  # Dosage Forms
        "E02.319.300",  # Drug Delivery Systems
        "J01.637.512.600",  # Nanoparticles
        "J01.637.512.850",  # Nanotubes
        "J01.637.512.925",  # Nanowires
    )
    TYPES = (enttypes.DOSAGE_FORM,)
    __name__ = "DosageFormTagger"
    __version__ = "1.0.0"

    def __init__(self, *args, **kwargs):
        super().__init__("dosage", "DosageFormTagger", DosageFormTagger.__version__,
                         enttypes.DOSAGE_FORM, config.DOSAGE_FORM_TAGGER_INDEX_CACHE, config.MESH_DESCRIPTORS_FILE,
                         *args, **kwargs)

        self.regex_micro = re.compile(r'micro[a-z]')
        self.regex_intra = re.compile(r'intra[a-z]')

    def load_additional_descs(self):
        # as a dict -
        # just key -> just add the descriptor
        # with values -> combine them to one descriptor
        additional_descs = {}
        with open(DOSAGE_ADDITIONAL_DESCS, 'r') as f:
            for l in f:
                l_s = l.strip()
                if '/' in l_s:
                    descs = l_s.split('/')
                    k = descs[0]
                    additional_descs[k] = []
                    for d in descs[1:]:
                        if d in additional_descs:
                            additional_descs[k].append(d)
                else:
                    if l_s in additional_descs:
                        raise KeyError('descriptor already included: {}'.format(l_s))
                    additional_descs[l_s] = []
        self.logger.debug('{} additional descs loaded'.format(len(additional_descs)))
        return additional_descs

    def load_additional_descs_terms(self):
        desc_terms = {}
        with open(DOSAGE_ADDITIONAL_DESCS_TERMS, 'r') as f:
            for l in f:
                components = l.strip().split('\t')
                desc = components[0]
                terms = components[1].lower().split(';')
                if desc in desc_terms:
                    raise KeyError('descriptor already included: {}'.format(desc))
                desc_terms[desc] = terms
        self.logger.debug('{} additional terms for descriptors added'.format(len(desc_terms)))
        return desc_terms

    def load_fid_descriptors(self):
        desc_terms = {}
        with open(DOSAGE_FID_DESCS, 'r') as f:
            for l in f:
                components = l.strip().split('\t')
                desc = components[0]
                heading = components[1].lower()
                if len(components) > 3:
                    raise Exception('to many \t in one line found')
                if len(components) == 3:
                    terms = components[2].lower().split(';')
                else:
                    terms = []
                terms.append(heading)

                if desc in desc_terms:
                    raise KeyError('descriptor already included: {}'.format(desc))
                desc_terms[desc] = terms
        self.logger.debug('{} FID terms for descriptors added'.format(len(desc_terms)))
        return desc_terms

    def apply_term_rules(self, term):
        new_terms = []
        if self.regex_micro.match(term):
            t1 = term.replace('micro', 'micro ')
            t2 = term.replace('micro', 'micro-')
            new_terms.append(t1)
            new_terms.append(t2)
            self.logger.debug('convert {} to {} and {}'.format(term, t1, t2))
        if self.regex_intra.match(term):
            t1 = term.replace('intra', 'intra ')
            t2 = term.replace('intra', 'intra-')
            new_terms.append(t1)
            new_terms.append(t2)
            self.logger.debug('convert {} to {} and {}'.format(term, t1, t2))

        return new_terms

    def index_from_source(self):
        meshdb = MeSHDB.instance()
        meshdb.load_xml(config.MESH_DESCRIPTORS_FILE)

        # all dosage form descriptors
        # (id, terms) pairs are included
        dosage_forms_all = []

        # load all additional descriptor terms
        for df_id, df_terms in self.load_additional_descs_terms().items():
            dosage_forms_all.append((df_id, list(df_terms)))

        # load all FID descriptor terms
        for df_id, df_terms in self.load_fid_descriptors().items():
            dosage_forms_all.append((df_id, list(df_terms)))

        # load additional descs manual from file
        additional_descs = self.load_additional_descs()
        for desc, to_combine in additional_descs.items():
            d_node = meshdb.desc_by_id(desc)
            d_node_terms = []
            for t in d_node.terms:
                d_node_terms.append(t.string.lower())
            # combine all additional terms
            if len(to_combine) > 0:
                for combine_desc in to_combine:
                    combine_desc_node = meshdb.desc_by_id(combine_desc)
                    for t in combine_desc_node.terms:
                        d_node_terms.add(t.string.lower())
            dosage_forms_all.append((d_node.unique_id, d_node_terms))

        self.logger.debug('loading subtrees...')
        # load descriptors from subtrees
        for df_tn in self.DOSAGE_FORM_TREE_NUMBERS:
            dosage_form_header_node = meshdb.desc_by_tree_number(df_tn)
            dosage_forms = meshdb.descs_under_tree_number(df_tn)
            dosage_forms.append(dosage_form_header_node)

            for df in dosage_forms:
                terms = []
                for t in df.terms:
                    terms.append(t.string.lower())

                dosage_forms_all.append((df.unique_id, terms))

        self.logger.debug(
            '{} descriptors loaded (contains duplicates because some additional terms where added manually)'.format(
                len(dosage_forms_all)))

        # create invers index
        for dosage_form, dosage_form_terms in dosage_forms_all:
            # add all terms for desc
            terms = []
            for t in dosage_form_terms:
                if t == '':
                    self.logger.info('warning skipping empty term for {}'.format(dosage_form))
                # search for rules (micro & intra)
                terms.extend(self.apply_term_rules(t))
                # e.g. tag ointments as well as ointment (plural form -> singular form)
                if t.endswith('s'):
                    t_singular = t[0:-1]
                    # convert to singular
                    terms.append(t_singular)
                    # search for rules (micro & intra)
                    terms.extend(self.apply_term_rules(t_singular))
                else:
                    t_plural = t + 's'
                    # add plural form
                    terms.append(t_plural)
                    # search for rules (micro & intra)
                    terms.extend(self.apply_term_rules(t_plural))
                terms.append(t)
            # go trough heading and all terms
            for term in terms:
                if term in self.desc_by_term:
                    term_descs = self.desc_by_term[term]
                    if dosage_form not in term_descs:
                        self.logger.debug(
                            "term duplicate found {} with different descriptors ({} vs {})".format(term,
                                                                                                   term_descs,
                                                                                                   dosage_form))
                    else:
                        continue
                # allow multiple dosage forms per term
                if term not in self.desc_by_term:
                    self.desc_by_term[term] = [dosage_form]
                else:
                    self.desc_by_term[term].append(dosage_form)
        self.logger.info('DosageFormTagger initialized from data ({} term mappings) - ready to start'
                         .format(len(self.desc_by_term.keys())))
