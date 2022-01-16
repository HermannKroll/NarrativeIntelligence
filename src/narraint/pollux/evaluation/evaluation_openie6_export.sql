
SELECT document_collection, extraction_type, count(*)
From Predication
WHERE extraction_type LIKE 'OPENIE6%'
GROUP by document_collection, extraction_type
ORDER BY  document_collection, extraction_type ASC




SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'PubMed' and extraction_type = 'OPENIE6_NF_NEW'
ORDER BY random()
LIMIT 100

SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'PubMed' and extraction_type = 'OPENIE6_EF_NEW'
ORDER BY random()
LIMIT 100

SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'PubMed' and extraction_type = 'OPENIE6_PF_NEW'
ORDER BY random()
LIMIT 100

SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'PubMed' and extraction_type = 'OPENIE6_SF_NEW'
ORDER BY random()
LIMIT 100





SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'pollux' and extraction_type = 'OPENIE6_NF_NEW'
ORDER BY random()
LIMIT 100

SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'pollux' and extraction_type = 'OPENIE6_EF_NEW'
ORDER BY random()
LIMIT 100

SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'pollux' and extraction_type = 'OPENIE6_PF_NEW'
ORDER BY random()
LIMIT 100

SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'pollux' and extraction_type = 'OPENIE6_SF_NEW'
ORDER BY random()
LIMIT 100



SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'scientists' and extraction_type = 'OPENIE6_NF_NEW'
ORDER BY random()
LIMIT 100

SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'scientists' and extraction_type = 'OPENIE6_EF_NEW'
ORDER BY random()
LIMIT 100

SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'scientists' and extraction_type = 'OPENIE6_PF_NEW'
ORDER BY random()
LIMIT 100

SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'scientists' and extraction_type = 'OPENIE6_SF_NEW'
ORDER BY random()
LIMIT 100

SELECT *
FROM document
WHERE collection = 'scientists'


SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'scientists' and Predication.document_id = '736' and extraction_type = 'OPENIE6_NF_NEW'
ORDER BY random()
LIMIT 100

SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'scientists' and Predication.document_id = '736' and extraction_type = 'OPENIE6_EF_NEW'
ORDER BY random()
LIMIT 100

SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'scientists' and Predication.document_id = '736' and extraction_type = 'OPENIE6_PF_NEW'
ORDER BY random()
LIMIT 100

SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'scientists' and Predication.document_id = '736' and extraction_type = 'OPENIE6_SF_NEW'
ORDER BY random()
LIMIT 100


SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'scientists' and Predication.document_id = '736' and extraction_type = 'OPENIE6_SF_NEW'
and subject_id = 'http://www.wikidata.org/entity/Q937'
ORDER BY random()
LIMIT 100


SELECT subject_str, subject_id, subject_type, predicate_org, predicate, object_str, object_id, object_type, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE Predication.document_collection = 'scientists' and subject_type = 'Person' and object_type = 'Award' and extraction_type = 'PathIE'
and subject_id = 'http://www.wikidata.org/entity/Q937'
ORDER BY random()
LIMIT 100