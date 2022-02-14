-- Vacuum every table of the db
VACUUM FULL public.document;
VACUUM FULL public.document_classification;
VACUUM FULL public.tag;
VACUUM FULL public.doc_tagged_by;
VACUUM FULL public.document_translation;
VACUUM FULL public.document_metadata;
VACUUM FULL public.document_metadata_service;
VACUUM FULL public.predication;
VACUUM FULL public.predication_inverted_index;
VACUUM FULL public.predication_rating;
VACUUM FULL public.predication_to_delete;
VACUUM FULL public.sentence;
VACUUM FULL public.doc_processed_by_ie;
VACUUM FULL public.tag_inverted_index;

