DOSAGE_FORM = "DosageForm"
CHEMICAL = "Chemical"
MUTATION = "Mutation"
GENE = "Gene"
SPECIES = "Species"
DISEASE = "Disease"
VARIANT = "Variant"
CELLLINE = "CellLine"
SNP = "SNP"
PROTEINMUTATION = "ProteinMutation"
DNAMUTATION = "DNAMutation"
DOMAINMOTIF = "DomainMotif"

ALL = (
    DOSAGE_FORM,
    CHEMICAL,
    MUTATION,
    GENE,
    SPECIES,
    DISEASE,
    VARIANT,
    CELLLINE,
    SNP,
    PROTEINMUTATION,
    DNAMUTATION,
    DOMAINMOTIF
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

ENTITY_TYPES = dict(
    Chemical=CHEMICAL,
    Disease=DISEASE,
    Gene=GENE,
    Species=SPECIES,
    Mutation=MUTATION,
    CellLine=CELLLINE,
    Variant=VARIANT,
    ProteinMutation=PROTEINMUTATION,
    DNAMutation=DNAMUTATION,
    SNP=SNP,
    DosageForm=DOSAGE_FORM,
    DomainMotiv=DOMAINMOTIF
)
