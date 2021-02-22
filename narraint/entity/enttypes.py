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
EXCIPIENT = "Excipient"
PLANT_FAMILY = "PlantFamily"
DRUGBANK_CHEMICAL = "DrugBankChemical"

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
    DOMAINMOTIF,
    EXCIPIENT,
    PLANT_FAMILY,
    DRUGBANK_CHEMICAL
)

DALL = {
    DOSAGE_FORM,
    DRUG,
    EXCIPIENT,
    PLANT_FAMILY,
    DRUGBANK_CHEMICAL,
    DISEASE
}

# set of all tags which are supported by our taggers
ENT_TYPES_SUPPORTED_BY_TAGGERS = (
    DOSAGE_FORM,
    DRUG,
    EXCIPIENT,
    CHEMICAL,
    GENE,
    SPECIES,
    DISEASE,
    PLANT_FAMILY,
    DRUGBANK_CHEMICAL
)


TAG_TYPE_MAPPING = dict(
    DF=DOSAGE_FORM,
    DR=DRUG,
    DC=DRUGBANK_CHEMICAL,
    E=EXCIPIENT,
    PF=PLANT_FAMILY,
    C=CHEMICAL,
    M=MUTATION,
    G=GENE,
    S=SPECIES,
    D=DISEASE,
    V=VARIANT,
    CL=CELLLINE,
    A="ALL",
    DA="DALL"
)

DICT_TAG_TYPES = {"DF", "DR", "DC", "E", "PF", "DA", "D"}

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
    Strain=STRAIN,
    Excipient=EXCIPIENT,
    PlantFamily=PLANT_FAMILY,
    DrugBankChemical=DRUGBANK_CHEMICAL
)
