import commune as c


class SubspaceModule(c.Module):

    def __init__(self, subspace=None, network='main', **kwargs):
        self.subspace = subspace or c.module('subspace')(network=network, **kwargs)


