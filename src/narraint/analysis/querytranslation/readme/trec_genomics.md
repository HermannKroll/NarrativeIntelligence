

# TREC Covid

```
cd /home/kroll/jupyter/JCDL2023/
```

## Load Everything
```
python3 ~/NarrativeIntelligence/lib/KGExtractionToolbox/src/kgextractiontoolbox/document/load_document.py trec_genomics_2007_documents.json -c TREC_GENOMICS_FULLTEXTS
```



# Next, tag the documents with our PharmDictTagger
```
python3 ~/NarrativeIntelligence/lib/NarrativeAnnotation/src/narrant/preprocessing/dictpreprocess.py -c TREC_GENOMICS_FULLTEXTS --workers 15
```

# Next, tag the documents with GNormPlus
```
python3 ~/NarrativeIntelligence/lib/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/biomedical_entity_linking.py trec_genomics_2007_documents.json -c TREC_GENOMICS_FULLTEXTS --skip-load --workers 10 --gnormplus
```


# Clean the database 
```
-- Update Long Covid from MeSH Supplement to MeSH Descriptor
UPDATE public.Tag SET ent_id = 'MESH:D000094024' WHERE ent_id = 'MESH:C000711409' and ent_type = 'Disease';

-- Delete all Covid 19 Supplement Tags from TaggerOne
DELETE FROM public.Tag as t where t.ent_id = 'MESH:C000657245' and t.ent_type = 'Disease';

-- Delete far too general Disease Descriptor
DELETE FROM public.Tag as t WHERE t.ent_id = 'MESH:D004194' and t.ent_type = 'Disease';

-- Delete problematic targets (they are learned abbreviations, we can't change this at the moment)
DELETE FROM TAG where ent_type = 'Target' and ent_str IN ('in', 'or');
DELETE FROM TAG where ent_type = 'Target' and ent_str = 'state';

DELETE FROM TAG where ent_type = 'Tissue';

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
python3 ~/NarrativeIntelligence/src/narraint/extraction/pharmaceutical_pipeline.py -c TREC_GENOMICS_FULLTEXTS -et PathIE --workers 32 --relation_vocab /home/kroll/NarrativeIntelligence/resources/pharm_relation_vocab.json -bs 50000
```

# Clean & Apply Rules
```
python3 ~/NarrativeIntelligence/lib/KGExtractionToolbox/src/kgextractiontoolbox/cleaning/canonicalize_predicates.py --collection TREC_GENOMICS_FULLTEXTS --word2vec_model /home/kroll/workingdir/BioWordVec_PubMed_MIMICIII_d200.bin --relation_vocab ~/NarrativeIntelligence/resources/pharm_relation_vocab.json

python3 ~/NarrativeIntelligence/src/narraint/cleaning/pharmaceutical_rules.py --collection TREC_GENOMICS_FULLTEXTS
```