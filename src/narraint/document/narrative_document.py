from typing import List

from narrant.pubtator.document import TaggedDocument, TaggedEntity


class DocumentSentence:

    def __init__(self, sentence_id: str, text: str):
        self.sentence_id = sentence_id
        self.text = text

    def to_dict(self):
        return {"id": self.sentence_id, "text": self.text}


class StatementExtraction:

    def __init__(self, subject_id: str, subject_type: str, subject_str: str,
                 predicate: str, relation: str, object_id: str, object_type: str, object_str: str,
                 sentence_id: int):
        self.subject_id = subject_id
        self.subject_type = subject_type
        self.subject_str = subject_str
        self.predicate = predicate
        self.relation = relation
        self.object_id = object_id
        self.object_type = object_type
        self.object_str = object_str
        self.sentence_id = sentence_id

    def to_dict(self):
        return {
            "subject_id": self.subject_id,
            "subject_type": self.subject_type,
            "subject_str": self.subject_str,
            "predicate": self.predicate,
            "relation": self.relation,
            "object_id": self.object_id,
            "object_type": self.object_type,
            "object_str": self.object_str,
            "sentence_id": self.sentence_id
        }


class NarrativeDocumentMetadata:

    def __init__(self, publication_year: int, publication_month: int, authors: str, journals: str,
                 publication_doi: str):
        self.publication_year = publication_year
        self.publication_month = publication_month
        self.authors = authors
        self.journals = journals
        self.publication_doi = publication_doi

    def to_dict(self):
        """
       {
          "publication_year":1992,
          "publication_month":4,
          "authors":"Dromer, C | Vedrenne, C | Billey, T | Pages, M | Fourni\u00e9, B | Fourni\u00e9, A",
          "journals":"Revue du rhumatisme et des maladies osteo-articulaires, Vol. 59 No. 4 (Apr 1992)",
          "doi":"https://www.pubpharm.de/vufind/Search/Results?lookfor=NLM1496277"
       }
        :return: a dict with metadata information
        """
        return dict(publication_year=self.publication_year,
                    publication_month=self.publication_month,
                    authors=self.authors,
                    journals=self.journals,
                    doi=self.publication_doi)


class NarrativeDocument(TaggedDocument):

    def __init__(self, document_id, title: str, abstract: str,
                 metadata: NarrativeDocumentMetadata = None,
                 tags: List[TaggedEntity] = None,
                 sentences: List[DocumentSentence] = None,
                 extracted_statements: List[StatementExtraction] = None):
        super().__init__(id=document_id, title=title, abstract=abstract)
        self.tags = tags
        if self.tags:
            self.sort_tags()
        self.metadata = metadata
        self.sentences = sentences
        self.extracted_statements = extracted_statements

    def to_dict(self):
        """
        {
          "id":1496277,
          "title":"[Rhabdomyolysis due to simvastin. Apropos of a case with review of the literature].",
          "abstract":"A new case of simvastatin-induced acute rhabdomyolysis with heart failure after initiation of treatment with fusidic acid is reported. In most reported instances, statin treatment was initially well tolerated with muscle toxicity developing only after addition of another drug. The mechanism of this muscle toxicity is unelucidated but involvement of a decrease in tissue Co enzyme Q is strongly suspected.",
          "classification":[

          ],
          "tags":[
             {
                "id":"MESH:D012206",
                "mention":"rhabdomyolysis",
                "start":1,
                "end":15,
                "type":"Disease"
             }, ...
          ],
         "metadata":{
              "publication_year":1992,
              "publication_month":4,
              "authors":"Dromer, C | Vedrenne, C | Billey, T | Pages, M | Fourni\u00e9, B | Fourni\u00e9, A",
              "journals":"Revue du rhumatisme et des maladies osteo-articulaires, Vol. 59 No. 4 (Apr 1992)",
              "doi":"https://www.pubpharm.de/vufind/Search/Results?lookfor=NLM1496277"
           }
          "sentences":[
             {
                "id":2456018,
                "text":"A new case of simvastatin-induced acute rhabdomyolysis with heart failure after initiation of treatment with fusidic acid is reported."
             }
          ],
          "statements":[
             {
                "subject_id":"CHEMBL374975",
                "subject_type":"Drug",
                "subject_str":"fusidic acid",
                "predicate":"treatment",
                "relation":"treats",
                "object_id":"MESH:D006333",
                "object_type":"Disease",
                "object_str":"heart failure",
                "sentence_id":2456018
             },
             ...
          ]
        }
        :return:
        """
        tagged_dict = super().to_dict()
        if self.metadata:
            tagged_dict["metadata"] = self.metadata.to_dict()
        if self.sentences:
            tagged_dict["sentences"] = list([s.to_dict() for s in self.sentences])
        if self.extracted_statements:
            tagged_dict["statements"] = list([es.to_dict() for es in self.extracted_statements])

        return tagged_dict
