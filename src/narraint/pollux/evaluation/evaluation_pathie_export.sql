
-- Wikipedia
-- Award Received
SELECT subject_str, subject_id, subject_type, predicate_org, predicate, relation, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'scientists' and subject_type = 'Person' and object_type = 'Award' and extraction_type = 'PathIE'
and relation = 'award received'
ORDER BY random()
LIMIT 100


SELECT subject_str, subject_id, subject_type, predicate_org, predicate, relation, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'scientists' and extraction_type = 'PathIE'
ORDER BY random()
LIMIT 100

-- PathIE Statistics
SELECT predicate, relation, count(*)
FROM Predication WHERE Predication.document_collection = 'scientists' and extraction_type = 'PathIE'
GROUP BY predicate, relation
ORDER BY COUNT(*) DESC
LIMIT 500

SELECT predicate, relation, count(*)
FROM Predication WHERE Predication.document_collection = 'scientists' and extraction_type = 'PathIE'
and relation is not null
GROUP BY predicate, relation
ORDER BY COUNT(*) DESC
LIMIT 500



-- PubMed

SELECT subject_str, subject_id, subject_type, predicate_org, predicate, relation, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'PubMed' and subject_type = 'Drug' and object_type = 'Disease' and extraction_type = 'PathIE'
and relation = 'treats'
ORDER BY random()
LIMIT 100


SELECT subject_str, subject_id, subject_type, predicate_org, predicate, relation, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'PubMed' and extraction_type = 'PathIE'
ORDER BY random()
LIMIT 100

-- PathIE Statistics
SELECT predicate, relation, count(*)
FROM Predication WHERE Predication.document_collection = 'PubMed' and extraction_type = 'PathIE'
GROUP BY predicate, relation
ORDER BY COUNT(*) DESC
LIMIT 500

SELECT predicate, relation, count(*)
FROM Predication WHERE Predication.document_collection = 'PubMed' and extraction_type = 'PathIE'
and relation is not null
GROUP BY predicate, relation
ORDER BY COUNT(*) DESC
LIMIT 500