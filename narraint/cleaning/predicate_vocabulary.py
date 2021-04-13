def create_predicate_vocab():
    return dict(administered=['receiv*', 'administrat*'],
                associated=['associat*', 'contain', 'produce', 'convert', 'yield', 'isolate', 'generate', 'synthesize',
                            'grow', 'occures', 'evaluat*', 'augment', 'effect', 'develop*', 'affect', 'contribut*',
                            'involve', 'isa', 'same as', 'coexists with', 'process', 'part of', 'associate',
                            'play', 'limit', 'show', 'present', 'exhibit', 'find', 'form'],
                compares=['compar*', 'correlate*', 'correspond*'],
                induces=['stimulat*', 'increas*', 'potentiat*', 'enhanc*' , 'activat*', 'lead', 'cause', 'side effect*',
                         'adverse', 'complication*', 'drug toxicit*', 'drug injur*', 'upregulat*', 'up regulat*',
                         'up-regulat*'],
                decreases=['reduc*', 'lower*', 'attenuat*', 'mediate', 'downregulat*', 'down-regulat*', 'down regulat*'],
                interacts=['bind', 'interact*', 'target*', 'regulat*', 'block*'],
                metabolises=["metabol*"],
                inhibits=['disrupt*', 'suppres*', 'inhibit*', 'disturb*'],
                treats=['prevent*', 'use', 'improv*', 'promot*', 'sensiti*', 'aid', 'treat*', '*therap*'],
                method=['method*'])


PRED_TO_REMOVE = "PRED_TO_REMOVE"
DOSAGE_FORM_PREDICATE = "administered"
METHOD_PREDICATE = "method"
ASSOCIATED_PREDICATE = "associated"
ASSOCIATED_PREDICATE_UNSURE = ASSOCIATED_PREDICATE
