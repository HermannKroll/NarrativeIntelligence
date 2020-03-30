CREATE INDEX pred_document_id_idx ON PREDICATION(document_id);
CREATE INDEX pred_document_col_idx ON PREDICATION(document_collection);
CREATE INDEX pred_subject_id_idx ON PREDICATION(subject_id);
CREATE INDEX pred_subject_type_idx ON PREDICATION(subject_type);
CREATE INDEX pred_predicate_idx ON PREDICATION(predicate);
CREATE INDEX pred_predicate_cleaned_idx ON PREDICATION(predicate_cleaned);
CREATE INDEX pred_predicate_canonicalized ON PREDICATION(predicate_canonicalized);
CREATE INDEX pred_object_id_idx ON PREDICATION(object_id);
CREATE INDEX pred_object_type_idx ON PREDICATION(object_type);

CREATE INDEX tag_document_id_idx ON TAG(document_id);
CREATE INDEX tag_document_collection_idx ON TAG(document_collection);