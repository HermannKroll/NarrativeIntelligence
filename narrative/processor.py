import itertools
from datetime import datetime
from typing import List

from document import TaggedDocument
from overlay import Narrative


class QueryProcessor:
    def __init__(self, *documents: TaggedDocument):
        self.documents = documents
        self._query: Narrative = None
        self._result = []
        self._start = None
        self._end = None

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
        ent_found = 0
        for ent_name, ent_type in self._query.bounds:
            if ent_name.lower() in doc.mesh_by_entity_name:
                mesh = doc.mesh_by_entity_name[ent_name.lower()]
                if mesh in doc.entities_by_mesh and doc.entities_by_mesh[mesh][0].type == ent_type:
                    ent_found += 1
        return ent_found == len(self._query.bounds)

    def prune_documents(self):
        return [doc for doc in self.documents if self._is_document_candidate(doc)]

    def query(self, narrative: Narrative):
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
                mesh_s = document.mesh_by_entity_name[fact.s.lower()]
                mesh_o = document.mesh_by_entity_name[fact.o.lower()]
                sents_with_ent = document.sentences_by_mesh[mesh_s].intersection(document.sentences_by_mesh[mesh_o])
                sents = {s for s in sents_with_ent if
                         fact.p.lower() in document.sentence_by_id[s].text.lower()}
            elif len(fact.bounds) == 1:
                # One variable
                mesh = document.mesh_by_entity_name[fact.bounds[0][0].lower()]
                v_name, v_type = fact.vars[0]
                sents_with_ent = document.sentences_by_mesh[mesh]
                sents_with_pred = {s for s in sents_with_ent if
                                   fact.p.lower() in document.sentence_by_id[s].text.lower()}
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
                raise NotImplementedError("Narrative with two variables is not implemented.")
            fact_match[fact] = sents

        for event in self._query.events:
            sents = set()
            if len(event.vars) == 0:
                # No variable
                mesh = document.mesh_by_entity_name[event.entity.lower()]
                sents_with_ent = document.sentences_by_mesh[mesh]
                sents = {s for s in sents_with_ent if
                         event.label.lower() in document.sentence_by_id[s].text.lower()}
            else:
                # One variable
                v_name, v_type = event.vars[0]
                sents_with_pred = {sid for sid, sent in document.sentence_by_id.items() if
                                   event.label.lower() in sent.text.lower()}
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
            assignments = [var_assignment[v] for v in variables]
            cart_prod = itertools.product(*assignments)
            for prod in cart_prod:
                result.append({v: prod[idx] for idx, v in enumerate(variables)})

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
        output += "Execution time (total): {}\n".format(self.exec_time_total)
        output += "Execution time (per document): {}".format(self.exec_time_per_document)
        return output

    def print_result(self):
        output = self._get_output()
        print(output)
        with open("results.log", "w") as f:
            f.write(output)
