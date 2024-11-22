from kgextractiontoolbox.backend.retrieve import retrieve_narrative_documents_from_database
from narraint.backend.database import SessionExtended
from narraint.queryengine.engine import QueryEngine
from narraint.queryengine.result import QueryDocumentResult
from narraint.ranking.corpus import DocumentCorpus
from narraint.recommender.core import NarrativeCoreExtractor
from narraint.recommender.document import RecommenderDocument
from narraint.recommender.first_stage import FirstStage
from narraint.recommender.recommender import Recommender
from narraint.recommender.recommender_config import FS_DOCUMENT_CUTOFF_HARD, NOT_CONTAINED_COLOUR_EDGE, enttype2colour, \
    NOT_CONTAINED_COLOUR
from narrant.entity.entityresolver import EntityResolver


class RecommendationSystem:

    def __init__(self):
        self.corpus = DocumentCorpus()
        self.core_extractor = NarrativeCoreExtractor(corpus=self.corpus)
        self.first_stage = FirstStage(extractor=self.core_extractor)
        self.recommender = Recommender(extractor=self.core_extractor)
        self.resolver = EntityResolver()

    def apply_recommendation(self, document_id: int, query_collection: str, document_collections: set):
        session = SessionExtended.get()

        # Step 1: First stage retrieval
        print('Step 1: Perform first stage retrieval...')

        input_docs = retrieve_narrative_documents_from_database(session=session,
                                                                document_ids={document_id},
                                                                document_collection=query_collection)
        if len(input_docs) != 1:
            return []

        input_doc = RecommenderDocument(input_docs[0])
        input_core = self.core_extractor.extract_narrative_core_from_document(input_doc)

        if not input_core:
            print("Step 1 could not extract document core")

        input_core_concept = self.core_extractor.extract_concept_core(input_doc)
        candidate_document_ids = self.first_stage.retrieve_documents_for(input_doc, document_collections)
        candidate_document_ids = [d for d in candidate_document_ids if d[0] != input_doc.id]

        if len(candidate_document_ids) == 0:
            print("Step 1 failed due to no candidate documents")
            return []

        # Apply hard cutoff
        if len(candidate_document_ids) > FS_DOCUMENT_CUTOFF_HARD:
            candidate_document_ids = candidate_document_ids[:FS_DOCUMENT_CUTOFF_HARD]

        # Step 2: document data retrieval
        print('Step 2: Query document data...')
        retrieved_doc_ids = {d[0] for d in candidate_document_ids}
        documents = retrieve_narrative_documents_from_database(session, retrieved_doc_ids, query_collection)
        documents = [RecommenderDocument(d) for d in documents]
        docid2doc = {d.id: d for d in documents}

        # Step 3: recommendation
        print('Step 3: Perform recommendation...')

        rec_doc_ids = self.recommender.recommend_documents_core_overlap(input_doc, documents)
        # ingore scores
        rec_doc_ids = [d[0] for d in rec_doc_ids]
        ranked_docs = [docid2doc[d] for d in rec_doc_ids]

        # Step 4: Get cores of all documents

        # Produce the result
        print('Step 4: Converting results...')
        results = []
        for rec_doc in ranked_docs:
            results.append(QueryDocumentResult(document_id=rec_doc.id,
                                               title=rec_doc.title, authors="", journals="",
                                               publication_year=0, publication_month=0,
                                               var2substitution={}, confidence=0.0,
                                               position2provenance_ids={},
                                               org_document_id=None, doi=None,
                                               document_collection="PubMed", document_classes=None))

        print('Step 5: Loading document metadata...')
        # Load metadata for the documents
        results = QueryEngine.enrich_document_results_with_metadata(results, {"PubMed": rec_doc_ids})

        # get input core concepts
        input_core_concepts = set([sc.concept for sc in input_core_concept.concepts])

        # Convert to a json structure
        results_converted = [r.to_dict() for r in results]
        print('Step 6: Enriching with graph data...')

        for r in results_converted:
            NO_STATEMENTS_TO_SHOW = 6
            rec_doc = docid2doc[int(r["docid"])]
            rec_core = self.core_extractor.extract_narrative_core_from_document(rec_doc)
            facts = []
            nodes = set()
            # nodes that overlap between input doc and rec doc
            overlapping_nodes = set()

            if rec_core:
                core_intersection = input_core.intersect(rec_core)
                core_intersection.statements.sort(key=lambda x: x.score, reverse=True)
                visited = set()

                if core_intersection and len(core_intersection.statements) > 0:
                    for s in core_intersection.statements:
                        if len(facts) > NO_STATEMENTS_TO_SHOW:
                            break

                        try:
                            subject_name = self.resolver.get_name_for_var_ent_id(s.subject_id, s.subject_type,
                                                                                 resolve_gene_by_id=False)
                            object_name = self.resolver.get_name_for_var_ent_id(s.object_id, s.object_type,
                                                                                resolve_gene_by_id=False)

                            if (subject_name, object_name) in visited:
                                continue
                            if (object_name, subject_name) in visited:
                                continue

                            visited.add((subject_name, object_name))
                            visited.add((object_name, subject_name))

                            # none means default colour
                            facts.append(({'s': subject_name, 'p': s.relation, 'o': object_name}, None))
                            nodes.add((subject_name, s.subject_type))
                            nodes.add((object_name, s.object_type))

                            overlapping_nodes.add((subject_name, s.subject_type))
                            overlapping_nodes.add((object_name, s.object_type))
                        except KeyError:
                            pass

                for s in rec_core.statements:
                    if len(facts) > NO_STATEMENTS_TO_SHOW * 2:
                        break
                    if s.subject_id in input_core_concepts or s.object_id in input_core_concepts:
                        try:
                            subject_name = self.resolver.get_name_for_var_ent_id(s.subject_id, s.subject_type,
                                                                                 resolve_gene_by_id=False)
                            object_name = self.resolver.get_name_for_var_ent_id(s.object_id, s.object_type,
                                                                                resolve_gene_by_id=False)

                            if (subject_name, object_name) in visited:
                                continue
                            if (object_name, subject_name) in visited:
                                continue

                            visited.add((subject_name, object_name))
                            visited.add((object_name, subject_name))

                            facts.append(({'s': subject_name, 'p': s.relation, 'o': object_name},
                                          NOT_CONTAINED_COLOUR_EDGE))
                            nodes.add((subject_name, s.subject_type))
                            nodes.add((object_name, s.object_type))

                            if s.subject_id in input_core_concepts:
                                overlapping_nodes.add((subject_name, s.subject_type))
                            else:
                                overlapping_nodes.add((object_name, s.object_type))
                        except KeyError:
                            pass

            else:
                facts = []
                nodes = set()

            # facts = [{'s': 'Metformin', 'p': 'treats', 'o': 'Diabetes Mellitus'}]
            # nodes = ['Metformin', 'Diabetes Mellitus']
            #
            data = {
                "nodes": [],
                "edges": []
            }

            node_id_map = {}
            next_node_id = 1

            for node, node_type in nodes:
                node_id = next_node_id
                # ignore duplicated nodes (different types)
                if node not in node_id_map:
                    node_id_map[node] = node_id
                    if (node, node_type) in overlapping_nodes:
                        data["nodes"].append({"id": node_id, "label": node, "color": enttype2colour[node_type]})
                    else:
                        data["nodes"].append({"id": node_id, "label": node, "color": NOT_CONTAINED_COLOUR})
                next_node_id += 1

            for fact, colour in facts:
                source_id = node_id_map[fact["s"]]
                target_id = node_id_map[fact["o"]]
                if colour == NOT_CONTAINED_COLOUR_EDGE:
                    data["edges"].append({"from": source_id, "to": target_id, "label": fact["p"],
                                          "color": NOT_CONTAINED_COLOUR_EDGE, "dashes": "true"})
                else:
                    data["edges"].append({"from": source_id, "to": target_id, "label": fact["p"]})
            r["graph_data"] = data

        return results_converted
