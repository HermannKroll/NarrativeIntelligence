from narraint.entity.entity import Entity
from narraint.queryengine.query import GraphQuery, FactPattern
from narraint.queryengine.query_hints import ENTITY_TYPE_VARIABLE, PREDICATE_TYPING, VAR_TYPE


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
            return entity.entity_type

    @staticmethod
    def optimize_predicate_types_for_fact_pattern(fact_pattern: FactPattern) -> FactPattern:
        """
        Checks whether the fact pattern's predicate hurt the predicate typing constraint
        e.g. if diabetes (disease) treats metformin (drug) then this method flips the fact pattern
        to metformin treats diabetes
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
                return FactPattern(fact_pattern.objects, fact_pattern.predicate, fact_pattern.subjects)
            else:
                # We can skip this fact pattern because it will hurt the predicate type constraints
                return None
        else:
            # everything is fine
            return fact_pattern

    @staticmethod
    def optimize_predicate_types(graph_query: GraphQuery) -> GraphQuery:
        """
        Optimizes a GraphQuery based on the type-constraint for the predicates
        e.g. if diabetes (disease) treats metformin (drug) then this method flips the fact pattern
        to metformin treats diabetes
        :param graph_query: a graph query
        :return: a new optimized graph query object
        """
        optimized_query = GraphQuery()
        for fp in graph_query.fact_patterns:
            optimized_fp = QueryOptimizer.optimize_predicate_types_for_fact_pattern(fp)
            if optimized_fp:
                optimized_query.add_fact_pattern(optimized_fp)
        return optimized_query

    @staticmethod
    def optimize_query(graph_query: GraphQuery) -> GraphQuery:
        """
        Performs a simple query optimization
        1. remove redundant entity ids in subject or object
        2. remove duplicated fact patterns
        3. order fact patterns by pushing patterns with variables in the end
        4. change order of subject or object if predicate typy constraint is hurt
        :param graph_query:
        :return:
        """
        fact_patterns_with_var_count = []
        for fp in graph_query.fact_patterns:
            new_fp = FactPattern([], fp.predicate, [])
            variable_count = 0
            subject_ids = set()
            for sub in fp.subjects:
                if sub.entity_id not in subject_ids:
                    subject_ids.add(sub.entity_id)
                    new_fp.subjects.append(sub)
                    if sub.entity_type == ENTITY_TYPE_VARIABLE:
                        variable_count += 1
            object_ids = set()
            for obj in fp.objects:
                if obj.entity_id not in object_ids:
                    object_ids.add(obj.entity_id)
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
        optimized = QueryOptimizer.optimize_predicate_types(optimized)
        return optimized
