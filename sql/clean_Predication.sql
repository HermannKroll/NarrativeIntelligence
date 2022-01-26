-- Update Dosage Form
UPDATE public.Predication SET relation = 'administered' WHERE subject_type = 'DosageForm' or object_type = 'DosageForm';

-- Update Method and LabMethod relation
UPDATE public.Predication SET relation = 'method' WHERE subject_type = 'Method' or object_type = 'Method';
UPDATE public.Predication SET relation = 'method' WHERE subject_type = 'LabMethod' or object_type = 'LabMethod';

-- Delete all symmetric predications (subject = object)
DELETE FROM public.Predication AS p WHERE p.subject_id = p.object_id and p.subject_type = p.object_type;

-- Update all non-relations
UPDATE public.Predication SET relation = 'associated' WHERE relation IS null;


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

DELETE FROM PREDICATION WHERE document_id NOT IN (SELECT distinct document_id FROM Document_Metadata_Service);

-- Rewrites the Predication table and deletes removed tuples
VACUUM FULL PREDICATION;
REINDEX TABLE PREDICATION;

VACUUM FULL SENTENCE;
