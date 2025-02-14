/**
 * Color map of the narrative service entity types
 */
const TYPE_COLOR_MAP = {
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
    "CellLine": "#ce41ff",
    "SNP": "#fd83ca",
    "DomainMotif": "#f383fd",
    "Plant": "#dcfd83",
    "PlantFamily/Genus": "#dcfd83", // copy of plant
    "Strain": "#75c4c7",
    "Vaccine": "#c7767d",
    "HealthStatus": "#bbaabb",
    "Organism": "#00bc0f",
    "Tissue": "#dc8cff",
    "Other": "#717171" // default for unknown types
}

// alias for old scripts
const typeColorMap = TYPE_COLOR_MAP;
