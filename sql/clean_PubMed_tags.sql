DELETE FROM TAG where ent_id = '-';


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