import re
import random

from .khelper import printProgressBar


def blocks(files, size=65536):
    while True:
        b = files.read(size)
        if not b: break
        yield b

def sample_pubtator_file(pubtator_filename, pubtator_filename_sampled, prob, debug=True, replace_special_char_in_entites = True, replace_special_char_in_entites_with = 'X', min_of_chemical_in_doc = 1, remove_entities_with_empty_cid = True, force_full_abstracts = True):
    i = 0
    with open(pubtator_filename_sampled, 'w', encoding='utf-8') as fout:
        # read puptator file as input
        with open(pubtator_filename, 'r', encoding='utf-8') as fp:
            # count amount of lines in file     
            print('Count fast amount of lines in file {}...'.format(pubtator_filename))  
            max_lines = sum(bl.count("\n") for bl in blocks(fp))
            print('Amount of lines: {}'.format(max_lines))
            printProgressBar(0, max_lines, prefix='Sampling pubtator file...')

            # min threshold for lines in doc
            if force_full_abstracts == True:
                min_lines = 1
            else:
                min_lines = 0

            # amount of documents inside file
            amount_of_docs = 0
            # amount of sampled docs
            amount_of_sampled_docs = 0

            # to print progress
            processed_lines = 0


            # amount of skipped documents
            skipped_regarding_min_chemicals = 0

            # process file noew
            lines = []
             # move fp to begin of file
            fp.seek(0,0)
            for line in fp:
                # count processed lines 
                processed_lines += 1
                if processed_lines % 5000 == 0:
                    printProgressBar(processed_lines, max_lines, prefix='Sampling pubtator file...')

                # read until empty line
                if len(line.rstrip()) == 0:
                    # do sampling
                    if random.random() < prob:
                        # if there are more than 1 line after last strip
                        if len(lines) > min_lines:
                            # count amount of chemicals to filter
                            amount_of_chemicals = 0
                            # write lines to new file
                            lines_to_write = []
                            amount_of_docs += 1
                            doc_id = re.split(r'\|', lines[0].rstrip(), maxsplit=1)[0]    
                            for lo in lines:
                                if remove_entities_with_empty_cid or min_of_chemical_in_doc > 0 or replace_special_char_in_entites:
                                    # check for line with entities
                                    if lo[0].isdigit():
                                        # ignore last \n
                                        l_split = lo[0:-1].split('\t')
                                        # if we found pmid start_span stop_span (3 numbers)
                                        # then this line is a entity line
                                        if l_split[0].isdigit() and l_split[1].isdigit() and l_split[2].isdigit():
                                            # does entity contain a special character in its text?
                                            if re.match(r'^[\w]+$', l_split[3]) == None: # some special character must be inside 
                                                # replace any special character in entity name by an replacement char 
                                                # i.e., Sim   vastatin - SimXXXvastatin
                                                to_replace = l_split[3]
                                                replaced = re.sub('[^0-9a-zA-Z]', replace_special_char_in_entites_with, to_replace)
                                                    
                                                # convert it to list for replacement
                                                replaced_list = list(replaced)

                                                # compute offset of doc_id length
                                                offset = len(doc_id) + 3 # add 3 characters for |t| or |a|

                                                # find place in file where entity name has to be replaced
                                                mention_start = int(l_split[1])
                                                mention_end = int(l_split[2])


                                                # replace entity name in line
                                                lo = lo.replace(to_replace, replaced)
                                                # extract title from first line and ignore offset and \n
                                                title = lines_to_write[0][offset:-1]
                                                # length of title
                                                title_len = len(title) + 1 # don't know why +1 but it is necessary

                                                # is entity between title and abstract? skip it
                                                if mention_start <= title_len and mention_end >= title_len:
                                                    if debug:
                                                        print('Mention between abstract and title - skipping it')
                                                        print('Mention: {}'.format(l_split))
                                                    continue

                                                # is entity located in title?
                                                elif mention_end <= title_len:
                                                    if debug:
                                                        print('Replacing in title {} at {} till {}'.format(''.join(replaced_list), mention_start, mention_end))
                                                
                                                    # replace entity in title
                                                    r_pos = 0
                                                    # convert string to list
                                                    s_list = list(lines_to_write[0])
                                                    for r_i in range(mention_start, mention_end):
                                                        s_list[r_i + offset] = replaced_list[r_pos]
                                                        r_pos += 1
                                                    # convert list to string
                                                    lines_to_write[0] = ''.join(s_list)
                                                else:
                                                    if debug:
                                                        print('Replacing in abstract {} at {} till {}'.format(''.join(replaced_list), mention_start, mention_end))
                                                    # replace entity in abstract
                                                    r_pos = 0
                                                    # convert string to list
                                                    s_list = list(lines_to_write[1])
                                                    for r_i in range(mention_start - title_len, mention_end - title_len):
                                                        s_list[r_i + offset] = replaced_list[r_pos]
                                                        r_pos += 1
                                                    # convert list to string
                                                    lines_to_write[1] = ''.join(s_list)

                                          
                                                if debug:
                                                    print('Replace {} with {}'.format(to_replace, replaced))

                                            # should we count amount of chemicals?
                                            if min_of_chemical_in_doc > 0:
                                                # we must force a chemical with a cid
                                                if l_split[4] == 'Chemical':
                                                    # if there is no 6 element or 6. element is empty
                                                    if len(l_split) == 5 or l_split[5] != '':
                                                        amount_of_chemicals += 1

                                            # should skip lines?
                                            if remove_entities_with_empty_cid:
                                                # then id is missing
                                                if len(l_split) == 5 or l_split[5] == '':
                                                    # skipping line with empy cid
                                                    if debug:
                                                        print('Skipping line with empty cid: {}'.format(l_split))
                                                    continue 
                                # write this line to output
                                lines_to_write.append(lo)
                      
                            # check if minimum is required
                            if min_of_chemical_in_doc > 0:
                                # if minimum should be used, then min chemicals must be in doc
                                if amount_of_chemicals >= min_of_chemical_in_doc:
                                    amount_of_sampled_docs += 1
                                    for lo in lines_to_write:
                                        fout.write(lo)   
                                    fout.write('\n')
                                else:
                                    skipped_regarding_min_chemicals += 1
                                    if debug:
                                        print('Skipping document {}, because only {} chemicals were found'.format(doc_id, amount_of_chemicals))
                            # min not required - just write file
                            else:
                                amount_of_sampled_docs += 1
                                for lo in lines_to_write:
                                    fout.write(lo)   
                                fout.write('\n')
                            # reset amount of chemicals
                            amount_of_chemicals = 0

                    # ready for next stored document
                    lines = []
                else:
                    lines.append(line)
    printProgressBar(max_lines, max_lines, prefix='Sampling pubtator file...')
    print('Skipped {} documents due to minimum chemical amount'.format(skipped_regarding_min_chemicals))     
    print('Saved {} (sampled) of {} (all) documents:'.format(amount_of_sampled_docs, amount_of_docs))   
    print('Sampling finished and saved at {}'.format(pubtator_filename_sampled))


def parse_pubtator_file(pubtator_filename):
        """

        :param content:
        :return:
        """
        doc_contents = []
        doc_ids = set()
        with open(pubtator_filename, 'r', encoding='utf-8') as fp:
            lines = []
            for line in fp:
                if len(line.rstrip()) == 0:
                    if len(lines) > 0:
                        # filter docs to target set
                        doc_id = re.split(r'\|', lines[0].rstrip(), maxsplit=2)[0]
                        if doc_id in doc_ids:
                            print('Warning: id {} already parsed!'.format(doc_id))
                        doc_ids.add(doc_id)  
                        doc_contents.append((doc_id,lines))
                        lines = []
                else:
                    lines.append(line)

        doc_content_with_annos = []
        for doc_id, content in doc_contents:
            #print(doc_id)
            #print(content)
            # First line is the title
            split = re.split(r'\|', content[0].rstrip(), maxsplit=2)
            doc_id = int(split[0])

           
            doc_text = split[2]

            # Second line is the abstract
            # Assume these are newline-separated; is this true?
            # Note: some articles do not have abstracts, however they still have this line
            doc_text += ' ' + re.split(r'\|', content[1].rstrip(), maxsplit=2)[2]

            # Rest of the lines are annotations
            annos = []
            for line in content[2:]:
                anno = line.rstrip('\n').rstrip('\r').split('\t')
                if anno[3] == 'NO ABSTRACT':
                    continue
                else:

                    # Handle cases where no CID is provided...
                    if len(anno) == 5:
                        anno.append("")

                    # Handle leading / trailing whitespace
                    if anno[3].lstrip() != anno[3]:
                        d = len(anno[3]) - len(anno[3].lstrip())
                        anno[1] = int(anno[1]) + d
                        anno[3] = anno[3].lstrip()

                    if anno[3].rstrip() != anno[3]:
                        d = len(anno[3]) - len(anno[3].rstrip())
                        anno[2] = int(anno[2]) - d
                        anno[3] = anno[3].rstrip()
                    annos.append(anno)

            annoset = {}
            annoset["annotations"] = annos
            # Form a Document
            doc_content_with_annos.append((doc_id,content,annoset))
            #print(len(annos))
        # Return the doc
        return doc_content_with_annos