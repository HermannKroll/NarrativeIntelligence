import itertools
import re
from datetime import datetime
from typing import List

from narrative.overlay import Narrative
from pubtator.document import TaggedDocument


class QueryProcessor:
    def __init__(self, *documents: TaggedDocument):
        self.documents = documents
        self._query: Narrative = None
        self._result = []
        self._start = None
        self._end = None
        self._match_by_doc = dict()
        self._mismatch_by_doc = dict()

    @property
    def exec_time_total(self):
        return self._end - self._start

    @property
    def exec_time_per_document(self):
        return self.exec_time_total / len(self.documents)

    def _is_document_candidate(self, doc: TaggedDocument):
        """
        Preselect documents which contain the queried entities
        :param doc:
        :return:
        """
        ent_found = []
        for ent_id, ent_type in self._query.bounds:
            if ent_id in doc.entities_by_mesh and doc.entities_by_mesh[ent_id][0].type == ent_type:
                # mesh = doc.mesh_by_entity_name[ent_id.lower()]
                # if mesh in doc.entities_by_mesh and doc.entities_by_mesh[mesh][0].type == ent_type:
                ent_found.append(ent_id)
        if len(ent_found) == len(self._query.bounds):
            return True
        else:
            self._mismatch_by_doc[doc] = [
                {ent_id: ent_id in ent_found for (ent_id, ent_type) in self._query.bounds},
                dict()
            ]
            return False

    def prune_documents(self):
        return [doc for doc in self.documents if self._is_document_candidate(doc)]

    def query(self, narrative: Narrative):
        self._match_by_doc = dict()
        self._start = datetime.now()
        self._query = narrative
        pruned_docs = self.prune_documents()
        result = []
        for doc in pruned_docs:
            match = self._match_document(doc)
            if match is not None:
                for assignment in match:
                    result.append((doc, assignment))
        self._result = result
        self._end = datetime.now()
        return result

    # TODO: Use ordering of events
    def _match_document(self, document: TaggedDocument) -> List[dict]:
        """
        Returns list of dictionaries with assignments for variables or None.
        :param document:
        :return:
        """
        # Intersect sentence ids
        fact_match = {}
        event_match = {}
        var_assignment = {}
        for fact in self._query.facts:
            sents = set()
            if len(fact.bounds) == 2:
                # No variable
                # mesh_s = document.mesh_by_entity_name[fact.s.lower()]
                # mesh_o = document.mesh_by_entity_name[fact.o.lower()]
                sents_with_ent = document.sentences_by_mesh[fact.s].intersection(document.sentences_by_mesh[fact.o])
                sents = {s for s in sents_with_ent if
                         re.search(fact.p.lower(), document.sentence_by_id[s].text.lower())}
            elif len(fact.bounds) == 1:
                # One variable
                mesh = document.mesh_by_entity_name[fact.bounds[0][0].lower()]
                v_name, v_type = fact.vars[0]
                sents_with_ent = document.sentences_by_mesh[mesh]
                sents_with_pred = {s for s in sents_with_ent if
                                   re.search(fact.p.lower(), document.sentence_by_id[s].text.lower())}
                v_candidates = set()
                for sid in sents_with_pred:
                    for ent in document.entities_by_sentence[sid]:
                        if ent.type == v_type:
                            sents.add(sid)
                            v_candidates.add(ent.text.lower())

                if v_name not in var_assignment:
                    var_assignment[v_name] = v_candidates
                else:
                    var_assignment[v_name] = var_assignment[v_name].intersection(v_candidates)
            else:
                # Two variables
                v1_name, v1_type = fact.vars[0]
                v2_name, v2_type = fact.vars[1]
                sents_with_pred = {sid for sid, sent in document.sentence_by_id.items() if
                                   re.search(fact.p.lower(), sent.text.lower())}
                v1_candidates = set()
                v2_candidates = set()
                for sid in sents_with_pred:
                    if sid in document.entities_by_sentence:
                        v1_cand_sent = set()
                        v2_cand_sent = set()
                        for ent in document.entities_by_sentence[sid]:
                            if ent.type == v1_type:
                                v1_cand_sent.add(ent.text.lower())
                            if ent.type == v2_type:
                                v2_cand_sent.add(ent.text.lower())
                        if v1_cand_sent and v2_cand_sent:
                            sents.add(sid)
                            v1_candidates.union(v1_cand_sent)
                            v2_candidates.union(v2_cand_sent)
                if v1_name not in var_assignment:
                    var_assignment[v1_name] = v1_candidates
                else:
                    var_assignment[v1_name] = var_assignment[v1_name].intersection(v1_candidates)
                if v2_name not in var_assignment:
                    var_assignment[v2_name] = v2_candidates
                else:
                    var_assignment[v2_name] = var_assignment[v2_name].intersection(v2_candidates)
            fact_match[fact] = sents

        for event in self._query.events:
            sents = set()
            if len(event.vars) == 0:
                # No variable
                # mesh = document.mesh_by_entity_name[event.entity.lower()]
                sents_with_ent = document.sentences_by_mesh[event.entity]
                sents = {s for s in sents_with_ent if
                         re.search(event.label.lower(), document.sentence_by_id[s].text.lower())}
            else:
                # One variable
                v_name, v_type = event.vars[0]
                sents_with_pred = {sid for sid, sent in document.sentence_by_id.items() if
                                   re.search(event.label.lower(), sent.text.lower())}
                v_candidates = set()
                for sid in sents_with_pred:
                    if sid in document.entities_by_sentence:
                        for ent in document.entities_by_sentence[sid]:
                            if ent.type == v_type:
                                sents.add(sid)
                                v_candidates.add(ent.text.lower())

                if v_name not in var_assignment:
                    var_assignment[v_name] = v_candidates
                else:
                    var_assignment[v_name] = var_assignment[v_name].intersection(v_candidates)
            event_match[event] = sents

        # Check if match is valid
        result = []
        are_facts_matching = all(len(match) > 0 for _, match in fact_match.items())
        are_events_matching = all(len(match) > 0 for _, match in event_match.items())
        has_result = are_events_matching and are_facts_matching
        if has_result:
            variables = var_assignment.keys()
            if variables:
                assignments = [var_assignment[v] for v in variables]
                cart_prod = itertools.product(*assignments)
                for prod in cart_prod:
                    result.append({v: prod[idx] for idx, v in enumerate(variables)})
            else:
                result.append({})
            self._match_by_doc[document] = [fact_match, event_match]
        else:
            self._mismatch_by_doc[document] = [fact_match, event_match]

        return result if has_result else None

    def _get_output(self):
        variables = [v[0] for v in self._query.vars]
        row_format = "{:<15}" * (len(variables) + 2) + "\n"
        # Header
        output = row_format.format("#", "DocID", *variables)
        output += "-" * (len(variables) + 2) * 15 + "\n"
        # Results
        for idx, (doc, ass) in enumerate(self._result):
            assignments = [ass[v] if v in ass else "" for v in variables]
            output += row_format.format(idx + 1, doc.id, *assignments)
        output += "-" * (len(variables) + 2) * 15 + "\n"
        # Meta
        output += "Number of documents: {}\n".format(len(self._match_by_doc.keys()))
        output += "Execution time (total): {}\n".format(self.exec_time_total)
        output += "Execution time (per document): {}".format(self.exec_time_per_document)
        return output

    def print_result(self, filename="results.log"):
        output = self._get_output()
        print(output)
        with open(filename, "w") as f:
            f.write(output)

    def _get_debug_match(self):
        output = "+" * 16 + " PROVENANCE " + "+" * 17 + "\n"
        row_format = "{:<15}" * 3 + "\n"
        output += row_format.format("DocID", "Fact/Event", "Sentence")
        output += "-" * 3 * 15 + "\n"
        for doc, (fact_match, evt_match) in self._match_by_doc.items():
            output += row_format.format(doc.id, "", "")
            for fact, fact_matches in fact_match.items():
                output += row_format.format("", str(fact), "")
                for m in fact_matches:
                    output += row_format.format("", "", "* " + doc.sentence_by_id[m].text)
            for evt, evt_matches in evt_match.items():
                output += row_format.format("", str(evt), "")
                for m in evt_matches:
                    output += row_format.format("", "", "* " + doc.sentence_by_id[m].text)
            output += "-" * 3 * 15 + "\n"
        return output

    def _get_debug_mismatch(self):
        output = "+" * 17 + " MISMATCH " + "+" * 18 + "\n"
        row_format = "{:<15}" * 3 + "\n"
        output += row_format.format("DocID", "Fact/Event", "Sentence")
        output += "-" * 3 * 15 + "\n"
        for doc, (fact_match, evt_match) in self._mismatch_by_doc.items():
            output += row_format.format(doc.id, "", "")
            for fact, fact_matches in fact_match.items():
                output += row_format.format("", str(fact), "")
                output += row_format.format("", "", str(fact_matches))
            for evt, evt_matches in evt_match.items():
                output += row_format.format("", str(evt), "")
                output += row_format.format("", "", str(evt_matches))
            output += "-" * 3 * 15 + "\n"
        return output

    def print_debug(self, filename="debug.log", with_mismatch=False):
        output = self._get_debug_match()
        if with_mismatch:
            output += "\n" + self._get_debug_mismatch()
        print(output)
        with open(filename, "w") as f:
            f.write(output)
