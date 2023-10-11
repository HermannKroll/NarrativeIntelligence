from typing import List, Set

from narraint.queryengine.query import GraphQuery, FactPattern
from narraint.queryengine.query_hints import ENTITY_TYPE_VARIABLE, VAR_TYPE, MESH_ONTOLOGY, \
    PREDICATE_ASSOCIATED
from narrant.cleaning.pharmaceutical_vocabulary import SYMMETRIC_PREDICATES, PREDICATE_TYPING, \
    have_entities_correct_order
from narrant.entity.entity import Entity
from narrant.preprocessing.enttypes import CHEMICAL, DISEASE, DOSAGE_FORM


class QueryOptimizer:

    @staticmethod
    def _get_variable_type(entity: Entity) -> str:
        """
        Returns the type of the entity (if its a variable, the variable text will be parsed for a given type)
        :param entity: an entity object
        :return:
        """
        if entity.entity_type == ENTITY_TYPE_VARIABLE:
            var_type = VAR_TYPE.search(entity.entity_id)
            if var_type:
                var_type = var_type.group(1)
                return var_type
            # variable has no type, so all types are allowed
            return "VAR_ALL"
        else:
            if entity.entity_type == MESH_ONTOLOGY:
                if entity.entity_id.startswith('C'):
                    return DISEASE
                elif entity.entity_id.startswith('D'):
                    return CHEMICAL
                else:
                    return DOSAGE_FORM
            return entity.entity_type

    @staticmethod
    def _keep_only_entities_matching_constraints(entities: List[Entity], allowed_types: Set[str]):
        return list([e for e in entities if QueryOptimizer._get_variable_type(e) in allowed_types])

    @staticmethod
    def optimize_predicate_types_for_fact_pattern(fact_pattern: FactPattern) -> FactPattern:
        """
        Checks whether the fact pattern's predicate hurt the predicate typing constraint
        e.g. if diabetes (disease) treats metformin (drug) then this method flips the fact pattern
        to metformin treats diabetes
        remove subjects and objects which do not meet the type constraint
        :param fact_pattern: a given fact pattern
        :return: a fact pattern or None
        """
        if fact_pattern.predicate not in PREDICATE_TYPING:
            return fact_pattern
        a_subj_types, a_obj_types = PREDICATE_TYPING[fact_pattern.predicate]
        # var with all types is always allowed
        a_subj_types.add("VAR_ALL")
        a_obj_types.add("VAR_ALL")
        # get the types for the fact pattern's subjects and objects
        q_subs = {QueryOptimizer._get_variable_type(sub) for sub in fact_pattern.subjects}
        q_objs = {QueryOptimizer._get_variable_type(obj) for obj in fact_pattern.objects}
        # if queried either subject types or object types are not allowed...
        if len(q_subs.intersection(a_subj_types)) == 0 or len(q_objs.intersection(a_obj_types)) == 0:
            # then check whether changing them helps
            if len(q_subs.intersection(a_obj_types)) > 0 and len(q_objs.intersection(a_subj_types)) > 0:
                # yes - flip pattern
                return FactPattern(QueryOptimizer._keep_only_entities_matching_constraints(fact_pattern.objects,
                                                                                           a_subj_types),
                                   fact_pattern.predicate,
                                   QueryOptimizer._keep_only_entities_matching_constraints(fact_pattern.subjects,
                                                                                           a_obj_types))
            else:
                # We can skip this fact pattern because it will hurt the predicate type constraints
                return None
        else:
            # everything is fine, just filter
            return FactPattern(QueryOptimizer._keep_only_entities_matching_constraints(fact_pattern.subjects,
                                                                                       a_subj_types),
                               fact_pattern.predicate,
                               QueryOptimizer._keep_only_entities_matching_constraints(fact_pattern.objects,
                                                                                       a_obj_types))

    @staticmethod
    def optimize_predicate_types(graph_query: GraphQuery, and_mod=True) -> GraphQuery:
        """
        Optimizes a GraphQuery based on the type-constraint for the predicates
        e.g. if diabetes (disease) treats metformin (drug) then this method flips the fact pattern
        to metformin treats diabetes
        :param graph_query: a graph query
        :param and_mod: should the fact patterns be treated as being connected by AND (yes if true)? else OR
        :return: a new optimized graph query object
        """
        optimized_query = GraphQuery()
        for fp in graph_query.fact_patterns:
            optimized_fp = QueryOptimizer.optimize_predicate_types_for_fact_pattern(fp)
            if optimized_fp and optimized_fp.subjects and optimized_fp.objects:
                optimized_query.add_fact_pattern(optimized_fp)
            elif and_mod:
                return None  # query wont yield results - it will be empty
        return optimized_query

    @staticmethod
    def optimize_symmetric_predicate_fp(fact_pattern: FactPattern) -> FactPattern:
        """
        Optimizes a symmetric predicate (the arguments must be in the correct order)
        :param fact_pattern: a fact pattern
        :return: the fact pattern or None if it has the wrong order
        """
        if fact_pattern.predicate == PREDICATE_ASSOCIATED:
            # both directions are important - cannot optimize
            return fact_pattern
        if len(fact_pattern.subjects) > 1 or len(fact_pattern.objects) > 1:
            # multiple subjects or objects cannot be optimize
            return fact_pattern
        # do not optimize fact patterns with variables
        if fact_pattern.has_variable():
            return fact_pattern
        if fact_pattern.predicate in SYMMETRIC_PREDICATES:
            e_sub = next(iter(fact_pattern.subjects))
            e_obj = next(iter(fact_pattern.objects))
            # correct order - everything is fine
            if have_entities_correct_order(e_sub, e_obj):
                return fact_pattern
            else:
                # fact pattern has the wrong order - stop here
                return None
        return fact_pattern

    @staticmethod
    def optimize_symmetric_predicate(graph_query: GraphQuery, and_mod=True) -> GraphQuery:
        """
        Optimize a graph query by checking if the symmetric predicates have the correct order
        :param graph_query: a graph query
        :param and_mod: should the fact patterns be treated as being connected by AND (yes if true)? else OR
        :return: a graph query or none if all fact patterns are in the wrong order
        """
        if not graph_query:
            return None
        query_optimized = GraphQuery()
        for fp in graph_query.fact_patterns:
            fp_optimized = QueryOptimizer.optimize_symmetric_predicate_fp(fp)
            if fp_optimized and fp_optimized.subjects and fp_optimized.objects:
                query_optimized.add_fact_pattern(fp_optimized)
            elif and_mod:
                return None
        if len(query_optimized.fact_patterns) > 0:
            return query_optimized
        else:
            return None

    @staticmethod
    def optimize_query(graph_query: GraphQuery, and_mod=True) -> GraphQuery:
        """
        Performs a simple query optimization
        1. remove redundant entity ids in subject or object
        2. remove duplicated fact patterns
        3. order fact patterns by pushing patterns with variables in the end
        4. change order of subject or object if predicate type constraint is hurt
        :param graph_query:
        :param and_mod: should the fact patterns be treated as being connected by AND (yes if true)? else OR
        :return:
        """
        fact_patterns_with_var_count = []
        for fp in graph_query.fact_patterns:
            new_fp = FactPattern([], fp.predicate, [])
            variable_count = 0
            subject_ids = set()
            for sub in fp.subjects:
                if (sub.entity_id, sub.entity_type) not in subject_ids:
                    subject_ids.add((sub.entity_id, sub.entity_type))
                    new_fp.subjects.append(sub)
                    if sub.entity_type == ENTITY_TYPE_VARIABLE:
                        variable_count += 1
            object_ids = set()
            for obj in fp.objects:
                if (obj.entity_id, obj.entity_type) not in object_ids:
                    object_ids.add((obj.entity_id, obj.entity_type))
                    new_fp.objects.append(obj)
                    if obj.entity_type == ENTITY_TYPE_VARIABLE:
                        variable_count += 1

            # skip duplicated fact patterns
            already_included = False
            for fp2, _ in fact_patterns_with_var_count:
                if fp == fp2:
                    already_included = True
                    continue

            if not already_included:
                fact_patterns_with_var_count.append((new_fp, variable_count))

        # Sort the fact patterns by the var count ascending
        optimized = GraphQuery()
        for fp, var_count in sorted(fact_patterns_with_var_count, key=lambda x: x[1]):
            optimized.add_fact_pattern(fp)

        # optimize based on predicate-type constraint
        optimized = QueryOptimizer.optimize_predicate_types(optimized, and_mod)
        # optimize wrong symmetric predicate argument order
        # must be the last check!
        optimized = QueryOptimizer.optimize_symmetric_predicate(optimized, and_mod)
        # copy already existing additional entities if needed
        if optimized:
            optimized.entity_sets = graph_query.entity_sets
            optimized.terms = graph_query.terms
        return optimized
