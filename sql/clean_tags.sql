-- Update Long Covid from MeSH Supplement to MeSH Descriptor
UPDATE public.Tag SET ent_id = 'MESH:D000094024' WHERE ent_id = 'MESH:C000711409' and ent_type = 'Disease';

-- Delete all Covid 19 Supplement Tags from TaggerOne
DELETE FROM public.Tag as t where t.ent_id = 'MESH:C000657245' and t.ent_type = 'Disease';

-- Delete problematic targets (they are learned abbreviations, we can't change this at the moment)
DELETE FROM TAG where ent_type = 'Target' and ent_str IN ('in', 'or');
DELETE FROM TAG where ent_type = 'Target' and ent_str = 'state';

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