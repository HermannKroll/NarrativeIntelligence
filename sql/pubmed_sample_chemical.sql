SELECT id
FROM document
WHERE collection = 'PubMed' and id
IN
(SELECT distinct(d1.id) FROM document d1 JOIN Tag t1
    ON (d1.id = t1.document_id and d1.collection = t1.document_collection)
 WHERE d1.collection = 'PubMed' and t1.ent_type = 'Chemical' and d1.abstract <> ''
)
ORDER BY random()
LIMIT 1000000