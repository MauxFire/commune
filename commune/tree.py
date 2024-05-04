import commune as c
from typing import *
import os
from copy import deepcopy

class Tree(c.Module):
    ignore_prefixes = ['commune', 'modules']
    tree_folders_path = 'module_tree_folders'
    default_tree_path = c.libpath
    default_tree = default_tree_path.split('/')[-1]
    default_trees = [default_tree_path]
    def __init__(self, **kwargs):
        self.set_config(kwargs=locals())
        c.thread(self.run_loop)


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
                verbose:bool = False,
                max_age = 100000, **kwargs
                ) -> List[str]:
        
        module_tree = {}
        path = cls.resolve_path(f'{tree}/tree')
        max_age = 0 if update else max_age
        module_tree =  c.get(path, {}, max_age=max_age)
        tree_path = c.pwd()
        t1 = c.time()
        if len(module_tree) == 0:
            # get modules from each tree
            python_paths = c.get_module_python_paths(path=tree_path)
            # add the modules to the module tree
            module_tree = {c.path2simple(f, tree=tree): f for f in python_paths}
            # remove
            # to use functions like c. we need to replace it with module lol
            if cls.root_module_class in module_tree:
                module_tree[cls.root_module_class] = module_tree.pop(cls.root_module_class)

            c.put(path, module_tree)

        # cache the module tree
        if search != None:
            module_tree = {k:v for k,v in module_tree.items() if search in k}
        c.print(f'Loaded module tree in {c.time() - t1} seconds')
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
                c.print('Tree has changed, updating')
                self.tree(update=True)
            else:
                c.print('Tree has not changed')
            self.sleep(10)
        
    @classmethod
    def add_tree(cls, tree_path:str, **kwargs):

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
            tree = cls.default_tree
        return tree




    