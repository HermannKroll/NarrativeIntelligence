DOSAGE_FORM = "DosageForm"
CHEMICAL = "Chemical"
MUTATION = "Mutation"
GENE = "Gene"
SPECIES = "Species"
DISEASE = "Disease"

ALL = (
    DOSAGE_FORM,
    CHEMICAL,
    MUTATION,
    GENE,
    SPECIES,
    DISEASE
)

TAG_TYPE_MAPPING = dict(
    DF=DOSAGE_FORM,
    C=CHEMICAL,
    M=MUTATION,
    G=GENE,
    S=SPECIES,
    D=DISEASE,
    A="ALL",
)
