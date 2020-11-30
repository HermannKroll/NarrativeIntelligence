UPDATE Predication SET predicate_canonicalized = 'associated_unsure' WHERE predicate_canonicalized = 'PRED_TO_REMOVE';


DELETE FROM Predication WHERE predicate_canonicalized IS NULL;

-- Chemicals with only a single character are mostly wrong tagged
DELETE FROM PREDICATION WHERE (subject_str like '_' and subject_type = 'Chemical') or (object_str like '_' and object_type = 'Chemical');
DELETE FROM PREDICATION WHERE (subject_str like '__' and subject_type = 'Chemical') or (object_str like '__' and object_type = 'Chemical');

-- Rewrites the Predication table and deletes removed tuples
VACUUM FULL PREDICATION;


-- Clean the Sentence table
DELETE FROM SENTENCE WHERE id NOT IN (SELECT DISTINCT SENTENCE_ID FROM Predication);


VACUUM FULL SENTENCE;
