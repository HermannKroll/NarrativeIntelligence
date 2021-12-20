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
WHERE document_collection = 'scientists'
GROUP BY ent_str, ent_id, ent_type
ORDER BY COUNT(*) DESC LIMIT 200;