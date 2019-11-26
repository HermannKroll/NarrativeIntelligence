## Narrative package

The narrative can be used to retrieve documents by a specific narrative.
Modify the `main.py` to create a narrative query. Then, insert the file with the
tagged documents and run

    python main.py tagged.txt
    
To create a narrative overlay you can use the classes `FactPattern`, `Event` and `Substory`.

    FactPattern(subject, predicate, object, subject_type, object_type)
    
    Event(action, entity, entity_type)
    
    Substory(fact1, fact2, ...)
    
The narrative overlay consists of transitions, which are 3-tuples.
The first and the thrid component can be `Substory`, `Event` or `FactPattern`.
The second component is the transistion between them.
    
    Narrative(
        (evt1, 'leads_to', evt2),
        ...
    )
 