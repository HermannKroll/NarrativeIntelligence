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
METHOD = "Method"
LAB_METHOD = "LabMethod"

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
    DRUGBANK_CHEMICAL,
    METHOD,
    LAB_METHOD
)

DALL = {
    DOSAGE_FORM,
    DRUG,
    EXCIPIENT,
    PLANT_FAMILY,
    DRUGBANK_CHEMICAL,
    DISEASE,
    METHOD,
    LAB_METHOD
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
    DRUGBANK_CHEMICAL,
    METHOD,
    LAB_METHOD
)


TAG_TYPE_MAPPING = dict(
    DF=DOSAGE_FORM,
    DR=DRUG,
    DC=DRUGBANK_CHEMICAL,
    E=EXCIPIENT,
    PF=PLANT_FAMILY,
    C=CHEMICAL,
    MU=MUTATION,
    G=GENE,
    S=SPECIES,
    D=DISEASE,
    V=VARIANT,
    CL=CELLLINE,
    M=METHOD,
    LM=LAB_METHOD,
    A="ALL",
    DA="DALL"
)

DICT_TAG_TYPES = {"DF", "DR", "DC", "E", "PF", "DA", "D", "M", "LM"}

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
    DrugBankChemical=DRUGBANK_CHEMICAL,
    Method=METHOD,
    LabMethod=LAB_METHOD
)
