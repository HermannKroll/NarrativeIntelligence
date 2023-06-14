from narraint.frontend.entity.entitytagger import EntityTagger
from narrant.entity.entityresolver import EntityResolver


def explain_concept_translation(concept):
    tagger = EntityTagger.instance()
    resolver = EntityResolver.instance()

    entities = tagger.tag_entity(concept)
    headings = []
    for entity in entities:
        heading = resolver.get_name_for_var_ent_id(entity.entity_id, entity.entity_type,
                                                   resolve_gene_by_id=False)
        if heading not in headings:
            headings.append(heading)
    headings.sort()

    if len(headings) > 1000:
        return [f'{len(headings)} entries found (too many to show)']

    # Remove headings that have the same prefix
    selected_prefixes = []
    for h in headings:
        already_selected = False
        for p in selected_prefixes:
            # we already selected that prefix
            if h.lower().startswith(p.lower()):
                already_selected = True
                break
        if not already_selected:
            # We did not consider it yet - take it
            selected_prefixes.append(h)

    headings = selected_prefixes
    heading_len = len(headings)
    if heading_len > 25:
        headings = headings[:25]
        headings.append(f"and {heading_len - 25} more")

    return headings


explain_concept_translation("Diabetes")
