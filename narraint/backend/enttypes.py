DOSAGE_FORM = "DosageForm"
CHEMICAL = "Chemical"
MUTATION = "Mutation"
GENE:str = "Gene"
SPECIES = "Species"
DISEASE = "Disease"
VARIANT = "Variant"
CELLLINE = "CellLine"

ALL = (
    DOSAGE_FORM,
    CHEMICAL,
    MUTATION,
    GENE,
    SPECIES,
    DISEASE,
    VARIANT,
    CELLLINE,
)

TAG_TYPE_MAPPING = dict(
    DF=DOSAGE_FORM,
    C=CHEMICAL,
    M=MUTATION,
    G=GENE,
    S=SPECIES,
    D=DISEASE,
    V=VARIANT,
    CL=CELLLINE,
    A="ALL",
)
