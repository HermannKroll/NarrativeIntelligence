DELETE FROM Tag where ent_id = 'MESH:C000657245' and ent_type = 'Disease';
DELETE FROM tag_inverted_index WHERE  entity_id = 'MESH:C000657245' and entity_type = 'Disease';

DELETE FROM Predication  where subject_id = 'MESH:C000657245' and subject_type = 'Disease';
DELETE FROM Predication  where object_id = 'MESH:C000657245' and object_type = 'Disease';
DELETE FROM predication_inverted_index  where subject_id = 'MESH:C000657245' and subject_type = 'Disease';
DELETE FROM predication_inverted_index  where object_id = 'MESH:C000657245' and object_type = 'Disease';
