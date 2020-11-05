DOSAGE_FORM = "DosageForm"
DRUG = "Drug"
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
GENUS = "Genus"
STRAIN = "Strain"

ALL = (
    DOSAGE_FORM,
    DRUG,
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

# set of all tags which are supported by our taggers
ENT_TYPES_SUPPORTED_BY_TAGGERS = (
    DOSAGE_FORM,
    CHEMICAL,
    GENE,
    SPECIES,
    DISEASE
)


TAG_TYPE_MAPPING = dict(
    DF=DOSAGE_FORM,
    DR=DRUG,
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
    Drug=DRUG,
    Gene=GENE,
    Species=SPECIES,
    Mutation=MUTATION,
    CellLine=CELLLINE,
    Variant=VARIANT,
    ProteinMutation=PROTEINMUTATION,
    DNAMutation=DNAMUTATION,
    SNP=SNP,
    DosageForm=DOSAGE_FORM,
    DomainMotif=DOMAINMOTIF,
    Genus=GENUS,
    Strain=STRAIN
)
