
SELECT ent_str, ent_id, ent_type, COUNT(*)
From Tag
where document_collection = 'PubMed'
GROUP BY ent_str, ent_id, ent_type
ORDER BY COUNT(*) DESC
LIMIT 500

-- Only Stanza (upper case entity types)
SELECT ent_str, ent_id, ent_type, COUNT(*)
From Tag
where document_collection = 'pollux' and ent_type = UPPER(ent_type)
GROUP BY ent_str, ent_id, ent_type
ORDER BY COUNT(*) DESC
LIMIT 500

-- Vocab Entity Linking
SELECT ent_str, ent_id, ent_type, COUNT(*)
From Tag
where document_collection = 'pollux' and ent_type <> UPPER(ent_type)
GROUP BY ent_str, ent_id, ent_type
ORDER BY COUNT(*) DESC
LIMIT 500


-- Delete short entity mentions
DELETE FROM Tag
WHERE document_collection = 'scientists' and length(ent_str) < 5;


-- Only Stanza (upper case entity types)
SELECT ent_str, ent_id, ent_type, COUNT(*)
From Tag
where document_collection = 'scientists' and ent_type = UPPER(ent_type)
GROUP BY ent_str, ent_id, ent_type
ORDER BY COUNT(*) DESC
LIMIT 500

-- Vocab Entity Linking
SELECT ent_str, ent_id, ent_type, COUNT(*)
From Tag
where document_collection = 'scientists' and ent_type <> UPPER(ent_type)
GROUP BY ent_str, ent_id, ent_type
ORDER BY COUNT(*) DESC
LIMIT 500