# BioMedICUS

The BioMedical Information Collection and Understanding System (BioMedICUS) is a system for large-scale text analysis and processing of biomedical and clinical reports. The system is being developed by the Natural Language Processing and Information Extraction Program at the University of Minnesota Institute for Health Informatics.

This is a collaborative project that aims to serve biomedical and clinical researchers, allowing for customization with different texts.

More information about BioMedICUS can be found on our [website](https://nlpie.github.io/biomedicus). 

## Prerequisites

- [Python 3.6 or later](https://www.python.org/)
- [Java JDK 9.0 or later](https://adoptopenjdk.net/index.html). Note, you will need to have the ["java" command on the your "$PATH"](https://www.java.com/en/download/help/path.xml).
- [PyTorch](https://pytorch.org/get-started/locally/)

## Installation

[Installation instructions are available on our website](https://nlpie.github.io/biomedicus/installation).

## Deploying the default BioMedICUS Pipeline

The following command runs a script that will start up all of the BioMedICUS services for processing clinical notes:

```bash
biomedicus deploy --download-data
```

## Processing a directory of text files using BioMedICUS

After deploying BioMedICUS, you can process a directory of documents using the following command:

```bash
biomedicus run /path/to/input_dir /path/to/output_dir
```

This will process the documents in the directory using BioMedICUS and save the results as json-serialized MTAP Events to output directory.

## Contact

BioMedICUS is developed by the [NLP/IE Group](https://healthinformatics.umn.edu/research/nlpie-group) at the University of Minnesota Institute for Health Informatics. You can contact us at [nlp-ie@umn.edu](mailto:nlp-ie@umn.edu).
