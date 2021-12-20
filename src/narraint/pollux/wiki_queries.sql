delete
from doc_tagged_by
where document_collection = 'scientists';

delete
from tag
    where document_collection = 'scientists'
    and ent_type in ('Academia of Science', 'Award', 'Belief', 'Country', 'Doctoral Degree', 'Person', 'Profession',
'Professional Society', 'Scientific Society', 'type');

delete
from document_translation
where document_collection = 'scientists';


select *
from document
where collection = 'scientists';

select *
from tag
where document_collection = 'scientists';

select count(*), ent_type
from tag
where document_collection = 'scientists'
group by ent_type;

SELECT ent_str, ent_id, ent_type, COUNT(*)
FROM Tag
WHERE document_collection = 'scientists' and ent_type = 'Person'
GROUP BY ent_str, ent_id, ent_type
ORDER BY COUNT(*) DESC LIMIT 200;


SELECT ent_type, COUNT(*)
FROM Tag
WHERE document_collection = 'scientists'
GROUP BY ent_type
ORDER BY COUNT(*) DESC LIMIT 200;

DELETE FROM Tag
WHERE document_collection = 'scientists'
and ent_str IN ('the', 'one', 'two', 'and', 'he', 'three', 'it', 'a', 'four', 'to', 'de',  'e', 'b', 'd');


DELETE FROM Predication
WHERE document_collection = 'scientists'
and (length(subject_str) < 5 or length(object_str) < 5);

-- Degree Received
SELECT Predication.*, Sentence.text
FROM Predication JOIN Sentence on (Predication.sentence_id = Sentence."id")
WHERE
relation = 'P512' -- is not null
and Predication.document_collection = 'scientists'
and subject_type = 'Person'  and object_str not in ('member','members', 'masters', 'doctor', 'diploma', 'degree')
ORDER by subject_type, relation, object_type

-- Member of
SELECT Predication.*, Sentence.text
FROM Predication JOIN Sentence on (Predication.sentence_id = Sentence."id")
WHERE
relation = 'P463' -- is not null
and Predication.document_collection = 'scientists'
and subject_type = 'Person'  and object_str not in ('member','members', 'masters', 'doctor')
ORDER by subject_type, relation, object_type

-- PathIE: persons that received an award
SELECT Predication.*, Sentence.text
FROM Predication JOIN Sentence on (Predication.sentence_id = Sentence."id")
WHERE
relation = 'P166' -- is not null
and Predication.document_collection = 'scientists'
and subject_type = 'Person' and object_type = 'Award' and object_str not in ('award','awards', 'diploma', 'winner')
ORDER by subject_type, relation, object_type


SELECT *
FROM Predication
WHERE extraction_type = 'OpenIE' and document_collection = 'scientists'
ORDER by subject_type, relation, object_type


SELECT *
FROM Predication
WHERe relation is not null;

DELETE FROM doc_processed_by_ie WHERE document_collection = 'scientists';
DELETE FROM predication WHERE document_collection = 'scientists';