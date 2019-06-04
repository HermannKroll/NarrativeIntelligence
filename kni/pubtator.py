import re
import random

from .khelper import printProgressBar


def blocks(files, size=65536):
    """
    reads blocks from a file
    :param files: file
    :param size: size to read in one chunk
    :return:
    """
    while True:
        b = files.read(size)
        if not b: break
        yield b

def sample_pubtator_file(pubtator_filename, pubtator_filename_sampled, prob, debug=True,
                         replace_special_char_in_entites=True, replace_special_char_in_entites_with='X',
                         min_of_chemical_in_doc=1, min_of_genes_in_doc=0, remove_entities_with_empty_cid=True,
                         force_full_abstracts=True):
    """
    creates a sample of a pubtator file
    :param pubtator_filename: filename of the pubtator file
    :param pubtator_filename_sampled: filename to write
    :param prob: probabilistic - 0.1 means 10% of all docs are randomly selected
    :param debug: gives debug information for debugging
    :param replace_special_char_in_entites: default (true), removes any non [a-z0-9] characters in entities by replacing
    them in text
    :param replace_special_char_in_entites_with: default (X) character to replace any special character
    :param min_of_chemical_in_doc: default (1) how many chemical should be at least in a doc?
    :param min_of_genes_in_doc: default (0) how many genes should be at least in a doc?
    :param remove_entities_with_empty_cid: default (true) removes entites with no given ids
    :param force_full_abstracts: default (true) only select documents which contain a full abstract (not title only)
    :return: nothing
    """
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
            skipped_regarding_missing_title_or_abstract = 0
            skipped_regarding_min_chemicals = 0
            skipped_regarding_min_genes = 0

            skipped_ent_regarding_double_tagged = 0
            skipped_ent_regarding_no_id = 0
            skipped_ent_regarding_wrong_mention_pos = 0
            skipped_ent_regarding_min_length = 0
            skipped_ent_regarding_max_length = 0
            skipped_ent_regarding_wrong_detected_length = 0
            amount_correctly_shifted_entity_mentions = 0
            skipped_ent_regarding_id_negative = 0
            skipped_ent_regarding_type_missing = 0

            # process file noew
            lines = []
             # move fp to begin of file
            fp.seek(0,0)
            for line in fp:
                # preprocess - replace α, β and γ
                line = line.replace('α', 'a')
                line = line.replace('β', 'b')
                line = line.replace('γ', 'g')
                line = line.replace('δ', 'q')
                line = line.replace('Δ', 'd')
                line = line.replace('𝜃', 's')
                line = line.replace('Φ', 'F')
                line = line.replace('ε', 'e')
                line = line.replace('ρ', 'p')
                line = line.replace('κ', 'k')

                # count processed lines 
                processed_lines += 1
                if processed_lines % 500 == 0:
                    printProgressBar(processed_lines, max_lines, prefix='Sampling pubtator file...')

                # read until empty line
                if len(line.rstrip()) == 0:
                    # do sampling
                    if random.random() < prob:
                        # if there are more than 1 line after last strip and must have title and abstract
                        if len(lines) > min_lines and re.match(r'\d+\|t\|', lines[0]) and re.match(r'\d+\|a\|', lines[1]):
                            # count amount of chemicals to filter
                            amount_of_chemicals = 0
                            # count genes
                            amount_of_genes = 0
                            # write lines to new file
                            lines_to_write = []
                            amount_of_docs += 1
                            doc_id = re.split(r'\|', lines[0].rstrip(), maxsplit=1)[0]    
                            line_i = -1
                            if debug:
                                print('Beginning to process document {}'.format(doc_id))

                            for lo in lines:
                                line_i += 1
                                if lo == '###DEL###':
                                    continue # skip this line

                                if remove_entities_with_empty_cid or min_of_chemical_in_doc > 0 or replace_special_char_in_entites:
                                    # check for line with entities
                                    if lo[0].isdigit():
                                        # ignore last \n
                                        l_split = lo[0:-1].split('\t')
                                        # if we found pmid start_span stop_span (3 numbers)
                                        # then this line is a entity line
                                        if l_split[0].isdigit() and l_split[1].isdigit() and l_split[2].isdigit():
                                            if len(l_split) < 5:
                                                # entity type and id missing
                                                skipped_ent_regarding_type_missing += 1
                                                if debug:
                                                    print('Skipping entity {} (type and id missing)'.format((l_split[3])))
                                                continue
                                            # should skip lines?
                                            if remove_entities_with_empty_cid:
                                                # then id is missing
                                                if len(l_split) == 5 or l_split[5] == '':
                                                    # skipping line with empy cid
                                                    if debug:
                                                        print('Skipping line with empty cid: {}'.format(l_split))
                                                    skipped_ent_regarding_no_id += 1
                                                    continue
                                                # check also war negative id
                                                if l_split[5] == '-1':
                                                        skipped_ent_regarding_max_length += 1
                                                        if debug:
                                                            print('Skipping entity {} (id is -1)'.format(l_split[3]))
                                                        continue
                                            # if entity is very short
                                            if len(l_split[3]) < 3: 
                                                # entity is only 1 or 2 characters long - ingore it
                                                skipped_ent_regarding_min_length += 1
                                                if debug:
                                                    print('Skipping entity {} (only 1/2 characters long)'.format(l_split[3]))
                                                continue
                                            if len(l_split[3]) > 100:
                                                skipped_ent_regarding_max_length += 1

                                                if debug:
                                                    print('Skipping entity {} (> 100 characters not allowed)'.format(l_split[3]))
                                                continue

                                            # move entity mention position, if it does not fit
                                            if l_split[4] == 'Species' or l_split[4] == 'Gene':
                                                # compute offset of doc_id length
                                                offset = len(doc_id) + 3 # add 3 characters for |t| or |a|

                                                # find place in file where entity name has to be replaced
                                                mention_start = int(l_split[1])
                                                mention_end = int(l_split[2])

                                                # extract tagged entity
                                                entity_tagged_name = list(l_split[3])
                                                    
                                                # extract title from first line and ignore offset and \n
                                                title = lines_to_write[0][offset:-1]
                                                # length of title
                                                title_len = len(title) + 1 # don't know why +1 but it is necessary

                                                # position for checking in text
                                                r_i = 0
                                                if mention_start <= title_len and mention_end >= title_len:
                                                    if debug:
                                                        print('Mention between abstract and title - skipping it')
                                                        print('Mention: {}'.format(l_split))
                                                    continue
                                                # is entity located in title?
                                                elif mention_end <= title_len:
                                                    # convert string to list
                                                    s_list = list(lines_to_write[0])
                                                    # position in title
                                                    r_i = mention_start
                                                else:
                                                    # convert string to list
                                                    s_list = list(lines_to_write[1])
                                                    # position in abstract (consider title_len)
                                                    r_i = mention_start - title_len
                                                

                                                # assume entity fits to begin
                                                correct_entity_position_offset = 0
                                                # go through text and find entity at given position
                                                r_pos = 0

                                                # check if we can check two characters
                                                if len(entity_tagged_name) > 1:
                                                    if s_list[r_i + offset] != entity_tagged_name[r_pos] or s_list[r_i + offset + 1] != entity_tagged_name[r_pos + 1]:
                                                        # try to move entity one to left
                                                        if s_list[r_i + offset - 1] == entity_tagged_name[r_pos] and s_list[r_i + offset] == entity_tagged_name[r_pos + 1]:
                                                            # sucess, entity mention postition must be corrected 
                                                            correct_entity_position_offset = -1 # shift to left
                                                        elif s_list[r_i + offset + 1] == entity_tagged_name[r_pos] and s_list[r_i + offset + 2] == entity_tagged_name[r_pos + 1]:
                                                            correct_entity_position_offset = 1 # shift to right
                                                        else:
                                                            # if entity doesn't match to its related position, skip this entity
                                                            if debug:
                                                                print('Mismatch: {} != {} for ({} != {})'.format(s_list[r_i + offset], entity_tagged_name[r_pos],s_list[r_i + offset:r_i+offset+5],  l_split[3]))
                                                            wrong_mention_pos_found = True
                                                            skipped_ent_regarding_wrong_mention_pos += 1
                                                            # skip this entity, if it cannot be used
                                                            continue
                                                else:
                                                    # we can only check on position
                                                    if s_list[r_i + offset] != entity_tagged_name[r_pos]:
                                                        # try to move entity one to left
                                                        if s_list[r_i + offset - 1] == entity_tagged_name[r_pos]:
                                                            # sucess, entity mention postition must be corrected 
                                                            correct_entity_position_offset = -1 # shift to left
                                                        elif s_list[r_i + offset + 1] == entity_tagged_name[r_pos]:
                                                            correct_entity_position_offset = 1 # shift to right
                                                        else:
                                                            # if entity doesn't match to its related position, skip this entity
                                                            if debug:
                                                                print('Mismatch: {} != {} for ({} != {})'.format(s_list[r_i + offset], entity_tagged_name[r_pos],s_list[r_i + offset:r_i+offset+5],  l_split[3]))
                                                            wrong_mention_pos_found = True
                                                            skipped_ent_regarding_wrong_mention_pos += 1
                                                            # skip this entity, if it cannot be used
                                                            continue
                 
                                                # entity mention must be moved
                                                if correct_entity_position_offset != 0:
                                                    if debug:
                                                        print('Move entity mention {} (start: {}, end: {}) with a shift of {}'.format(l_split[3], mention_start, mention_end, correct_entity_position_offset))
                                                    # correct shift is allowed
                                                    amount_correctly_shifted_entity_mentions += 1
                                                    l_split[1] = str((int(l_split[1]) + correct_entity_position_offset))
                                                    l_split[2] = str((int(l_split[2]) + correct_entity_position_offset))

                                                    if len(l_split) == 5 or l_split[5] == '':
                                                        lo = '{}\t{}\t{}\t{}\t{}\n'.format(l_split[0], l_split[1], l_split[2], l_split[3], l_split[4])
                                                    else:
                                                        lo = '{}\t{}\t{}\t{}\t{}\t{}\n'.format(l_split[0], l_split[1], l_split[2], l_split[3], l_split[4], l_split[5])


                                                # Really scary: if the replaced word is also tagged as another entity 
                                                # then all other entities must be deleted - prefer genes over chemicals here
                                                # Example:
                                                #3560696 14674   14680   CYP2C9  Gene    1559
                                                #3560696 14674   14682   CYP2C9*3    Chemical    MESH:D065688
                                                e_line_i = 2
                                                for e_line in lines[2:]:
                                                    if e_line == '###DEL###':
                                                        # increment counter
                                                        e_line_i += 1
                                                        continue
                                                    # Dont replace yourself
                                                    if e_line_i != line_i:
                                                        e_split = e_line.split('\t')
                                                        # check whether both entites are start at the same pos?
                                                        # use the updated position
                                                        if int(l_split[1]) == int(e_split[1]) and l_split[4] == 'Gene' and e_split[4] == 'Chemical':
                                                            skipped_ent_regarding_double_tagged += 1
                                                            if debug:
                                                                print('Deleting line (conflicting start): {}'.format(lines[e_line_i]))
                                                            # mark that line as deleted
                                                            lines[e_line_i] = '###DEL###'
                                               
                                                    # increment counter
                                                    e_line_i += 1


                                              
                                            # does entity contain a special character in its text?
                                            if remove_entities_with_empty_cid and re.match(r'^[\w]+$', l_split[3]) == None: # some special character must be inside 
                                                # replace any special character in entity name by an replacement char 
                                                # i.e., Sim   vastatin - SimXXXvastatin
                                                to_replace = l_split[3]
                                                replaced = re.sub('[^0-9a-zA-Z]', replace_special_char_in_entites_with, to_replace)

                                                if debug:
                                                    print('Replacing {} with {}'.format(to_replace, replaced))


                                                # convert it to list for checking
                                                to_replace_list = list(to_replace)
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

                                                # entity is not as long as it should be
                                                if len(replaced_list) != (mention_end - mention_start):
                                                    skipped_ent_regarding_wrong_detected_length += 1
                                                    if debug:
                                                        print('Ignoring entity because the length is not tagged correctly')
                                                    continue

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

                       

                                                # Really scary: if the replaced word is also tagged as another entity 
                                                # then all other entity information must be updated
                                                # Example:
                                                #4521666 839 842 XX2 Chemical    MESH:D015232
                                                #4521666 951 954 bX2 Gene    28907
                                                e_line_i = 2
                                                for e_line in lines[2:]:
                                                    if e_line == '###DEL###':
                                                        continue
                                                    # Dont replace yourself
                                                    if e_line_i != line_i:   
                                                        e_split = e_line.split('\t')
                                                        # entity must be updated
                                                        if mention_start == int(e_split[1]) and mention_end == int(e_split[2]):
                                                            # update this entity line
                                                            new_entity_name = replaced
                                                            #print('Replace test v6: using {} in line {}'.format(new_entity_name, e_line))
                                                            # build line new (test if id is avaible or not)
                                                            if len(e_split) == 5 or e_split[5] == '':
                                                                e_l_new = '{}\t{}\t{}\t{}\t{}'.format(e_split[0], e_split[1], e_split[2], new_entity_name, e_split[4])
                                                            else:
                                                                e_l_new = '{}\t{}\t{}\t{}\t{}\t{}'.format(e_split[0], e_split[1], e_split[2], new_entity_name, e_split[4], e_split[5])
                                                            # update line
                                                            lines[e_line_i] = e_l_new
                                                    # increment counter
                                                    e_line_i += 1
                                          
                                                if debug:
                                                    print('Replaced {} with {}'.format(to_replace, replaced))

                                            # should we count amount of chemicals?
                                            if min_of_chemical_in_doc > 0:
                                                # we must force a chemical with a cid
                                                if l_split[4] == 'Chemical':
                                                    # if there is no 6 element or 6. element is empty
                                                    if len(l_split) == 5 or l_split[5] != '':
                                                        amount_of_chemicals += 1
                                            # should we count the amount of genes?
                                            if min_of_genes_in_doc > 0:
                                                if l_split[4] == 'Gene':
                                                    # if there is no 6 element or 6. element is empty
                                                    if len(l_split) == 5 or l_split[5] != '':
                                                        amount_of_genes += 1


                                # write this line to output
                                lines_to_write.append(lo)

                            should_skip = False
                            # check if minimum is required
                            if min_of_genes_in_doc > 0:
                                if amount_of_genes < min_of_genes_in_doc:
                                    skipped_regarding_min_genes += 1
                                    if debug:
                                        print('Skipping document {}, because only {} genes were found'.
                                                format(doc_id, amount_of_genes))
                                    should_skip = True
                            # check if minimum is required
                            if min_of_chemical_in_doc > 0:
                                if amount_of_chemicals < min_of_chemical_in_doc:
                                    skipped_regarding_min_chemicals += 1
                                    if debug:
                                        print('Skipping document {}, because only {} chemicals were found'.
                                                format(doc_id, amount_of_chemicals))
                                    should_skip = True

                            if not should_skip:
                                amount_of_sampled_docs += 1
                                for lo in lines_to_write:
                                    fout.write(lo)
                                fout.write('\n')
                    else:
                        skipped_regarding_missing_title_or_abstract += 1 
                        if debug:
                            print('Skipping document due to missing title or abstract')

                    # ready for next stored document
                    lines = []
                else:
                    lines.append(line)
    printProgressBar(max_lines, max_lines, prefix='Sampling pubtator file...')
    print('Skipped {} documents due to missing title or abstract'.format(skipped_regarding_missing_title_or_abstract))  

    if min_of_chemical_in_doc > 0:
        print('Skipped {} documents due to minimum chemical amount'.format(skipped_regarding_min_chemicals))
    if min_of_genes_in_doc > 0:
        print('Skipped {} documents due to minimum gene amount'.format(skipped_regarding_min_genes))

    print('Amount of correctly shifted entity mentions {}'.format(amount_correctly_shifted_entity_mentions))
    print('Skipped {} entites due to double tagged (genes are prefered)'.format(skipped_ent_regarding_double_tagged))  
    print('Skipped {} entites due to wrong entity detection position'.format(skipped_ent_regarding_wrong_mention_pos))  
    print('Skipped {} entites due to no id was found'.format(skipped_ent_regarding_no_id))  
    print('Skipped {} entites due to length (only 1 or 2 charcters)'.format(skipped_ent_regarding_min_length))  
    print('Skipped {} entites due to length (> 100 characters)'.format(skipped_ent_regarding_max_length))  
    print('Skipped {} entites due to wrong detection of their length'.format(skipped_ent_regarding_wrong_detected_length))
    print('Skipped {} entites due to missing type'.format(skipped_ent_regarding_type_missing))
    print('Skipped {} entites due to negative id (-1)'.format(skipped_ent_regarding_id_negative))

    print('Saved {} (sampled) of {} (all) documents:'.format(amount_of_sampled_docs, amount_of_docs))
    print('Sampling finished and saved at {}'.format(pubtator_filename_sampled))


def parse_pubtator_file(pubtator_filename):
        """
        parses a pubtator file
        :param content: content of a pubpator file
        :return: a list of tuples (doc_id, content, annotation_set)
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