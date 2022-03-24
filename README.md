# ena-analysis-submitter

Background
----------
This tool has been developed to handle submissions of Pathogen Analysis objects into ENA. Its intended use is as an additional component to integrated workflows in the [Data Hubs](http://europepmc.org/article/PMC/6927095).

The tool uploads analysis data files and carries out the submission to a project, although possible for general use, these projects are generally associated with certain Data Hubs, and therefore result in analysis being submitted to the Data Hub. Altogether the tool does the following:
- Creates appropriate analysis and submission XMLs required for programmatic submission to REST API.
- Carries out submission process to ENA using generated XMLs.
- Obtains and stores resulting assigned analysis accessions.

Usage
-----
The tool expects knowledge of the following, prior to usage:

1. A valid INSDC project/study accession (e.g. PRJ...)
2. One or more valid INSDC run accession(s), submitted to the project defined in 1 (e.g. ERR...). The script accepts multiple run accessions per analysis separated by commas or can read from a file with an accession per line.
3. One or more analysis files (full paths) to be submitted as part of the project in 1 and referring to the run(s) in 2. The script accepts multiple file names per analysis separated by commas or can be read from a file with a file per line.

`python3 analysis_submission.py -p <PROJECT_ACCESSION> -s <SAMPLE_ACCESSION(S)> -r <RUN_ACCESSION(S)> -f <FILE_NAME(S)> -a <ANALYSIS_TYPE> -au <WEBIN_USERNAME> -ap <WEBIN_PASSWORD> -t`

`python3 analysis_submission.py --help` for more information.

An output directory can be specified using `-o` flag, where the configuration file will be read from, and any output from the tool is stored. By default, the tool works from the current working directory.


To utilise the Docker container:
1. Pull from the docker repository:
   `docker pull davidyuyuan/ena-analysis-submitter:2.0`
   
2. Run the image container interactively:
   `docker run -it -v pathto/data:/usr/local/bin/data ena-analysis-submitter:1.0 python analysis_submission.py -p <PROJECT_ACCESSION> -s <SAMPLE_ACCESSION(S)> -r <RUN_ACCESSION(S)> -f <FILE_NAME(S)> -a <ANALYSIS_TYPE> -au <WEBIN_USERNAME> -ap <WEBIN_PASSWORD> -t`
   (Change `pathto/data` to specify the directory where your data files are held.)

Requirements
------------
- [Python3+](https://www.python.org/downloads/)
