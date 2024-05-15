import commune as c
from typing import *
import os
from copy import deepcopy

class Tree(c.Module):
    tree_folders_path = 'module_tree_folders'
    default_tree_path = c.libpath
    default_tree_name = default_tree_path.split('/')[-1]
    default_trees = [default_tree_path]
    def __init__(self, **kwargs):
        self.set_config(kwargs=locals())
        # c.thread(self.run_loop)

    @classmethod
    def simple2path(cls, path:str, tree = None, **kwargs) -> bool:
        pwd = c.pwd()
        simple_path = path

        path = pwd + '/' + path.replace('.', '/')

        if os.path.isdir(path):
            paths_in_dir = os.listdir(path)
            for p in paths_in_dir:
                if p.endswith('.py'):
                    filename = p.split('.')[0].split('/')[-1]
                    if filename == simple_path:
                        path =  path +'/'+ p
                        return path
    
                    
        if os.path.exists(path + '.py'):
            path =  path + '.py'
        else:
            tree = cls.tree()
            is_module_in_tree = simple_path in tree
            tree = {k:v for k,v in tree.items() if simple_path in k}
            if not is_module_in_tree:
                tree = cls.tree(update=True)
            assert len(tree) > 0, f'No module found for {simple_path}'
            path = tree[simple_path] 
        
        return path
    

    
    def path2tree(self, **kwargs) -> str:
        trees = c.trees()
        path2tree = {}
        for tree in trees:
            for module, path in self.tree(tree).items():
                path2tree[path] = tree
        return path2tree
    

    @classmethod
    def tree(cls, tree = None,
                search=None,
                update = False,
                max_age = None, **kwargs
                ) -> List[str]:
        
        tree = cls.resolve_tree(tree)
        module_tree = {}
        path = cls.resolve_path(f'{tree}/tree')
        max_age = 0 if update else max_age
        module_tree =  c.get(path, {}, max_age=max_age)

        if len(module_tree) == 0:
            tree2path = cls.tree2path()
            if tree in tree2path:
                tree_path = tree2path[tree]
            else:
                tree_path = cls.default_tree_path
            # get modules from each tree
            python_paths = c.get_module_python_paths(path=tree_path)
            # add the modules to the module tree
            new_tree = {c.path2simple(f): f for f in python_paths}
            for k,v in new_tree.items():
                if k not in module_tree:
                    module_tree[k] = v
            # to use functions like c. we need to replace it with module lol
            
            if cls.root_module_class in module_tree:
                module_tree[cls.root_module_class] = module_tree.pop(cls.root_module_class)
            
            c.put(path, module_tree)

        # cache the module tree
        if search != None:
            module_tree = {k:v for k,v in module_tree.items() if search in k}
 
        return module_tree
    
    @classmethod
    def tree_paths(cls, update=False, **kwargs) -> List[str]:
        path = cls.tree_folders_path
        trees =   [] if update else c.get(path, [], **kwargs)
        if len(trees) == 0:

            trees = cls.default_trees
        return trees
    
    @classmethod
    def tree_hash(cls, *args, **kwargs):
        tree = cls.tree(*args, **kwargs)
        tree_hash = c.hash(tree)
        cls.put('tree_hash', tree_hash)
        return tree_hash

    @classmethod
    def old_tree_hash(cls, *args, **kwargs):
        return cls.get('tree_hash', None)

    @classmethod
    def has_tree_changed(cls, *args, **kwargs):
        old_tree_hash = cls.old_tree_hash(*args, **kwargs)
        new_tree_hash = cls.tree_hash(*args, **kwargs)
        return old_tree_hash != new_tree_hash

    def run_loop(self, *args, sleep_time=10, **kwargs):
        while True:
            c.print('Checking for tree changes')
            if self.has_tree_changed():
                self.tree(update=True)
            self.sleep(10)
        
    @classmethod
    def add_tree(cls, tree_path:str = './', **kwargs):

        tree_path = os.path.abspath(tree_path)

        path = cls.tree_folders_path
        tree_folder = c.get(path, [])
        tree_folder = list(set(tree_folder + cls.default_trees + [tree_path]))
        assert os.path.isdir(tree_path)
        assert isinstance(tree_folder, list)
        c.put(path, tree_folder, **kwargs)
        return {'module_tree_folders': tree_folder}
    
    @classmethod
    def rm_tree(cls, tree_path:str, **kwargs):
        path = cls.tree_folders_path
        tree_folder = c.get(path, [])
        tree_folder = [f for f in tree_folder if f != tree_path ]
        c.put(path, tree_folder)
        return {'module_tree_folders': tree_folder}


    

    @classmethod
    def pwd_tree(cls):
        tree2path   =  c.tree2path()
        pwd = c.pwd()
        return {v:k for k,v in tree2path.items()}.get(pwd, None)

    @classmethod
    def is_pwd_tree(cls):
        return c.pwd() == cls.default_tree_path
    
    @classmethod
    def trees(cls):
        tree_paths = cls.tree_paths()
        trees = [t.split('/')[-1] for t in tree_paths]
        return trees

    @classmethod
    def tree2path(cls, tree : str = None, **kwargs) -> str:
        tree_paths = cls.tree_paths(**kwargs)
        tree2path = {t.split('/')[-1]: t for t in tree_paths}
        if tree != None:
            return tree2path[tree]
        return tree2path
    

    @classmethod
    def resolve_tree(cls, tree:str=None):
        if tree == None:    
            tree = cls.default_tree_name
        return tree
    
    

    @classmethod
    def path2simple(cls, path:str, ignore_prefixes = ['commune', 'modules', 'commune.modules']) -> str:

        tree = cls.resolve_tree(None)

        path = os.path.abspath(path)

        pwd = c.pwd()

        if path.startswith(pwd):
            path = path.replace(pwd, '')
        elif path.startswith(c.libpath):
            path = path.replace(c.libpath, '')

        simple_path =  path.split(deepcopy(tree))[-1]

        if cls.path_config_exists(path):
            simple_path = os.path.dirname(simple_path)
        simple_path = simple_path.replace('.py', '')
        simple_path = simple_path.replace('/', '.')
        if simple_path.startswith('.'):
            simple_path = simple_path[1:]


        # compress nae
        chunks = simple_path.split('.')
        simple_chunks = []
        simple_path = ''
        for i, chunk in enumerate(chunks):
            if len(simple_chunks)>0:
                if chunk in simple_chunks:
                    continue
            simple_chunks += [chunk]
            simple_path = '.'.join(simple_chunks)

        # FOR DIRECTORY MODULES: remove suffixes (e.g. _module, module, etc. or )
        suffix =  simple_path.split('.')[-1]
        if '_' in suffix:
            suffix = simple_path.split('.')[-1]
            suffix_chunks = suffix.split('_')
            new_simple_path = '.'.join(simple_path.split('.')[:-1])
            if all([s.lower() in new_simple_path for s in suffix_chunks]):
                simple_path = '.'.join(simple_path.split('.')[:-1])
        if suffix.endswith('_module'):
            simple_path = '.'.join(simple_path.split('.')[:-1])
        # remove prefixes from commune
        for prefix in ignore_prefixes:
            if simple_path.startswith(prefix):
                simple_path = simple_path.replace(prefix, '')
        
        # remove leading and trailing dots
        if simple_path.startswith('.'):
            simple_path = simple_path[1:]
        if simple_path.endswith('.'):
            simple_path = simple_path[:-1]
        
        return simple_path


    
    @classmethod
    def path_config_exists(cls, path:str) -> bool:
        '''
        Checks if the path exists
        '''
        for ext in ['.yaml', '.yml']:
            if os.path.exists(path.replace('.py', ext)):
                return True
        return False
    

    @classmethod
    def find_classes(cls, path):
        code = c.get_text(path)
        classes = []
        for line in code.split('\n'):
            if all([s in line for s in ['class ', ':']]):
                new_class = line.split('class ')[-1].split('(')[0].strip()
                if new_class.endswith(':'):
                    new_class = new_class[:-1]
                if ' ' in new_class:
                    continue
                classes += [new_class]
        return [c for c in classes]
    
    @classmethod
    def simple2objectpath(cls, simple_path:str, **kwargs) -> str:
        path = cls.simple2path(simple_path, **kwargs)
        libpath = c.libpath
        if path.startswith(libpath):
            object_path = path.replace(libpath, '')
        else:
            pwd = c.pwd()
            object_path = path.replace(pwd, '')
        classes =  cls.find_classes(path)
        object_path = object_path.replace('.py', '')
        object_path = object_path.replace('/', '.')
        if object_path.startswith('.'):
            object_path = object_path[1:]
        object_path = object_path + '.' + classes[-1]
        return object_path
    
    




    