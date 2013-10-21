import sys
sys.path.append("/Users/acoard/scrapy") #allows us to import Scrapy on school computers.
sys.path.append("/Users/acoard/beautifulsoup")
sys.path.append("/Users/acoard/pdfminer")
from bs4 import BeautifulSoup
#import scrapy
import urllib
import urllib2
import re
import datetime
import mechanize


from cStringIO import StringIO
from pdfminer.pdfinterp import PDFResourceManager, process_pdf
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams


#ISBN http://stackoverflow.com/questions/4893908/how-to-get-isbn-number-from-a-book-title-and-author-programmatically

regex_ISBN = re.compile('978(?:-?\d){10}')

def to_txt(pdf_path):
    input_ = file(pdf_path, 'rb')
    output = StringIO()

    manager = PDFResourceManager()
    converter = TextConverter(manager, output, laparams=LAParams())
    process_pdf(manager, converter, input_)

    return output.getvalue() 

def get_PDF(pdf_path, pdf_name):
	print "Downloading PDF."
	u = urllib2.urlopen(pdf_path)
	f = open(pdf_name, 'w+b')
	f.write(u.read())

def scrape_Blegen():
	"""
	This function properly scrapes the website, but there is a problem.  Blegen just have one long list of their books,
	sorted by date acquired.  There's no easy to way just add the "new" ones (although later I plan to see if new books are copies of the list on GDocs).
	Thus, this function only attempts to search the first page.  The commented out code below was for searching through all pages.

	"""


	Blegen_URL = 'http://ambrosia.ascsa.edu.gr:8991/F/?func=find-b&request=blg1013+or+gen1013+or+bsa1013&find_code=WRD&adjacent=N'
	html = urllib2.urlopen(Blegen_URL).read()
	soup = BeautifulSoup( html )
	tables = soup.find_all('table')
	data = scrape_Blegen_sub(soup)
	#is_another_page = bool(soup.find("img", {"alt":"Next Page"}))

	#THE BELOW CODE IS PARTIALLY WORKING, BUT GOING BACK THROUGH ALL THE PAGES JUST GOES BACK TO THEIR ORIGINAL BOOKS.
	#AS THEY ONLY SORT BOOKS BY YEAR, CAN'T REALLY COMPILE A MONTHLY REPORT.  

	# while is_another_page:
	# 	new_page_link = tables[3].a.get('href')
	# 	new_page = urllib2.urlopen(new_page_link).read()
	# 	soup = BeautifulSoup ( new_page )
	# 	is_another_page = bool(soup.find("img", {"alt":"Next Page"}))

	# 	data += scrape_Blegen_sub(soup)



	return data

def scrape_Blegen_sub(soup):
	#Only to be called by scrape_Blegen.
	tables = soup.find_all('table')
	table = tables[4] #Tables 0-3 are all navbar layout, [4] is content.
	output = []
	for tr in table.find_all('tr'):
		d = {}
		tr = tr.text.split('\n')
		author = tr[3].split(u'\xa0')[0]
		title = tr[4]#.split(u'\xa0')[0]
		d["author"] = author
		d["title"] = title
		output.append(d)
	if output[0] == {'title' : 'Title', 'author' : 'Author'}: #technical debt
		del output[0]
	return output

def scrape_JRA():
	#Returns a list of ISBNs.
	#TODO: Transform ISBNs to Author/Book info.
	JRA = 'http://www.journalofromanarch.com/booksreceived.html'
	JRA_base = 'http://www.journalofromanarch.com/'
	#First, must find links on page to the PDFs.  Find the most recent one, download it.
	html = urllib2.urlopen(JRA).read()
	soup = BeautifulSoup(html)
	links = soup.find(id="content").find_all('a')
	
	#Check that each link ends with .pdf
	links_to_pdf = []
	for link in links:
		is_pdf = bool(link.get('href')[-3:] == 'pdf')
		if is_pdf:
			links_to_pdf.append(link.get('href'))
	
	#The first item in the list is the most recent, so disregard the others.
	first_link = links_to_pdf[0]
	recent_pdf = JRA_base + first_link #affix pdf extension to domain name.
	u = urllib2.urlopen(recent_pdf)
	
	#PDFminer can't work off in memory files.  So, download the file then parse with to_txt()
	f = open(str(first_link), 'r+b') #taking str removes the u' unicode
	f.write(u.read())

	text = to_txt(str(first_link))
	text = text.split('USA\n')[1] #skips header
	regex = re.compile('978(?:-?\d){10}') #ISBN
	
	return regex_ISBN.findall(text)	 #IF this isn't working return to regex.findall(text)

def scrape_Sackler():
	#As this bot will run monthly, the bot must go through EACH of the 4 weekly pages and add them to the list.
	URL = 'http://www.bodleian.ox.ac.uk/sackler/collections/accessions/monograph-accessions'
	html = urllib2.urlopen(URL).read()
	soup = BeautifulSoup( html )
	content_div = BeautifulSoup(str(soup.find_all(attrs={'class':'content'}))) #parse by BeautifulSoup again in order to search it next step.
	
	#Pair links to PDFs with their weeks
	linksInTable = []
	for link in content_div.find_all('a'):
		linksInTable.append((link.text, link.get('href'))) #('wk xx', 'url.') nb: some wks are malformed.
	
	#Download last 4 links.	
	download_urls = []
	for i in [1,2,3,4]: 
		download_urls.append(linksInTable[len(linksInTable) - i][1])

	pdfs_to_scrape = []
	for i in xrange(len(download_urls)):
		pdf_name = download_urls[i].split('=')[1] + '.pdf'
		get_PDF(download_urls[i], pdf_name)

		pdfs_to_scrape.append(pdf_name)
		
		#PDF downloaded, begin scraping:
		text = to_txt(pdf_name)
		
		#REALLY MALFORMED.  EXPERIMENT WITH pdf2txt.py - properly setup via setup.py
	
	#After using pdf2txt.py - 
	#f = open('output.html')
	#html =  f.read()
	#soup = BeautifulSoup( html ) #spaces seem necssary?

	#divs = soup.find_all('div')
	#author_style = 'position:absolute; border: textbox 1px solid; writing-mode:lr-tb; left:181px'
	#book_style = 'position:absolute; border: textbox 1px solid; writing-mode:lr-tb; left:263px' #double check
	#list_of_authors = []
	#for div in divs:
		#if author_style in div.attrs['style']:
			#list_of_authors.append(div)

	#Problem: This would create two lists, of authors and books, and since I'm not sure the two line up perfectly (or will later)...
	#Maybe grab books off of something like 30 characters after author?
		
	return pdfs_to_scrape
	
def scrape_Prop():
	#Function is 100% operational.
	url = 'http://www.propylaeum.de/en/altertumswissenschaften/new-acquisitions/'
	br = mechanize.Browser()
	br.open(url)
	br.select_form(nr=1)
	#Form values
	br["EPOCHE"] = [".*"] #all time periods
	br["RAUM"] = ["G_rr"]  # Region: Roman Empire
	form_response = br.submit()
	
	soup = BeautifulSoup(form_response)
	output = scrape_Prop_sub(soup)

	#Check to see if there is another page of results:
	there_is_another_page = bool(soup.find_all('a')[-1].text.strip() == 'Anzeige weiterer Titel')
	while there_is_another_page:
		#follow link, repeat scraping, add to output
		base_url = 'http://mdz1.bib-bvb.de/'
		page_link = soup.find_all('a')[-1].get('href')
		url = base_url + page_link
		response = br.open(url)
		soup = BeautifulSoup(response)
		output += scrape_Prop_sub(soup)
		there_is_another_page = bool(soup.find_all('a')[-1].text.strip() == 'Anzeige weiterer Titel')
	return output

def scrape_Prop_sub(soup):
	#Function to be called in scrape_Prop() ONLY.  
	p_tags = soup.body.find_all('p')
	#Lots of malformed <p> tags, so check to make sure they aren't empty. 
	#NB: len(<p></p>) == 0, I think this is BeautifulSoup doing this.
	paras = [p for p in p_tags if len(p) > 1]
	#Create a list of dictionaries of author:title and return it.
	output = []
	for i in paras:
		d = {}
		d["author"] = i.b.text
		d["title"] = i.b.next_sibling.b.text
		d["ISBN"] = regex_ISBN.findall(str(i))
		output.append(d)
	return output


soup = scrape_Blegen()

def scraped_results():
	#Amalgamtes all the results into one function.
	#Prop's website is 404ing, I think it's their end - uncomment when it's back up.
	output = scrape_Blegen() + scrape_Prop()
	return output