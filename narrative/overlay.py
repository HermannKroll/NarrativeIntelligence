class FactPattern:
    def __init__(self, s, p, o, type_s, type_o):
        self.s = s
        self.o = o
        self.p = p
        self.type_s = type_s
        self.type_o = type_o

    @property
    def vars(self):
        result = []
        if self.s.startswith("?"):
            result.append((self.s, self.type_s))
        if self.o.startswith("?"):
            result.append((self.o, self.type_o))
        return result

    @property
    def bounds(self):
        result = []
        if not self.s.startswith("?"):
            result.append((self.s, self.type_s))
        if not self.o.startswith("?"):
            result.append((self.o, self.type_o))
        return result

    def __str__(self):
        return "({}:{}, {}, {}:{})".format(self.s, self.type_s, self.p, self.o, self.type_o)


class Event:
    def __init__(self, label, entity, ent_type=None):
        self.label = label
        self.entity = entity
        self.ent_type = ent_type

    def __str__(self):
        return "({}, {}:{})".format(self.label, self.entity, self.ent_type)

    @property
    def vars(self):
        result = []
        if self.entity.startswith("?"):
            result.append((self.entity, self.ent_type))
        return result

    @property
    def bounds(self):
        result = []
        if not self.entity.startswith("?"):
            result.append((self.entity, self.ent_type))
        return result


class Substory:
    def __init__(self, *facts):
        self.facts = facts

    @property
    def vars(self):
        result = []
        for fact in self.facts:
            result += fact.vars
        return result

    @property
    def bounds(self):
        result = []
        for fact in self.facts:
            result += fact.bounds
        return result


class Narrative:
    """TODO: Currently ignoring ordering. Transitions are not implemented."""

    def __init__(self, *transitions):
        self.transitions = []
        self.facts = []
        self.events = []
        for t in transitions:
            self.add_transition(*t)

    def add_fact(self, fact):
        # TODO: Translate names to MESH
        self.facts.append(fact)

    def add_event(self, evt):
        # TODO: Translate names to MESH
        self.events.append(evt)

    def add_transition(self, head, transition, tail):
        # TODO: Translate names to MESH
        self.transitions.append((head, transition, tail))
        if isinstance(head, Substory):
            self.facts.extend(head.facts)
        else:
            self.events.append(head)
        if isinstance(tail, Substory):
            self.facts.extend(tail.facts)
        else:
            self.events.append(tail)

    @property
    def vars(self):
        result = set()
        for t in self.transitions:
            result = result.union(set(t[0].vars))
            result = result.union(set(t[2].vars))
        for f in self.facts:
            result = result.union(set(f.vars))
        for e in self.events:
            result = result.union(set(e.vars))
        return result

    @property
    def bounds(self):
        result = set()
        for t in self.transitions:
            result = result.union(set(t[0].bounds))
            result = result.union(set(t[2].bounds))
        for f in self.facts:
            result = result.union(set(f.bounds))
        for e in self.events:
            result = result.union(set(e.bounds))
        return result
