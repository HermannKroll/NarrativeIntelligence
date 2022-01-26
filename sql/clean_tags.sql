-- Delete all Covid 19 Supplement Tags from TaggerOne
DELETE FROM public.Tag as t where t.ent_id = 'MESH:C000657245' and t.ent_type = 'Disease';

-- Delete tags without entity ids
DELETE FROM public.Tag as t WHERE t.ent_id = '';

-- Clean all tags against OMIM
DELETE FROM public.tag as t WHERE t.ent_id like 'OMIM:%';

-- Delete all chemicals from TaggerOne
DELETE FROM public.tag as t WHERE t.ent_type = 'Chemical' and t.ent_id like 'MESH:%';