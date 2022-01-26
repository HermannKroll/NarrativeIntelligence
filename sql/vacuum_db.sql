-- Vacuum every table of the db
VACCUM FULL public.document;
VACCUM FULL public.document_classification;
VACCUM FULL public.tag;
VACCUM FULL public.doc_tagged_by;
VACCUM FULL public.document_translation;
VACCUM FULL public.document_metadata;
VACCUM FULL public.document_metadata_service;
VACCUM FULL public.predication;
VACCUM FULL public.predication_denorm;
VACCUM FULL public.predication_rating;
VACCUM FULL public.predication_to_delete;
VACCUM FULL public.sentence;
VACCUM FULL public.doc_processedy_by_ie;

