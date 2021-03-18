WITH doc AS (
    SELECT id, (length(title) + length(abstract) + 10) as length
    from document d
    where collection = 'PubMed'
)
DELETE
FROM tag t
    USING doc
WHERE t.document_id = doc.id
  AND t.end > doc.length
  AND t.document_collection = 'PubMed';


DELETE FROM TAG where ent_id = '-';

DELETE FROM tag WHERE ent_type = 'Chemical';
DELETE FROM doc_tagged_by WHERE ent_type = 'Chemical';

DELETE FROM tag WHERE ent_id like 'OMIM:%';
DELETE FROM doc_tagged_by WHERE ent_type = 'Disease';