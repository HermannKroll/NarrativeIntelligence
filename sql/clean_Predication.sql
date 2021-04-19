UPDATE Predication SET predicate_canonicalized = 'associated_unsure' WHERE predicate_canonicalized = 'PRED_TO_REMOVE';
UPDATE PREDICATION SET subject_id = lower(subject_id) WHERE subject_type = 'Gene';
UPDATE PREDICATION SET object_id = lower(object_id) WHERE object_type = 'Gene';


DELETE FROM Predication WHERE predicate_canonicalized IS NULL;
DELETE FROM Predication WHERE predicate IN
	(SELECT distinct predicate FROM Predication GROUP BY predicate HAVING COUNT(*) < 50000);


DELETE FROM Predication Where subject_id = '' or object_id = '';

-- Delete two frequent methods
DELETE FROM Predication WHERE predicate_canonicalized = 'method' and (subject_id = 'E02.319' or subject_id = 'E02');
-- Delete Sprains and Strains
DELETE FROM Predication WHERE (subject_type = 'Disease' and subject_id = 'C26.844') or (object_type = 'Disease' and object_id = 'C26.844');

-- Rewrites the Predication table and deletes removed tuples
VACUUM FULL PREDICATION;
REINDEX TABLE PREDICATION;

VACUUM FULL SENTENCE;
