This folder contains top-level models and functions used in various parts of OpenAgua.

# Data (data.py)

The main purpose of this module is to help interact with Hydra Platform datasets, while providing important additional functionality.

Importantly, it helps to interpret custom, user-created functions in the data editor(s). In the future, this will be moved to a separate library and support multiple languages. In the meantime, it is here.

The general approach of the custom function parser is as follows (innards omitted):

```
class SYSTEM(object):
	
    def __init__(network=None, res_id=None, dates=None):
    
    	self.network = network
        self.res_id = res_id
        self.dates = dates
  
    	self.data = {}
        # This stores data that can be referenced later, in both time and space. The main purpose is to minimize repeated calls to data sources, especially when referencing other networks/resources/attributes within the project. While this needs to be recreated on every new evaluation or run, within each evaluation or run this can store as much as possible for reuse.

	def eval_data(...) [from existing code]
    	return ...

	def calculate(self, func, date):
    '''This calls the user-generated function (func)'''
        return func(date)
   
    def DATA(res_class, res_id, attr_name):
    '''This sets self.data from self.calculate. It is only used if a function contains self.DATA, which is added by a preprocessor'''
    
    	key = (res_class, res_id, attr_name)
    
    	if key not in self.data:
        	self.data[key] = eval_data(...)
        
        return self.data[key]

```