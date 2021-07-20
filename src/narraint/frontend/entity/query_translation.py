import logging
import re

from narraint.cleaning.relation_vocabulary import create_predicate_vocab
from narraint.frontend.entity.entitytagger import EntityTagger
from narraint.queryengine.query import GraphQuery, FactPattern
from narraint.queryengine.query_hints import VAR_NAME, VAR_TYPE, ENTITY_TYPE_VARIABLE
from narrant.entity.entity import Entity
from narrant.preprocessing.enttypes import ALL, DOSAGE_FORM, GENE, SPECIES


class QueryTranslation:

    def __init__(self, logger=logging):
        self.variable_type_mappings = {}
        for ent_typ in ALL:
            self.variable_type_mappings[ent_typ.lower()] = ent_typ
            self.variable_type_mappings[f'{ent_typ.lower()}s'] = ent_typ
        # support entry of targets
        self.variable_type_mappings["dosage form"] = DOSAGE_FORM
        self.variable_type_mappings["dosage forms"] = DOSAGE_FORM
        self.variable_type_mappings["target"] = GENE
        self.variable_type_mappings["targets"] = GENE
        self.entity_tagger = EntityTagger.instance()

        self.allowed_predicates = set(create_predicate_vocab().keys())
        self.logger = logger
        self.logger.info('allowed predicates are: {}'.format(self.allowed_predicates))

    def check_and_convert_variable(self, text):
        try:
            var_name = VAR_NAME.search(text).group(1)
            m = VAR_TYPE.search(text)
            if m:
                t = m.group(1).lower()
                if t not in self.variable_type_mappings:
                    raise ValueError('"{}" as Variable Type unknown (supported: {})'
                                     .format(t, set(self.variable_type_mappings.values())))
                return '{}({})'.format(var_name, self.variable_type_mappings[t]), self.variable_type_mappings[t]
            else:
                return var_name, None
        except AttributeError:
            if not VAR_NAME.search(text):
                raise ValueError('variable "{}" has no name (e.g. ?X(Chemical))'.format(text))

    def check_wrong_variable_entry(self, text_low):
        if text_low in self.variable_type_mappings:
            var_type = self.variable_type_mappings[text_low]
            var_string = f'?{var_type}({var_type})'
            return [Entity(var_string, ENTITY_TYPE_VARIABLE)]
        else:
            return None

    def convert_text_to_entity(self, text):
        text_low = text.replace('_', ' ').lower()
        if text.startswith('?'):
            var_string, var_type = self.check_and_convert_variable(text)
            e = [Entity(var_string, ENTITY_TYPE_VARIABLE)]
        elif text_low.startswith('mesh:'):
            e = [Entity(text_low.replace('mesh:', 'MESH:').replace('c', 'C').replace('d', 'D'), 'MeSH')]
        elif text_low.startswith('gene:'):
            e = [Entity(text.split(":", 1)[1], GENE)]
        elif text_low.startswith('species:'):
            e = [Entity(text.split(":", 1)[1], SPECIES)]
        elif text_low.startswith('fidx'):
            e = [Entity(text.upper(), DOSAGE_FORM)]
        else:
            # check if the user expects a variable here
            may_variable = self.check_wrong_variable_entry(text_low)
            if may_variable:
                return may_variable
            try:
                e = self.entity_tagger.tag_entity(text)
            except KeyError:
                raise ValueError("Unknown term: {}".format(text))
        return e

    def align_triple(self, text: str):
        # first greedy search the predicate
        text_lower = text.lower().replace('\"', "")
        text_without_quotes = text.replace('\"', "")

        p_found = False
        pred_start, pred_len = 0, 0
        for pred in self.allowed_predicates:
            search = ' {} '.format(pred)
            pos = text_lower.find(search)
            if pos > 0:
                pred_start = pos
                pred_len = len(pred)
                p_found = True
                break
        if not p_found:
            raise ValueError('Cannot find a predicate in: {}'.format(text))

        subj = text_without_quotes[0:pred_start].strip()
        pred = text_without_quotes[pred_start:pred_start + pred_len + 1].strip()
        obj = text_without_quotes[pred_start + pred_len + 1:].strip()
        return subj, pred, obj

    def convert_query_text_to_fact_patterns(self, query_txt) -> (GraphQuery, str):
        if not query_txt.strip():
            return None, "subject or object is missing"
        # remove too many spaces
        fact_txt = re.sub('\s+', ' ', query_txt).strip()
        # split query into facts by '.'
        facts_txt = fact_txt.strip().split('_AND_')
        graph_query = GraphQuery()
        explanation_str = ""
        for fact_txt in facts_txt:
            # skip empty facts
            if not fact_txt.strip():
                continue
            s_t, p_t, o_t = None, None, None
            try:
                # check whether the text forms a triple
                s_t, p_t, o_t = self.align_triple(fact_txt)
            except ValueError:
                explanation_str += 'Cannot find a predicate in: {}'.format(fact_txt)
                self.logger.error('Cannot find a predicate in: {}'.format(fact_txt))
                return None, explanation_str

            try:
                s = self.convert_text_to_entity(s_t)
            except ValueError as e:
                self.logger.error('error unknown subject: {}'.format(e))
                return None, '{} (subject error)\n'.format(e)

            try:
                o = self.convert_text_to_entity(o_t)
            except ValueError as e:
                self.logger.error('error unknown object: {}'.format(e))
                return None,  '{} (object error)\n'.format(e)

            p = p_t.lower()
            if p not in self.allowed_predicates:
                self.logger.error("error unknown predicate: {}".format(p_t))
                return None, "{} (predicate error)\n".format(p_t)

            explanation_str += '{}\t----->\t({}, {}, {})\n'.format(fact_txt.strip(), s, p, o)
            graph_query.add_fact_pattern(FactPattern(s, p, o))

        return graph_query, explanation_str

    def convert_graph_patterns_to_nt(self, query_txt):
        fact_txt = re.sub('\s+', ' ', query_txt).strip()
        facts_split = fact_txt.strip().split('_AND_')
        nt_string = ""
        var_dict = {}
        for f in facts_split:
            # skip empty facts
            if not f.strip():
                continue
            s, p, o = self.align_triple(f.strip())

            if s.startswith('?'):
                var_name = VAR_NAME.search(s).group(1)
                var_type = VAR_TYPE.search(s)
                if var_name not in var_dict:
                    var_dict[var_name], _ = self.check_and_convert_variable(s)
                if var_type:
                    var_dict[var_name], _ = self.check_and_convert_variable(s)
            if o.startswith('?'):
                var_name = VAR_NAME.search(o).group(1)
                var_type = VAR_TYPE.search(o)
                if var_name not in var_dict:
                    var_dict[var_name], _ = self.check_and_convert_variable(o)
                if var_type:
                    var_dict[var_name], _ = self.check_and_convert_variable(o)

        for f in facts_split:
            # skip empty facts
            if not f.strip():
                continue
            s, p, o = self.align_triple(f.strip())

            if s.startswith('?'):
                s = var_dict[VAR_NAME.search(s).group(1)]
            if o.startswith('?'):
                o = var_dict[VAR_NAME.search(o).group(1)]

            nt_string += "<{}>\t<{}>\t<{}>\t.\n".format(s, p, o)
        return nt_string[0:-1]  # remove last \n

    @staticmethod
    def count_variables_in_query(graph_query: GraphQuery):
        var_set = set()
        for fp in graph_query.fact_patterns:
            s = next(iter(fp.subjects)).entity_id
            s_t = next(iter(fp.subjects)).entity_type
            o = next(iter(fp.objects)).entity_id
            o_t = next(iter(fp.objects)).entity_type
            if s_t == 'Variable':
                var_set.add(VAR_NAME.search(s).group(1))
            if o_t == 'Variable':
                var_set.add(VAR_NAME.search(o).group(1))
        return len(var_set)