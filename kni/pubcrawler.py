import urllib.request
from urllib.parse import quote
import xml.etree.ElementTree as ET
import time

from .khelper import chunks, printProgressBar


# Query pmid's from pmed
def pubmed_crawl_pmids(query, mail='ex@sample.com', tool='sampletool'):
	# wait amount specifc amount of time
	time.sleep(1)
	# url callls
	domain = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?email={}?tool={}?db=pubmed&term='.format(mail, tool)
	param = "&retmax=20000"

	# get ids for sentence (empty list)
	pmids = []
	try: 
		# encode sentence as url
		query_enc = quote(query, safe='')
		# construct final url
		url = domain + query_enc + param
		print("Crawling {}".format(url))
		# http get
		contents = urllib.request.urlopen(url).read()
		# convert result to xml
		xml_root = ET.fromstring(contents)
	
		# extract idlist of result
		for pmid_element in xml_root.find('IdList'):
			pmid = pmid_element.text
			# add all id's to sentence's pmids
			pmids.append(pmid)

		return pmids
	except:
		print("Error by crawling pmids for query: {}".format(sen))
		return None



# Crawl pubtator documents
# following formats are allowed "PubTator"; //"JSON"; // "BioC";
def pubtator_crawl_pubtator_documents(pmids, format):
	# wait amount specifc amount of time
	time.sleep(1)

	if format not in ['JSON', 'BioC', 'PubTator']:
		print('Format not supported: {}'.format(format))
		print('Supported formats: JSON, BioC, PubTator')
		return None
	if len(pmids) > 100 and format is not 'PubTator':
		print('Only in PubTator format more than 100 pmids are supported...')
		return None

	domain = 'https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/RESTful/tmTool.cgi/'
	concept_mode = 'BioConcept'
	

	if len(pmids) <= 100:
		# compute pmid str
		pmid_str = ''
		for pmid in pmids:
			pmid_str += pmid + ','
		pmid_str = pmid_str[:-1]

		url = '{}/{}/{}/{}'.format(domain,concept_mode,pmid_str,format)
		#print("Crawling {}".format(url))
		# http get
		contents = urllib.request.urlopen(url).read().decode('utf-8')
		return contents
	else:
		result_str = ''	
		# we assume format mode is PubTator (see check above)
		i = 1
		chunk_size = int(len(pmids)/100)+1 
		for c in chunks(pmids,100):
			# compute pmid str
			pmid_str = ''
			for pmid in c:
				pmid_str += pmid + ','
			pmid_str = pmid_str[:-1]
			# url call
			url = '{}/{}/{}/{}'.format(domain,concept_mode,pmid_str,format)
			#print("Crawling (Step: {}/{}): {}".format(i,chunk_size, url))
			printProgressBar(i, chunk_size, prefix='Crawling PMIDs from PubTator...')
			# http get
			result_str += urllib.request.urlopen(url).read().decode('utf-8')
			# wait amount specifc amount of time
			time.sleep(5)
			i += 1
		return result_str

def pubtator_crawl_pubtator_documents_with_query(query, mail='ex@sample.com', tool='sampletool'):
	print("Crawling PMIDs for query: {}".format(query))
	pmids = pubmed_crawl_pmids(query, mail, tool)
	print("{} PMIDs queried".format(len(pmids)))
	print("Crawling PubTator documents...")
	result = pubtator_crawl_pubtator_documents(pmids, 'PubTator')
	print("Crawling finished!")
	return result



