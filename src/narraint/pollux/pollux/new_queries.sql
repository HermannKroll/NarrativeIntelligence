
SELECT document_collection, extraction_type, count(*)
From Predication
GROUP by document_collection, extraction_type
ORDER BY  document_collection, extraction_type ASC

SELECT subject_str, predicate_org, predicate, object_str, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE extraction_type = 'OPENIE6_NF_NVPF'
ORDER BY random()
LIMIT 100


SELECT subject_str, predicate_org, predicate, object_str, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE extraction_type = 'OPENIE6_EF_NVPF'
ORDER BY random()
LIMIT 100


SELECT subject_str, predicate, object_str, Sentence.text
FROM Predication JOIN Sentence ON (Predication.sentence_id = Sentence.id)
WHERE extraction_type = 'OPENIE6_NF_OVP'
LIMIT 1000


DELETE FROM Predication WHERE extraction_type like '%NVPF';
DELETE FROM Predication WHERE extraction_type like '%OVP';
#

SELECT document_collection, COUNT(*)
from TAG
group by document_collection

DELETE FROM TAG WHERE document_collection = 'scientists_benchmark' and length(ent_str) < 5

DELETE FROM TAG where document_collection = 'scientists_benchmark'
