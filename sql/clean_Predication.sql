DELETE FROM Predication WHERE predicate_canonicalized IS NULL;
DELETE FROM Predication WHERE predicate_canonicalized = 'PRED_TO_REMOVE';

-- gel mistake error
DELETE FROM PREDICATION WHERE (subject_str like '%_gely' and subject_type = 'DosageForm') or (object_str like '%_gely' and object_type = 'DosageForm');


-- Chemicals with only a single character are mostly wrong tagged
DELETE FROM PREDICATION WHERE (subject_str like '_' and subject_type = 'Chemical') or (object_str like '_' and object_type = 'Chemical');
