enttype2colour = {
    "Disease": "#aeff9a",
    "Drug": "#ff8181",
    "Species": "#b88cff",
    "Excipient": "#ffcf97",
    "LabMethod": "#9eb8ff",
    "Chemical": "#fff38c",
    "Gene": "#87e7ff",
    "Target": "#1fe7ff",
    "Method": "#7897ff",
    "DosageForm": "#9189ff",
    "Mutation": "#8cffa9",
    "ProteinMutation": "#b9ffcb",
    "DNAMutation": "#4aff78",
    "Variant": "#ffa981",
    "CellLine": "#00bc0f",
    "SNP": "#fd83ca",
    "DomainMotif": "#f383fd",
    "Plant": "#dcfd83",
    "PlantFamily/Genus": "#dcfd83",
    "Strain": "#75c4c7",
    "Vaccine": "#c7767d",
    "HealthStatus": "#bbaabb",
    "Organism": "#00bc0f",
    "Tissue": "#dc8cff"
}


NOT_CONTAINED_COLOUR = "#FFFFFF"
NOT_CONTAINED_COLOUR_EDGE = "#E5E4E2"

CONCEPT_MAX_SUPPORT = 1000000

# Experimental Configuration (because first stage will always find input doc)
FS_DOCUMENT_CUTOFF = 100
FS_DOCUMENT_CUTOFF_HARD = FS_DOCUMENT_CUTOFF * 2

NODE_SIMILARITY_THRESHOLD = 0.3

GRAPH_WEIGHT = 0.6
BM25_WEIGHT = 0.4