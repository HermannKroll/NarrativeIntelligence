import os
import pickle
import re
from datetime import datetime

from narraint import config
from narraint.backend import enttypes
from narraint.config import DOSAGE_ADDITIONAL_DESCS, DOSAGE_ADDITIONAL_DESCS_TERMS, DOSAGE_FID_DESCS, \
    DOSAGE_FORM_TAGGER_INDEX_CACHE, TMP_DIR
from narraint.mesh.data import MeSHDB
from narraint.preprocessing.tagging.base import BaseTagger
from narraint.pubtator.document import DocumentError
from narraint.pubtator.regex import CONTENT_ID_TIT_ABS


class DosageFormTaggerIndex:

    def __init__(self):
        self.mesh_file = ""
        self.tagger_version = DosageFormTagger.__version__
        self.desc_by_term = {}


class DosageFormTagger(BaseTagger):
    PROGRESS_BATCH = 100
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
        super().__init__(*args, **kwargs)
        self.in_dir = os.path.join(self.root_dir, "dosage_in")
        self.out_dir = os.path.join(self.root_dir, "dosage_out")
        self.log_file = os.path.join(self.log_dir, "dosage.log")
        self.desc_by_term = {}

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

    def _check_for_index(self):
        if os.path.isfile(DOSAGE_FORM_TAGGER_INDEX_CACHE):
            index = pickle.load(open(DOSAGE_FORM_TAGGER_INDEX_CACHE, 'rb'))
            if not isinstance(index, DosageFormTaggerIndex):
                self.logger.warning('Ignore index: expect index file to contain an DosageFormTaggerIndexObject: {}'
                                    .format(DOSAGE_FORM_TAGGER_INDEX_CACHE))
                pass

            if index.tagger_version != DosageFormTagger.__version__:
                self.logger.warning('Ignore index: index does not match tagger version ({} index vs. {} tagger)'
                                    .format(index.tagger_version, DosageFormTagger.__version__))
                pass

            if index.mesh_file != config.MESH_DESCRIPTORS_FILE:
                self.logger.warning('Ignore index: index created with another mesh file ({} index vs. {} tagger)'
                                    .format(index.mesh_file, config.MESH_DESCRIPTORS_FILE))
                pass

            self.logger.debug('Use precached index from {}'.format(DOSAGE_FORM_TAGGER_INDEX_CACHE))
            self.desc_by_term = index.desc_by_term
            return index
        pass

    def _create_index(self):
        index = DosageFormTaggerIndex()
        index.mesh_file = config.MESH_DESCRIPTORS_FILE
        index.tagger_version = DosageFormTagger.__version__
        index.desc_by_term = self.desc_by_term
        if not os.path.isdir(TMP_DIR):
            os.mkdir(TMP_DIR)
        self.logger.debug('Storing DosageFormTagerIndex cache to: {}'.format(DOSAGE_FORM_TAGGER_INDEX_CACHE))
        pickle.dump(index, open(DOSAGE_FORM_TAGGER_INDEX_CACHE, 'wb'))

    def prepare(self, resume=False):
        if self._check_for_index():
            self.logger.info('DosageFormTagger initialized from cache ({} term mappings) - ready to start'
                             .format(len(self.desc_by_term.keys())))
            pass
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

        # Store Tagger information in cache
        self._create_index()
        self.logger.info('DosageFormTagger initialized from data ({} term mappings) - ready to start'
                         .format(len(self.desc_by_term.keys())))

        # Create output directory
        if not resume:
            os.mkdir(self.out_dir)
        else:
            raise NotImplementedError("Resuming DosageFormTagger is not implemented.")

    def get_tags(self):
        return self._get_tags(self.out_dir)

    def run(self):
        skipped_files = []
        files_total = len(self.files)
        start_time = datetime.now()

        for idx, in_file in enumerate(self.files):
            if in_file.endswith(".txt"):
                self.logger.debug("Processing {}".format(in_file))
                out_file = os.path.join(self.out_dir, in_file.split("/")[-1])
                try:
                    self.tag(in_file, out_file)
                except DocumentError as e:
                    skipped_files.append(in_file)
                    self.logger.info(e)
                if idx % self.PROGRESS_BATCH == 0:
                    self.logger.info("Progress {}/{}".format(self.get_progress(), files_total))
            else:
                self.logger.debug("Ignoring {}: Suffix .txt missing".format(in_file))

        end_time = datetime.now()
        self.logger.info("Finished in {} ({} files processed, {} files total, {} errors)".format(
            end_time - start_time,
            self.get_progress(),
            files_total,
            len(skipped_files)),
        )

    def tag(self, in_file, out_file):
        with open(in_file) as f:
            document = f.read()
        match = CONTENT_ID_TIT_ABS.match(document)
        if not match:
            raise DocumentError(f"No match in {in_file}")
        pmid, title, abstact = match.group(1, 2, 3)
        content = title.strip() + " " + abstact.strip()
        content = content.lower()

        # Generate output
        output = ""
        for term, descs in self.desc_by_term.items():
            for desc in descs:
                for match in re.finditer(term, content):
                    start = match.start()
                    end = match.end()
                    # Find left end of sequence sequence
                    try:
                        idx = content.rindex(" ", 0, start)
                        if idx != start - 1:
                            start = idx + 1
                    except ValueError:
                        start = 0
                    # Find right end of sequence sequence
                    try:
                        idx = content.index(" ", end)
                        if idx > end:
                            end = idx
                    except ValueError:
                        end = len(content)

                    occurrence = content[start:end]
                    occurrence = occurrence.rstrip(".,;")

                    # if the descriptor is not from us (then it is a mesh descriptor)
                    if not desc.startswith('FIDX'):
                        desc_str = 'MESH:{}'.format(desc)
                    else:
                        desc_str = desc

                    line = "{id}\t{start}\t{end}\t{str}\t{type}\t{desc}\n".format(
                        id=pmid, start=start, end=start + len(occurrence), str=occurrence, type=enttypes.DOSAGE_FORM,
                        desc=desc_str
                    )
                    output += line

        # Write
        with open(out_file, "w") as f:
            f.write(output)

    def get_progress(self):
        return len([f for f in os.listdir(self.out_dir) if f.endswith(".txt")])
