import numpy as np 
from tqdm import tqdm

class Cursor:
	def __init__(self,func,**kwargs):
		self.func=func
		self.kwargs=kwargs
		self.kwargs['is_cursor']=True
		self.n_pages=None
		self.n_items=np.inf
		self.tqdm_bar=False

	def pages(self,n_pages,tqdm_bar=False):
		self.n_pages=n_pages
		self.tqdm_bar=tqdm_bar
		if tqdm_bar:
			self.tqdm_bar=tqdm(desc='pages',total=n_pages,position=0)
		return self

	def items(self,n_items,tqdm_bar=False):
		self.n_items=n_items
		self.tqdm_bar=tqdm_bar
		if tqdm_bar:
			self.tqdm_bar=tqdm(desc='items',total=n_items,position=0)		
		return self

	def __iter__(self):
		n=0
		while True:
			for trya in range(3):
				try:
					has_more_items,cursor_value,cursor_name,res=self.func(**self.kwargs)
					break
				except Exception as e:
					er=e
					time.sleep(1)
			else:
				raise er

			if cursor_value is None:
				break
			if len(res)==0:
				break
			if self.n_pages:
				yield res
				n+=1
				if self.tqdm_bar:self.tqdm_bar.update(1)
				if n>=self.n_pages:
					if self.tqdm_bar:self.tqdm_bar.close()
					break
			else:
				for item in res:
					yield item
					n+=1
					if self.tqdm_bar:self.tqdm_bar.update(1)
					if n>=self.n_items:	break
				if n>=self.n_items:
					if self.tqdm_bar:self.tqdm_bar.close()
					break

			self.kwargs[cursor_name]=cursor_value
			if not has_more_items:
				if self.tqdm_bar:self.tqdm_bar.close()
				break