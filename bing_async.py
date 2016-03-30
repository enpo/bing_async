# -*- coding: utf-8 -*-
import requests
from requests_futures.sessions import FuturesSession
from requests.auth import HTTPBasicAuth
from urllib2 import quote
import logging
from lxml import etree

logger = logging.getLogger(__name__)

class BingAsync(object):
    '''
    Wrapper around the Bing API, supporting asynchronous requests and proxies. All parameters supported by the API can be passed through the search function.
    Convenience methods for general web search, English web search and news search are provided. Basic information is passed to a potentially configured logger.
    Some of the most common errors returned by the API are transformed to understandable exceptions.
    '''
    API_URL = 'https://api.datamarket.azure.com/Bing/Search/v1/'

    ENGLISH_MARKETS = ['en-AU', 'en-CA', 'en-GB', 'en-ID', 'en-IE', 'en-IN', 'en-MY', 'en-NZ', 'en-PH', 'en-SG', 'en-US', 'en-XA', 'en-ZA']

    def __init__(self, api_key, proxies=None):
        '''
        Creates an instance of BingAsync.
        api_key: The API key of your Bing subscription. Can be acquired via https://datamarket.azure.com/dataset/bing/search.
        proxies: A proxy dict, e.g. {'https' : 'https://myproxy.com', 'http' : 'http://myproxy.com'}
        '''
        
        self.api_key = api_key
        self.proxies = proxies
        logger.debug('BingAsync initialized with API key "{}".'.format(self.api_key))
        
        if self.proxies:
            logger.debug('BingAsync initialized with proxies {}.'.format(str(proxies)))
    
    def _get_session(self):
        session = FuturesSession()
        session.auth = HTTPBasicAuth(self.api_key, self.api_key)
        if self.proxies and (self.proxies.get('http') or self.proxies.get('https')):
            session.proxies = proxies
        return session
 
    def _process_json_responses(self, responses):
        logger.debug("Processing responses, assuming JSON format.")
        results = []
        
        for response in responses:
            json_result = response.json()
            if (json_result):
                results.extend(json_result['d']['results'])
        
        return results    

    def _process_atom_responses(self, responses):
        logger.debug("Processing responses, assuming XML format.")
        root = None 
        
        for response in responses:
            if not root:
                #first response, create initial tree
                logger.debug("Creating root element.")
                root = etree.fromstring(response.content)
                root_ns =  root.nsmap[None]
                continue
            
            logger.debug("Adding entries..") 
            response_root = etree.fromstring(response.content)
            root_ns =  root.nsmap[None]
            for entry in response_root.iter("{" + root_ns + "}" + "entry"):            
                root.append(entry)

        #remove id and next elements as they are inaccurate when dealing with aggregated results
        if not root:
           raise Exception("Error trying to process XML. No root element defined.")

        if root.findall("{" + root_ns + "}" + 'id'):
           root.remove(root.findall("{" + root_ns + "}" +'id')[0])
        if root.findall("{" + root_ns + "}" + 'link'):
           root.remove(root.findall("{" + root_ns + "}" + 'link')[0])
        
        return etree.tostring(root, encoding='UTF-8')

    def _search_async(self, futures, format='json'):
        #collect responses
        responses = []
        
        for future in futures:
           result = future.result()
           if result.status_code == requests.codes.forbidden:
               raise Exception('Bing API key exhausted. Please raise your subscription limit or use a different key!.')
           elif result.status_code == requests.codes.service_unavailable:
               raise Exception('Reached maximum number of transactions per limit. Please wait some time before performing another query.')
           elif result.status_code != requests.codes.ok:
               raise Exception('Unknown error accessing Bing API. Status code: "{}"'.format(result.status_code))
           else:
               responses.append(result)

        if format == 'json':
            return self._process_json_responses(responses)
        elif format == 'atom':
            return self._process_atom_responses(responses)
        else:
            raise Exception('Unknown format "{}" provided. Please decided between "json" and "atom".'.format(format))

    def _build_most_basic_uri(self, search_type, search_terms, quoting=False):
        if quoting:
            logging.debug("Quoting search terms..")
            quoted_search_terms = []
            for search_term in search_terms:
                quoted_search_terms.append('"{}"'.format(search_term))
            logging.debug("Quoted search terms: {}".format(" ".join(quoted_search_terms)))
            search_terms = quoted_search_terms
   
        joined_and_escaped_query = quote(' '.join(search_terms))
        
        return self.API_URL + search_type + '?Query=%27' + joined_and_escaped_query + '%27'
                      
    def _add_parameter_to_urls(self, urls, parameter_name, parameter_values):
        new_urls = []
        for url in urls:
            for parameter_value in parameter_values:
                new_url = url + '&' + parameter_name + '=%27' + parameter_value + '%27'
                new_urls.append(new_url)
        return new_urls

    def _add_news_categories_to_urls(self, urls, news_categories):
        converted_news_categories = []
        for news_category in news_categories:
            converted_news_categories.append('rt_' + news_category)
        
        return self._add_parameter_to_urls(urls, 'NewsCategory', converted_news_categories)
        
    def search(self, search_terms, search_type, news_categories=[], markets=[], adult='Off', pages=10, results_per_page=15, format='json', quoting=False, latitude=None, longitude=None ):
        '''
        Searches the given search_type using Bing. Returns the result as a String in the specified format.

        search_terms: A list of strings representing the search terms.
        news_categories: A list of string representing the news categories to search for.
            Only needed for 'news' search. Empty array by default.
            Available categories include 'Business', 'Entertainment', 'Health', 'Politics',
            'Sports', 'US', 'World', 'Science_and_Technology'.
        markets: A list of markets like 'en-US', 'en-GB', 'fr-FR' etc. Default is no markets, i.e. Bing determines a sensible market from IP. 
        adult: Setting used for filtering sexually explicit content. Valid inputs are 'Off', 'Moderate' and 'Strict'. Default is 'Off'.
        pages: The number of pages to query, default is 10.
        format: The format in which to return results. Default is JSON.
        quoting: Whether you want the search terms to be quoted. This may improve accuracy for
            multiple word terms. Default is False.
        latitude: Latitude (north/south coordinate). Valid input values range from –90 to 90.
        longitude: Longitude (east/west coordinate). Valid input values range from –180 to 180.

        '''
        session = self._get_session()
        futures = []
        urls = []        

        basic_url = self._build_most_basic_uri(search_type, search_terms, quoting)
        urls.append(basic_url)

        if news_categories:
            urls = self._add_news_categories_to_urls(urls, news_categories)        
        
        if markets:
            urls = self._add_parameter_to_urls(urls, 'Market', markets)
        
        logging.debug("Querying {} pages per query containing {} results each.".format(pages, results_per_page)) 
        for url in urls: 
            for i in range(pages):
                skip = i * results_per_page
                current_url = url + '&$Top=' + str(results_per_page) + '&$Skip=' + str(skip) + '&$format=' + format
                     
                if latitude:
                    current_url = current_url + '&Latitude=' + latitude
                    
                if longitude:
                    current_url = current_url + '&Longitude=' + longitude
                    
                logging.debug("Calling Bing API with URL '{}'.".format(current_url))
                future = session.get(current_url)
                futures.append(future)

        return self._search_async(futures, format)
        
    def web_search(self, search_terms, markets, adult='Off', pages=10, format='json', quoting = False):
        '''
        Searches the web using Bing. Returns the result as a String in the specified format.

        search_terms: A list of strings representing the search terms.
        markets: A list of markets like 'en-US', 'en-GB', 'fr-FR' etc. Default is all english markets. May be an empty array, then the
                 Bing API will determine a value.
        adult: Setting used for filtering sexually explicit content. Valid inputs are 'Off', 'Moderate' and 'Strict'. Default is 'Off'.
        pages: The number of pages to query, default is 10.
        format: The format in which to return results. Default is JSON.
        quoting: Whether you want the search terms to be quoted. This may improve accuracy for
            multiple word terms. Default is False.
        '''

        return self.search(search_terms, 'Web', [], markets, adult, pages, 50, format, quoting)

    def web_search_english(self, search_terms, adult='Off', pages=10, format='json', quoting=False):
        '''
        Searches the english speaking web using Bing. Returns the result as a String in the specified format.

        search_terms: A list of strings representing the search terms.
        adult: Setting used for filtering sexually explicit content. Valid inputs are 'Off', 'Moderate' and 'Strict'. Default is 'Off'.
        pages: The number of pages to query, default is 10.
        format: The format in which to return results. Default is JSON.
        quoting: Whether you want the search terms to be quoted. This may improve accuracy for
            multiple word terms. Default is False.
        '''
        return self.web_search(search_terms, self.ENGLISH_MARKETS, adult, pages, format, quoting) 

    def news_search(self, search_terms, news_categories, markets, adult='Off', pages=10, format='json', quoting=False):
        '''
        Searches the news section of Bing. Returns the result as a String in the specified format.

        search_terms: A list of strings representing the search terms.
        news_categories: A list of string representing the news categories to search for.
            Available categories include 'Business', 'Entertainment', 'Health', 'Politics',
            'Sports', 'US', 'World', 'Science_and_Technology'.
        markets: A list of markets like 'en-US', 'en-GB', 'fr-FR' etc. Default is all english markets. May be an empty array, then the
                 Bing API will determine a value.
        pages: The number of pages to query, default is 10.
        format: The format in which to return results. Default is JSON.
        quoting: Whether you want the search terms to be quoted. This may improve accuracy for
            multiple word terms. Default is False.
        '''
        return self.search(search_terms, 'News', news_categories, markets, adult, pages, 15, format, quoting) 
