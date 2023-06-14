-- Update Long Covid from MeSH Supplement to MeSH Descriptor
UPDATE public.Tag SET ent_id = 'MESH:D000094024' WHERE ent_id = 'MESH:C000711409' and ent_type = 'Disease';

-- Delete all Covid 19 Supplement Tags from TaggerOne
DELETE FROM public.Tag as t where t.ent_id = 'MESH:C000657245' and t.ent_type = 'Disease';

-- Delete problematic targets (they are learned abbreviations, we can't change this at the moment)
-- DELETE FROM TAG where ent_type = 'Target' and ent_str IN ('in', 'or', 'state', 'april', 'transporter', 'transporters');

-- Deletes all targets where a term is mapped to another entity id, although we know that we would have a perfect match
-- (heading == term). Targets are identified by their heading
-- Deactivated at the moment
--DELETE
--FROM Tag
--WHERE ent_type = 'Target' and (lower(ent_str) <> lower(ent_id) and
--							   lower(ent_str) <> lower(ent_id || 's'))
--      and ent_str IN
--(
--		SELECT t1.ent_str
--		-- First get all targets distinctly
--		FROM (
--			SELECT DISTINCT ent_str, ent_id
--			FROM Tag
--			WHERE ent_type = 'Target'
--		) AS t1
--		-- Only consider ent_str that would directly map to an target heading (ent_id)
--		-- or entity id + 's'
--		WHERE lower(t1.ent_str) IN
--					(SELECT distinct lower(ent_str)
--					FROM Tag
--					WHERE ent_type = 'Target' and (lower(ent_str) = lower(ent_id)
--					                               OR lower(ent_str) = lower(ent_id || 's')))
--		-- Now group them and ensure that the term was linked to several targets
--		-- Although we already know that the there would be a perfect match
--		GROUP BY t1.ent_str
--		HAVING COUNT(*) > 1
-- );

-- Delete far too general Disease Descriptor
DELETE FROM public.Tag as t WHERE t.ent_id = 'MESH:D004194' and t.ent_type = 'Disease';

-- Delete far too general Strain and Strains Tags
DELETE FROM public.Tag as t WHERE t.ent_id = 'MESH:D013180' and t.ent_type = 'Disease' and t.ent_str = 'strain';
DELETE FROM public.Tag as t WHERE t.ent_id = 'MESH:D013180' and t.ent_type = 'Disease' and t.ent_str = 'strains';

-- Delete tags without entity ids
DELETE FROM public.Tag as t WHERE t.ent_id = '';

-- Clean all tags against OMIM
DELETE FROM public.tag as t WHERE t.ent_id like 'OMIM:%';

-- Delete all chemicals from TaggerOne
DELETE FROM public.tag as t WHERE t.ent_type = 'Chemical' and t.ent_id like 'MESH:%';