# Narrative Intelligence Docker

This project can be used to perform Named Entity Recognition on documents in the PubTator format.

## Getting Started
The Docker image is contained inside the ``narraint.tar.gz`` file. Load the image into Docker.

```
docker load < narraint.tar.gz
```

## Usage
```
docker run -d -v /some/path:/input -v /some/other/path:/output narraint:latest -c PMC -t DF G
```

## Named Entity Recognition

Currently, the following entity types can be detected:
- Chemicals
- Diseases
- Genes
- Species
- Dosage Forms

The package provides APIs for several third-party taggers:

| Tagger | Entity types |
|-------------------|-------------------|
| TaggerOne 0.2.1 | Chemical, Disease |
| GNormPlusJava | Gene |
| DNorm 0.0.7 | Disease |
| tmChem 0.0.2| Chemical |
| DosageFormTagger | DosageForm
