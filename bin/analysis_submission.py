#!/usr/bin/env python

__author__ = "Nadim Rahman"

import argparse, hashlib, json, os, subprocess, sys, time, yaml
import xml.etree.ElementTree as ET
from datetime import datetime
from sra_objects import createWebinXML



def get_args():
    '''
    Define and obtain script arguments
    :return: Arguments object
    '''
    parser = argparse.ArgumentParser(prog='analysis_submission.py', formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="""
        + ============================================================ +
        |  European Nucleotide Archive (ENA) Analysis Submission Tool  |
        |                                                              |
        |  Tool to submit Pathogen analysis objects to an ENA project  |
        |  , mainly in the data hub context.                           |
        + =========================================================== +
        """)
    parser.add_argument('-p', '--project', help='Valid ENA project accession to submit analysis to (e.g. PRJXXXXXXX)', type=str, required=True)
    parser.add_argument('-s', '--sample_list', help='ENA sample accessions/s to link with the analysis submission, accepts a list of accessions (e.g. ERSXXXXX,ERSXXXXX) or a file with list of accessions separated by new line', required=False)
    parser.add_argument('-r', '--run_list', help='ENA run accession/s to link with the analysis submission, accepts a list of accessions (e.g. ERRXXXXX,ERRXXXXX) or a file with a list of accessions separated by new line', required=False)
    parser.add_argument('-f', '--file', help='Files of analysis to submit to the project, accepts a list of files (e.g. path/to/file1.csv.gz,path/to/file2.txt.gz)', type=str, required=True)
    parser.add_argument('-a', '--analysis_type', help='Type of analysis to submit. Options: PATHOGEN_ANALYSIS, COVID19_CONSENSUS, COVID19_FILTERED_VCF, PHYLOGENY_ANALYSIS', choices=['PATHOGEN_ANALYSIS', 'COVID19_CONSENSUS', 'COVID19_FILTERED_VCF', 'PHYLOGENY_ANALYSIS'], required=True)         # Can add more options if you wish to share more analysis types
    parser.add_argument('-au', '--analysis_username', help='Valid Webin submission account ID (e.g. Webin-XXXXX) used to carry out the submission', type=str, required=True)
    parser.add_argument('-ap', '--analysis_password', help='Password for Webin submission account', type=str, required=True)
    parser.add_argument('-o', '--output_location', help='A parent directory to pull configuration file and store outputs.', type=str, required=False)
    parser.add_argument('-as', '--asynchronous', help='Specify usage of the asynchronous Webin API for submissions. Options are true/t or false/f. Default: false/f', type=str.lower, choices=['true', 't', 'false', 'f'], required=False)
    parser.add_argument('-t', '--test', help='Specify whether to use ENA test server for submission. Options are true/t or false/f', type=str.lower, choices=['true', 't', 'false', 'f'], required=True)
    args = parser.parse_args()

    if args.test in ['true', 't']:
        args.test = True
    elif args.test in ['false', 'f']:
        args.test = False
    return args


def read_config(parent_dir):
    """
    Read in the configuration file
    :param parent_dir: The optional parent directory which houses the configuration file
    :return: A dictionary referring to tool configuration
    """
    config_file = os.path.join(parent_dir, 'config.yaml')
    with open(config_file) as f:
        configuration = yaml.safe_load(f)
    return configuration


def convert_to_list(string):
    """
    Convert a string to a list by a particular separator
    :param string: String to convert to list
    :return: List
    """
    if os.path.isfile(string):
        # Handle cases where the input string is a file location, reading a list from file
        with open(string) as f:
            li_read = f.read()
            li = li_read.splitlines()
    elif ',' in string:
        li = list(string.split(','))
    else:
        li = [string]
    return li


class file_handling:
    def __init__(self, file_list, file_type):
        self.file_list = file_list
        self.type = file_type

    def calculate_md5(self, file):
        """
        Calculate MD5 value for analysis data file to be submitted
        :param file: List of file(s) to be submitted
        :return: MD5 checksum value
        """
        print(file)
        return hashlib.md5(open(file, 'rb').read()).hexdigest()

    def construct_file_info(self):
        """
        Construct information on analysis data file(s) to be submitted
        :return: List of dictionary/ies consisting of file information
        """
        files_information = []
        for file in self.file_list:             # To be changed in future with dictionary of file types
            file_md5 = self.calculate_md5(file)  # Calculate an MD5 checksum value for file to be submitted
            if self.type == "COVID19_CONSENSUS":
                file_type = "fasta"
            elif self.type == "COVID19_FILTERED_VCF":
                file_type = "vcf"
            else:
                file_type = "other"
            file_information = {'name': file, 'type': file_type,
                                'md5_value': file_md5}  # Create dictionary of information
            files_information.append(file_information)
        return files_information


class upload_and_submit:
    def __init__(self, analysis_file, analysis_username, analysis_password, datestamp, parent_dir, api_service, test):
        self.analysis_file = analysis_file
        self.analysis_username = analysis_username
        self.analysis_password = analysis_password
        self.datestamp = datestamp
        self.parent_dir = parent_dir
        self.api_service = api_service
        self.test = test

    def upload_to_ENA(self, trialcount):
        """
        Upload data file(s) to ENA
        :param trialcount: Submission attempt number
        :return: Lists of successful file upload and list of any errors during upload
        """
        upload_errors = []
        upload_success = []

        # Process each file that needs to be submitted
        for file in self.analysis_file:
            command = "curl -T {}  ftp://webin.ebi.ac.uk --user {}:{}".format(file.get('name'), self.analysis_username, self.analysis_password)         # Command to upload file to Webin
            md5downloaded = "curl -s ftp://webin.ebi.ac.uk/{} --user {}:{} | md5sum | cut -f1 -d ' '".format(os.path.basename(file.get('name')), self.analysis_username, self.analysis_password)       # Command to check the MD5 value for the submitted file
            md5uploaded = file.get('md5_value')         # The MD5 calculated before the file upload
            print('-' * 100)
            print("CURL command:\n{}".format(command))
            print("MD5 Download command:\n{}".format(md5downloaded))
            print("MD5 uploaded:\n{}".format(md5uploaded))
            print('-' * 100)

            # Upload the file to Webin
            sp = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = sp.communicate()

            # Obtain the MD5 of the submitted file
            downloadmd5, downloaderr = subprocess.Popen(md5downloaded, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
            downloadmd5 = downloadmd5.decode().strip(' \t\n\r')

            print('*' * 100)
            print("--> {} {} {} <--".format(os.path.basename(file.get('name')), md5uploaded, downloadmd5))
            print('*' * 100)

            if md5uploaded == downloadmd5:
                # File integrity proven with matching MD5 values pre and post upload
                if out:
                    upload_success.append(file.get('name'))
                    print("Standard output of subprocess:")
                    print(out.decode())
                if err:
                    upload_success.append(file.get('name'))
                    print("Standard error of subprocess:")
                    print(err.decode())
                if sp.returncode != 0:
                    upload_errors.append({file.get('name'): err.decode()})
                    print(err.decode(), file=sys.stderr)
                print("Returncode of subprocess:", sp.returncode)
                return upload_success, upload_errors
            else:
                # Failed file integrity check, try at least 10 times before failure
                print("Analysis file {} may be corrupt, MD5 values do not match.".format(file.get('name')))
                time.sleep(10)
                trialcount += 1
                if trialcount > 5:
                    upload_errors.append({file.get('name'): err.decode()})
                    return upload_success, upload_errors
                else:
                    self.upload_to_ENA(trialcount)

    def save_accession(self, accession):
        """
        Retrieve the analysis accession of a successful result
        :param accession: Successfully submitted accession to be saved
        :return: Analysis accession from the receipt XML
        """
        successful_subs = os.path.join(self.parent_dir, 'successful_submissions.txt')
        with open(successful_subs, 'a') as f:
            for file in self.analysis_file:
                f.write(str(accession) + "\t" + str(file.get('name')) + "\t" + str(self.datestamp) + "\n")             # Saves the analysis accession, local path to file and date of submission

    def retrieve_xml_info(self, output, error, attempts, webin_loc):
        """
        Handle information from an XML output following submission
        :param output: Output requests object from submission
        :param error: Error output requests object from submission
        :param attempts: Number of attempts for submission
        :param webin_loc Full path of the Webin XML
        :return: Analysis accession or error message
        """
        root = ET.fromstring(output.decode())
        receipt_attributes = root.attrib
        if receipt_attributes.get('success') == 'true':  # If submission successful, obtain the analysis accession
            analysis_attributes = root[0].attrib  # Dictionary of XML attributes for the analysis object
            analysis_accession = analysis_attributes.get('accession')
            self.save_accession(analysis_accession)
            print('> Analysis ID: {}'.format(analysis_accession))
            return analysis_accession
        elif receipt_attributes.get('success') == 'false':  # Retry submission if unsuccessful
            time.sleep(10)
            attempts += 1
            if attempts > 3:
                analysis_accession = '> ERROR - Submission failed for {}_{}.xml: {}'.format(webin_loc, self.datestamp, error.decode())
                print(analysis_accession)
                return analysis_accession
            else:
                self.submission(attempts)

    def retrieve_json_info(self, output, error, attempts, webin_loc):
        """
        Handle information from JSON output following the submission
        :param output: Output requests object from submission
        :param error: Error output requests object from submission
        :param attempts: Number of attempts for submission
        :param webin_loc Full path of the Webin XML
        :return: Submission accession or error message
        """
        output = json.loads(output)         # Convert JSON into dictionary object
        try:
            submission_id = output['submissionId']
            self.save_accession(submission_id)
            print('> Submission ID: {}'.format(submission_id))
            return submission_id
        except:
            # If the output could not obtained, retry the submission
            time.sleep(10)
            attempts += 1
            if attempts > 3:
                submission_id = '> ERROR - Submission failed for {}_{}.xml: {}'.format(webin_loc, self.datestamp, error.decode())
                print(submission_id)
                return submission_id
            else:
                self.submission(attempts)

    def submission(self, attempts):
        """
        Carry out the submission
        :param attempts: The number of times the submission has been attempted
        :return: Command string and output
        """
        webin_loc = os.path.join(self.parent_dir, 'webin')          # Prefix for the name of the Webin XML with file path

        # Construct the appropriate submission command and run
        if self.test is True:
            command = 'curl -u {}:{} -X POST -H "accept: */*"  -H "Content-Type: multipart/form-data" -F "file=@{}_{}.xml;type=text/xml" "https://wwwdev.ebi.ac.uk/ena/submit/webin-v2/{}"'.format(
                self.analysis_username, self.analysis_password, webin_loc,
                self.datestamp, self.api_service)
        else:
            command = 'curl -u {}:{} -X POST -H "accept: */*"  -H "Content-Type: multipart/form-data" -F "file=@{}_{}.xml;type=txt/xml" "https://www.ebi.ac.uk/ena/submit/webin-v2/{}"'.format(
                self.analysis_username, self.analysis_password, webin_loc,
                self.datestamp, self.api_service)
        sp = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = sp.communicate()

        # Retrieve the resulting accession or attempt if it has failed
        if self.api_service == 'submit':
            accession = self.retrieve_xml_info(out, err, attempts, webin_loc)           # Analysis ID is retrieved
        elif self.api_service == 'submit/queue':
            accession = self.retrieve_json_info(out, err, attempts, webin_loc)          # Submission ID is retrieved which needs to be polled

        return command, out

    def submit_data(self):
        """
        Coordinate the upload of data files and submission to ENA
        :return: Upload of file(s) and curl command
        """
        trialcount = 0
        success, errors = self.upload_to_ENA(trialcount)      # Upload the data files to ENA prior to submission

        # Attempt the submission according to whether the upload was successful
        if not errors:
            attempts = 0
            command, out = self.submission(attempts)
            print("-" * 100)
            print("CURL submission command: \n")
            print(command)
            print("Returned output: \n")
            print(out.decode())
            print("-" * 100)
        else:
            print("File upload errors detected, aborted file upload:\n {}".format(errors))



if __name__=='__main__':
    args = get_args()       # Get script arguments

    if args.output_location is not None:
        # Check that the output directory exists, as this would be a prefix.
        if os.path.isdir(args.output_location) is not True:
            print('ERROR: Please provide a valid and existing output directory... Exiting.')
            sys.exit()
    else:
        args.output_location = '.'          # Default is the current working directory, unless specified
    configuration = read_config(args.output_location)           # Configuration from YAML

    # Handle indication of asynchronous Webin API
    if args.asynchronous in ['true', 't']:
        api_service = 'submit/queue'
    else:
        api_service = 'submit'

    # Handle any metadata references
    if args.sample_list is not None:            # Sample references are technically optional for analysis objects
        samples = convert_to_list(args.sample_list)
    else:
        samples = ""

    if args.run_list is not None:
        runs = convert_to_list(args.run_list)
    else:
        runs = ""

    if ',' in args.file:
        files = list(args.file.split(','))
    else:
        files = [args.file]

    # Define sections to include in analysis XML
    timestamp = datetime.now()
    analysis_date = timestamp.strftime("%Y-%m-%dT%H:%M:%S")        # Get a formatted date and time string

    # Create an appropriate alias to tag submissions
    if len(runs) == 1:
        alias = configuration['ALIAS'] + '_' + str(runs[0])
        if samples != "" and len(samples) == 1:         # If there is a single sample reference provided, add this to the alias
            alias += '_' + str(samples[0])
        alias += "_" + str(analysis_date)
    else:
        alias = configuration['ALIAS'] + '_' + str(analysis_date)

    # Obtain file information
    file_preparation_obj = file_handling(files, args.analysis_type)     # Instantiate object for analysis file handling information
    analysis_file = file_preparation_obj.construct_file_info()      # Obtain information on file/s to be submitted for the analysis XML

    # Create the Webin XML for submission
    create_xml_object = createWebinXML(alias, configuration, args.project, analysis_date, analysis_file, args.analysis_type, args.output_location, sample_accession=samples, run_accession=runs)
    webin_xml = create_xml_object.build_webin()

    # Upload data files and submit to ENA
    submission_obj = upload_and_submit(analysis_file, args.analysis_username, args.analysis_password, analysis_date, args.output_location, api_service, args.test)
    submission = submission_obj.submit_data()
