def create_predicate_vocab():
    return dict(administered=["receive"],
                associated=["contain", "produce", "convert", "yield", "isolate", "generate", "synthesize", "grow",
                            "occures", "evaluate", "augment", "effect", "develop", "affect", "contribute", "involve",
                            "associated with", "isa", "same as", "coexists with", "process", "method of", "part of",
                            "associate", "correlate", "play role", "play", "limit"],
                compares=["compare with"],
                induces=["stimulate", "increase", "potentiate", "enhance", "activate", "higher",
                         "result", "lead", "causes"],
                decreases=["reduce", "lower", "attenuate", "mediate"],
                interacts=["bind", "interact", "target", "regulate"],
                metabolises=["metabolite", "metabolize", "metabolise", "metabolism", "metabol"],
                inhibits=["disrupt", "suppress", "inhibitor", "disturb"],
                treats=["prevents", "use", "improve", "promote", "sensitize", "sensitise", "aid"],
                PRED_TO_REMOVE=["show", "present", "exhibit", "find", "form"])


PRED_TO_REMOVE = "PRED_TO_REMOVE"
