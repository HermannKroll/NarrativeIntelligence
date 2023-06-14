

# TREC Covid

```
cd /home/kroll/jupyter/JCDL2023/
```

## Load Everything
```
python3 ~/NarrativeIntelligence/lib/KGExtractionToolbox/src/kgextractiontoolbox/document/load_document.py trec_covid_round5_abstract.json -c TREC_COVID_ABSTRACTS --artificial_document_ids

python3 ~/NarrativeIntelligence/lib/KGExtractionToolbox/src/kgextractiontoolbox/document/load_document.py trec_covid_round5_abstract_fulltext.json -c TREC_COVID_FULLTEXTS --artificial_document_ids
```



# Next, tag the documents with our PharmDictTagger
```
python3 ~/NarrativeIntelligence/lib/NarrativeAnnotation/src/narrant/preprocessing/dictpreprocess.py -c TREC_COVID_ABSTRACTS --workers 15 

python3 ~/NarrativeIntelligence/lib/NarrativeAnnotation/src/narrant/preprocessing/dictpreprocess.py -c TREC_COVID_FULLTEXTS --workers 15 --sections
```

```
python3 ~/NarrativeIntelligence/lib/NarrativeAnnotation/src/narrant/preprocessing/dictpreprocess.py -c TREC_COVID_ABSTRACTS --workers 15 --tag TI

python3 ~/NarrativeIntelligence/lib/NarrativeAnnotation/src/narrant/preprocessing/dictpreprocess.py -c TREC_COVID_FULLTEXTS --workers 15 --sections --tag TI
```

# Clean the database 
```
-- Update Long Covid from MeSH Supplement to MeSH Descriptor
UPDATE public.Tag SET ent_id = 'MESH:D000094024' WHERE ent_id = 'MESH:C000711409' and ent_type = 'Disease';

-- Delete all Covid 19 Supplement Tags from TaggerOne
DELETE FROM public.Tag as t where t.ent_id = 'MESH:C000657245' and t.ent_type = 'Disease';

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
```

# Extract Statements
```
python3 ~/NarrativeIntelligence/src/narraint/extraction/pharmaceutical_pipeline.py -c TREC_COVID_ABSTRACTS -et PathIE --workers 32 --relation_vocab /home/kroll/NarrativeIntelligence/resources/pharm_relation_vocab.json

python3 ~/NarrativeIntelligence/src/narraint/extraction/pharmaceutical_pipeline.py --sections -c TREC_COVID_FULLTEXTS -et PathIE --workers 32 --relation_vocab /home/kroll/NarrativeIntelligence/resources/pharm_relation_vocab.json
```