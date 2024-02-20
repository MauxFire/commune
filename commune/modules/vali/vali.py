import torch
import traceback
import commune as c
import concurrent


class Vali(c.Module):
    
    last_sync_time = 0

    def __init__(self,config=None,**kwargs):
        self.init_vali(config=config, **kwargs)


    def init_vali(self,config=None, **kwargs):

        config = self.set_config(config=config, kwargs=kwargs)
        c.print(config)
        self.config = c.dict2munch({**Vali.config(), **config})
        c.print(f'Vali config: {self.config}', color='cyan')
        # merge the config with the default config
        self.count = 0
        # we want to make sure that the config is a munch
        self.start_time = c.time()
        self.errors = 0
        self.sync_network()

        if 'subspace' in self.config.network:
            if '.' in self.config.network:
                chain = self.config.network.split('.')[-1]
            else: 
                chain = 'main'
            self.subspace = c.module('subspace')(network=chain)

        c.print(f'Vali config: {self.config}', color='cyan')
        if self.config.start:
            c.sleep(10)
            self.executor = c.module('thread.pool')(num_workers=self.config.num_workers, save_outputs=False)
            # launch a thread to run the vali
            c.thread(self.run)


    def subnet2modules(self, network:str='main'):
        subnet2modules = {}
        self.resolve_network(network)

        for netuid in self.netuids():
            subnet2modules[netuid] = self.modules(netuid=netuid)

        return subnet2modules


    def sync_network(self, network:str=None, search:str=None,  netuid:int=None, update: bool = False):
        
        self.namespace = c.namespace(search=self.config.search, network=self.config.network, netuid=self.config.netuid, update=update)
        self.n  = len(self.namespace)    
        self.addresses = [self.namespace.values()]     
        self.names = list(self.namespace.keys())
        self.address2name = {v: k for k, v in self.namespace.items()}    

        self.last_sync_time = c.time()
        return {'namespace': self.namespace}

    def score_module(self, module):
        '''
        params:
            module: module client
            kwargs : the key word arguments
        
        '''
        info = module.info()
        assert isinstance(info, dict), f'Response must be a dict, got {type(info)}'
        assert 'address' in info, f'Response must have an error key, got {info}'
        return {'success': True, 'w': 1}


    def eval_module(self, module:str):
        """
        The following evaluates a module server
        """
        # load the module stats (if it exists)

        my_info = self.info()
        
        module_info = self.load_module_info( module, {})
        if module in self.namespace:
            module_name = module
            module_address = self.namespace[module]
        else:
            module_address = module
            module_name = self.address2name.get(module_address, module_address)
        
        # emoji = c.emoji('hi')
        # c.print(f'Evaluating  {module_name}:{module_address} -->', color='cyan')

        if module_address == my_info['address']:
            return {'error': f'Cannot evaluate self {module_address}'}

        start_timestamp = c.time()

        seconds_since_called = c.time() - module_info.get('timestamp', 0)
        
        # TEST IF THE MODULE IS WAS TESTED TOO RECENTLY
        if seconds_since_called < self.config.max_staleness:
            # c.print(f'{prefix} [bold yellow] {module["name"]} is too new as we pinged it {staleness}(s) ago[/bold yellow]', color='yellow')
            r = {'error': f'{module_name} is too new as we pinged it {seconds_since_called}(s) ago'}
            return r

        try:
            # check the info of the module
            module = c.connect(module_address, key=self.key, virtual=True)

            if len(module_info) == 0:
                module_info = module.info(timeout=5)
            # this is where we connect to the client
            response = self.score_module(module)
            response['msg'] = f'{c.emoji("check")}{module_name} --> w:{response["w"]} {c.emoji("check")} '
        except Exception as e:
            response = {'error': c.detailed_error(e), 'w': 0, 
                        'msg': f'{c.emoji("cross")} {module_name} --> {e} {c.emoji("cross")}'  
                        }

        end_timestamp = c.time()        
        w = response['w']
        response['timestamp'] = c.time()
        # we only want to save the module stats if the module was successful
        module_info['count'] = module_info.get('count', 0) + 1 # update the count of times this module was hit
        module_info['w'] = module_info.get('w', w)*(1-self.config.alpha) + w * self.config.alpha
        module_info['history'] = (module_info.get('history', []) + [{'response': response, 'w': w}])[:self.config.max_history]
        module_info['timestamp'] = response['timestamp']
        module_info['start_timestamp'] = start_timestamp
        module_info['end_timestamp'] = end_timestamp
        module_info['latency'] = end_timestamp - start_timestamp
        emoji = c.emoji('checkmark') if response['w'] > 0 else c.emoji('cross')
        c.print(f'{emoji} {module_name}:{module_address} --> {w} {emoji}', color='cyan')
        self.save_module_info(module_name, module_info)
        self.count += 1

        return module_info

    @classmethod
    def resolve_storage_path(cls, network:str, tag:str=None):
        if tag == None:
            tag = 'base'
        return f'{tag}.{network}'
        
    def refresh_stats(self, network='main', tag=None):
        tag = self.tag if tag == None else tag
        path = self.resolve_storage_path(network=network, tag=tag)
        return self.rm(path)
    
    def resolve_tag(self, tag:str=None):
        return self.tag if tag == None else tag

    def vote(self, tag=None):


        c.print(f'Voting on {self.config.network} {self.config.netuid}', color='cyan')
        stake = self.subspace.get_stake(self.key.ss58_address, netuid=self.config.netuid)

        if stake < self.config.min_stake:
            result = {'success': False, 'message': f'Not enough  {self.key.ss58_address} ({self.key.path}) stake to vote, need at least {self.config.min_stake} stake'}
            return result
        

        tag = tag or self.tag
        module_infos = self.module_infos(network=self.config.network, keys=['name','uid', 'w', 'ss58_address'], tag=tag)
        votes = {
            'keys' : [],            # get all names where w > 0
            'weights' : [],  # get all weights where w > 0
            'uids': [],
            'timestamp' : c.time()
        }

        key2uid = self.subspace.key2uid()
        for info in module_infos:
            if 'ss58_address' in info and info['w'] > 0:
                votes['keys'] += [info['ss58_address']]
                votes['weights'] += [info['w']]
                votes['uids'] += [key2uid.get(info['ss58_address'], 0)]

        assert len(votes['uids']) == len(votes['weights']), f'Length of uids and weights must be the same, got {len(votes["uids"])} uids and {len(votes["weights"])} weights'

        self.subspace.vote(uids=votes['uids'], # passing names as uids, to avoid slot conflicts
                        weights=votes['weights'], 
                        key=self.key, 
                        network='main', 
                        netuid=self.config.netuid)

        self.save_votes(votes)

        return {'success': True, 'message': 'Voted', 'votes': votes }

    @property
    def last_vote_time(self):
        votes = self.load_votes()
        return votes.get('timestamp', 0)

    def load_votes(self) -> dict:
        default={'uids': [], 'weights': [], 'timestamp': 0, 'block': 0}
        votes = self.get(f'votes/{self.config.network}/{self.tag}', default=default)
        return votes

    def save_votes(self, votes:dict):
        assert isinstance(votes, dict), f'Weights must be a dict, got {type(votes)}'
        assert 'uids' in votes, f'Weights must have a uids key, got {votes.keys()}'
        assert 'weights' in votes, f'Weights must have a weights key, got {votes.keys()}'
        assert 'timestamp' in votes, f'Weights must have a timestamp key, got {votes.keys()}'
        storage_path = self.resolve_storage_path(network=self.config.network, tag=self.tag)
        self.put(f'votes/{self.config.network}/{self.tag}', votes)

    @classmethod
    def tags(cls, network='main', mode='stats'):
        return list([p.split('/')[-1].split('.')[0] for p in cls.ls()])

    @classmethod
    def paths(cls, network='main', mode='stats'):
        return list(cls.tag2path(network=network, mode=mode).values())

    @classmethod
    def tag2path(cls, network:str='main', mode='stats'):
        return {f.split('/')[-1].split('.')[0]: f for f in cls.ls(f'{mode}/{network}')}

    @classmethod
    def sand(cls):
        for path in cls.ls('votes'):
            if '/main.' in path:
                new_path = c.copy(path)
                new_path = new_path.replace('/main.', '/main/')
                c.mv(path, new_path)

    @classmethod
    def saved_module_paths(cls, network:str='subspace ', tag:str=None):
        path = cls.resolve_storage_path(network=network, tag=tag)
        paths = cls.ls(path)
        return paths

    @classmethod
    def saved_module_names(cls, network:str='main', tag:str=None):
        paths = cls.saved_module_paths(network=network, tag=tag)
        modules = [p.split('/')[-1].replace('.json', '') for p in paths]
        return modules
        
    @classmethod
    def module_infos(cls,
                     tag=None,
                      network:str='subspace', 
                    batch_size:int=20 , 
                    max_staleness:int= 1000000,
                    keys:str=None):

        paths = cls.saved_module_paths(network=network, tag=tag)   
        c.print(f'Loading {len(paths)} module infos', color='cyan')
        jobs = [c.async_get_json(p) for p in paths]
        module_infos = []

        # chunk the jobs into batches
        for jobs_batch in c.chunk(jobs, batch_size):
            results = c.gather(jobs_batch)
            # last_interaction = [r['history'][-1][] for r in results if r != None and len(r['history']) > 0]
            for s in results:
                if s == None:
                    continue
                if 'timestamp' in s:
                    s['staleness'] = c.timestamp() - s['timestamp']
                else:
                    s['staleness'] = 0
                if s['staleness'] > max_staleness:
                    continue
                if keys  != None:
                    s = {k: s.get(k,None) for k in keys}
                module_infos += [s]
        
        return module_infos
    

    def ls_stats(self):
        paths = self.ls(f'stats/{self.config.network}')
        return paths

    def load_module_info(self, k:str,default=None):
        default = default if default != None else {}
        path = self.resolve_storage_path(network=self.config.network, tag=self.tag) + f'/{k}'
        return self.get_json(path, default=default)


    def get_history(self, k:str, default=None):
        module_infos = self.load_module_info(k, default=default)
        return module_infos.get('history', [])
    
    def save_module_info(self,k:str, v):
        path = self.resolve_storage_path(network=self.config.network, tag=self.tag) + f'/{k}'
        self.put_json(path, v)


    @property
    def vote_staleness(self) -> int:
        return int(c.time() - self.last_vote_time)


    def run(self, vote=False):


        c.print(f'Running -> network:{self.config.network} netuid: {self.config.netuid}', color='cyan')
        c.new_event_loop()
        self.running = True
        futures = []
        vote_futures = []
        while self.running:

            if self.last_sync_time + self.config.sync_interval < c.time():
                c.print(f'Syncing network {self.config.network}', color='cyan') 
                self.sync_network()

            modules = c.shuffle(c.copy(self.names))
            c.print(len(modules))
            time_between_interval = c.time()
            module = c.choice(modules)

            # c.sleep(self.config.sleep_time)
            # rocket ship emoji
            c.print(f'{c.emoji("rocket")} {module} --> me {c.emoji("rocket")}', color='cyan')
            future = self.executor.submit(fn=self.eval_module, kwargs={'module':module}, return_future=True)
            futures.append(future)

            if self.vote_staleness > self.config.vote_interval:
                if not len(vote_futures) > 0 and 'subspace' in self.config.network:
                    vote_futures = [self.executor.submit(fn=self.vote, kwargs={}, return_future=True, timeout=self.config.vote_timeout)]

            if len(futures) >= self.config.max_futures:
                try:
                    for future in c.as_completed(futures, timeout=self.config.timeout):

                        try:
                            result = future.result()
                        except Exception as e:
                            result = {'error': c.detailed_error(e)}

                        futures.remove(future)
                        self.errors += 1
                        break
                except TimeoutError as e:
                    e = c.print('TimeoutError', color='red')

            
      
            if self.count % 10 == 0 and self.count > 0:
                stats =  {
                'total_modules': self.count,
                'lifetime': int(self.lifetime),
                'modules_per_second': int(self.modules_per_second()), 
                'vote_staleness': self.vote_staleness,
                'errors': self.errors,
                'vote_interval': self.config.vote_interval,
                'epochs': self.epochs,
                    }
                c.print(f'STATS  --> {stats}\n', color='white')


    @property
    def epochs(self):
        return self.count // self.n
    
           
    def check_score(self, module):
        module_name = module['name']

        return self.w.get(module_name, 0)
            
    def stop(self):
        self.running = False
        
    @classmethod
    def check_valis(cls, network='main', interval:int = 1, max_staleness:int=300, return_all:bool=True, remote=False):
        # get the up to date vali stats
        vali_stats = cls.stats(network=network, df=False, return_all=return_all, update=True)
        for v in vali_stats:
            if 'serving' not in v:
                continue
            if v['staleness'] > max_staleness:
                c.print(f'{v["name"]} is stale {v["staleness"]}s, restrting', color='red')
                c.serve(v['name'])
            if v['serving'] == False:
                c.print(f'{v["name"]} is not serving, restrting', color='red')
                address = c.get_address(v['name'])
                port = None
                if address != None:
                    port = int(address.split(':')[-1])
                c.serve(v['name'], port=port)

            c.print(f'{interval} ', color='green')
            c.sleep(interval)

            

    check_loop_name = 'vali::check_loop'
    @classmethod
    def check_loop(cls, interval=2, remote=True, **kwargs):
        if remote:
            kwargs['remote'] = False
            cls.remote_fn('check_loop', name=cls.check_loop_name, kwargs=kwargs)
            return {'success': True, 'message': 'Started check_vali_loop'}
        while True:
            c.print('Checking valis', color='cyan')
            c.print(cls.all_stats())
            cls.check_valis(**kwargs)
            c.sleep(interval)

    @classmethod
    def check_loop_running(cls):
        return c.pm2_exists(cls.check_loop_name)

    @classmethod
    def ensure_check_loop(self):
        if self.check_loop_running() == False:
            self.check_loop(remote=True)

    # @classmethod
    # def stake_spread(cls, modulenetwork='main'):
    #     subspace = c.module('subspace')(network=network)
    #     total_stake = self.subspace.total_stake(netuid=self.config.netuid)
    #     return stake / total_stake

    @classmethod
    def stats(cls,     
                    network='main', 
                    df:bool = True,
                    sortby:str=['name'], 
                    update:bool=True, 
                    cache_path:str = 'vali_stats',
                    return_all:bool=False):
        if return_all:
            return cls.all_stats(network=network, df=df)
        vali_stats = []
        if update == False:
            vali_stats = cls.get(cache_path, default=[])


        if len(vali_stats) == 0:
            module_path = cls.module_path()
            stats = c.stats(module_path+'::', df=False, network=network)
            name2stats = {s['name']: s for s in stats}
            for tag, path in cls.tag2path(mode='votes', network=network).items():
                v = cls.get(path)
                name = module_path + "::" +tag
                vote_info = name2stats.get(name, {})

                if vote_info.get('registered') == None:
                    continue
                if 'timestamp' in v:
                    vote_info['name'] = name
                    vote_info['n'] = len(v['uids'])
                    vote_info['timestamp'] = v['timestamp']
                    vote_info['avg_w'] = sum(v['weights']) / (len(v['uids']) + 1e-8)
                    vali_stats += [vote_info]
            cls.put(cache_path, vali_stats)    

        
        for v in vali_stats:
            v['staleness'] = int(c.time() - v['timestamp'])

            del v['timestamp']


        if df:
            vali_stats = c.df(vali_stats)
            # filter out NaN values for registered modules
            # include nans  for registered modules
            if len(vali_stats) > 0:
                vali_stats.sort_values(sortby, ascending=False, inplace=True)
            
        return vali_stats

    @classmethod
    def all_stats(cls, network='main', df:bool = True, sortby:str=['name'] , update=True, cache_path:str = 'vali_stats'):
        modules = c.modules('vali')
        all_vote_stats = []
        for m in modules:
            if not m.startswith('vali'):
                continue 
            try:
                # WE ONLY WANT TO UPDATE THE STATS IF THE MODULE IS RUNNING
                m_vote_stats = c.module(m).stats(df=False, network=network, return_all=False, update=update)
                c.print(f'Got vote stats for {m} (n={len(m_vote_stats)})')
                if len(m_vote_stats) > 0:
                    all_vote_stats += m_vote_stats
            except Exception as e:
                e = c.detailed_error(e)
                c.print(c.dict2str(e), color='red')
                continue
                
        if df == True:
            df =  c.df(all_vote_stats)
            # filter out NaN values for registered modules
            df.sort_values(sortby, ascending=False, inplace=True)
            return df
        return all_vote_stats

    @property
    def lifetime(self):
        return c.time() - self.start_time

    def modules_per_second(self):
        return self.count / self.lifetime

    @classmethod
    def test(cls, **kwargs):
        kwargs['num_workers'] = 0
        kwargs['vote'] = False
        kwargs['verbose'] = True
        self = cls(**kwargs )
        return self.run()
