UPDATE Predication SET predicate_canonicalized = 'associated_unsure' WHERE predicate_canonicalized = 'PRED_TO_REMOVE';
UPDATE PREDICATION SET subject_id = lower(subject_id) WHERE subject_type = 'Gene';
UPDATE PREDICATION SET object_id = lower(object_id) WHERE object_type = 'Gene';


DELETE FROM Predication WHERE predicate_canonicalized IS NULL;
DELETE FROM Predication WHERE predicate IN
	(SELECT distinct predicate FROM Predication GROUP BY predicate HAVING COUNT(*) < 50000);


DELETE FROM Predication Where subject_id = '' or object_id = '';

-- Rewrites the Predication table and deletes removed tuples
VACUUM FULL PREDICATION;
REINDEX TABLE PREDICATION;

VACUUM FULL SENTENCE;
