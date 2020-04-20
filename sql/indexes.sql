CREATE INDEX pred_document_id_idx ON PREDICATION(document_id);
CREATE INDEX pred_document_col_idx ON PREDICATION(document_collection);
CREATE INDEX pred_subject_id_idx ON PREDICATION(subject_id);
CREATE INDEX pred_subject_type_idx ON PREDICATION(subject_type);
CREATE INDEX pred_predicate_idx ON PREDICATION(predicate);
CREATE INDEX pred_predicate_cleaned_idx ON PREDICATION(predicate_cleaned);
CREATE INDEX pred_predicate_canonicalized ON PREDICATION(predicate_canonicalized);
CREATE INDEX pred_object_id_idx ON PREDICATION(object_id);
CREATE INDEX pred_object_type_idx ON PREDICATION(object_type);

CREATE UNIQUE INDEX unique_doc_s_p_o_sent_idx ON PREDICATION(document_id, document_collection, subject_id, predicate, object_id, md5(sentence::text));


CREATE INDEX tag_document_id_idx ON TAG(document_id);
CREATE INDEX tag_document_collection_idx ON TAG(document_collection);

CREATE INDEX doc_tagged_by_doc_idx ON DOC_TAGGED_BY(document_id);
CREATE INDEX doc_tagged_by_doc_collection_idx ON DOC_TAGGED_BY(document_collection);