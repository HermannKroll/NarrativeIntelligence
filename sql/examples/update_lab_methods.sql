UPDATE Tag
SET ent_type = 'LabMethod'
WHERE ent_id IN
('MESH:D000092165', 'MESH:D000092386', 'MESH:D000094443', 'MESH:D000094506', 'MESH:D000094542', 'MESH:D000095025', 'MESH:D000092025')
and ent_type = 'Method';


UPDATE Predication
SET subject_type = 'LabMethod'
WHERE subject_id IN
('MESH:D000092165', 'MESH:D000092386', 'MESH:D000094443', 'MESH:D000094506', 'MESH:D000094542', 'MESH:D000095025', 'MESH:D000092025')
and subject_type = 'Method';


UPDATE Predication
SET object_type = 'LabMethod'
WHERE object_id IN
('MESH:D000092165', 'MESH:D000092386', 'MESH:D000094443', 'MESH:D000094506', 'MESH:D000094542', 'MESH:D000095025', 'MESH:D000092025')
and object_type = 'Method';


UPDATE tag_inverted_index
SET entity_type = 'LabMethod'
WHERE entity_id IN
('MESH:D000092165', 'MESH:D000092386', 'MESH:D000094443', 'MESH:D000094506', 'MESH:D000094542', 'MESH:D000095025', 'MESH:D000092025')
and entity_type = 'Method';


UPDATE predication_inverted_index
SET subject_type = 'LabMethod'
WHERE subject_id IN
('MESH:D000092165', 'MESH:D000092386', 'MESH:D000094443', 'MESH:D000094506', 'MESH:D000094542', 'MESH:D000095025', 'MESH:D000092025')
and subject_type = 'Method';


UPDATE predication_inverted_index
SET object_type = 'LabMethod'
WHERE object_id IN
('MESH:D000092165', 'MESH:D000092386', 'MESH:D000094443', 'MESH:D000094506', 'MESH:D000094542', 'MESH:D000095025', 'MESH:D000092025')
and object_type = 'Method';
