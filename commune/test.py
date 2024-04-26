import commune as c

class Test(c.Module):


    modules = ['key', 'namespace', 'server', 'subspace', 'module']

    @classmethod
    def test(cls, module=None, timeout=60):
        module = module or cls.module_path()
        if c.module_exists(module + '.test'):
            c.print('FOUND TEST MODULE', color='yellow')
            module = module + '.test'
        cls = c.module(module)
        self = cls()
        future2fn = {}
        fns = self.test_fns()
        for fn in fns:
            c.print(f'Testing {module}::{fn}', color='yellow')
            f = c.submit(getattr(self, fn), timeout=timeout)
            future2fn[f] = fn
        fn2result = {}
        for f in c.as_completed(future2fn, timeout=timeout):

            fn = future2fn[f]
            result = f.result()
            c.print(f'{fn} result: {result}')
            fn2result[fn] = result
        return fn2result
