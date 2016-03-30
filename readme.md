# Bing Async - Bing Python Wrapper

Wrapper around the Bing API, supporting asynchronous requests and proxies. All parameters supported by the API can be passed through the search function.
Convenience methods for general web search, English web search and news search are provided. Basic information is passed to a potentially configured logger.
Some of the most common errors returned by the API are transformed to understandable exceptions.

## Dependencies
- requests
- requests_futures
- urllib2
- lxml

## Usage

    #set up logging if necessary
    logging.basicConfig(filename='bing_async.log',level=logging.DEBUG)
    #initialize BingAsync with your Bing API key. You can also add a proxy dict as the second argument, e.g.  {'https' : 'https://myproxy.com', 'http' : 'http://myproxy.com'}
    bing_async = BingAsync('your-bing-api-key')
    
    #perform a web search
    result_as_json_string = bing_async.web_search(['Barack Obama', 'Cuba'], ['en-US'])
    
    #perform a web search with english for all english markets
    result_as_json_string = bing_async.web_search_english(['Barack Obama', 'Cuba'])
    
    #perform a news search 
    news_result_as_json_string = bing_async.news_search(['Barack Obama', 'Cuba'], ['World', 'Business'], ['en-US'])
    
    #perform a news search and get the result as xml/atom string. Quote the search terms
    news_result_as_atom_string = bing_async.news_search(['Barack Obama', 'Cuba'], ['World', 'Business'], ['en-US'], format='atom', quoting=True)

