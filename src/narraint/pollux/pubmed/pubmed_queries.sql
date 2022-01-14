SELECT subject_id, subject_str, predicate, object_str, s.text
FROM Predication join Sentence s on (Predication.sentence_id = s.id)
WHERE extraction_type = 'OPENIE6_PF'  and Predication.document_collection = 'PubMed'
ORDER by random()
LIMIT 100;