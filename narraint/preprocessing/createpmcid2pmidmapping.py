import argparse
import logging


# TODO: Is this a duplicate of "convertids.py"?
# TODO: Move this to "tools" or "pubmedutils"
def create_pmcid2pmid_index_from_tsv(input, output):
    first = False
    with open(input, "r") as f_in:
        with open(output, 'w') as f_out:
            for l in f_in:
                split = l.split(',')
                pmcid = split[8].replace('PMC', '')
                pmid = split[9]
                # skip missing ids
                if pmid == '':
                    continue
                if first:
                    f_out.write('{}\t{}'.format(pmcid, pmid))
                else:
                    f_out.write('\n{}\t{}'.format(pmcid, pmid))


def main():
    # here is a guide for conversion
    # https://www.ncbi.nlm.nih.gov/pmc/pmctopmid/
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--log", action="store_true")
    args = parser.parse_args()

    if args.log:
        logging.basicConfig()

    print('Converting csv file...')
    create_pmcid2pmid_index_from_tsv(args.input, args.output)
    print('output written in {}'.format(args.output))


if __name__ == "__main__":
    main()
