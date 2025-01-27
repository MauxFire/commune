import commune as c
from typing import *
import json
import typer

class SubspaceWallet:

    ##################
    #### Transfer ####
    ##################
    def transfer(
        self,
        dest: str, 
        amount: float , 
        key: str = None,
        nonce= None,
        **kwargs
        
    ) -> bool:
        # this is a bit of a hack to allow for the amount to be a string for c send 500 0x1234 instead of c send 0x1234 500
        if type(dest) in [int, float]:
            assert isinstance(amount, str), f"Amount must be a string"
            new_amount = int(dest)
            dest = amount
            amount = new_amount
        key = self.resolve_key(key)
        dest = self.resolve_key_ss58(dest)
        amount = self.to_nanos(amount) # convert to nano (10^9 nanos = 1 token)

        response = self.compose_call(
            module='Balances',
            fn='transfer_keep_alive',
            params={
                'dest': dest, 
                'value': amount
            },
            key=key,
            nonce = nonce,
            **kwargs
        )
        
        return response

    def add_profit_shares(
        self,
        keys: List[str], # the keys to add profit shares to
        shares: List[float] = None , # the shares to add to the keys
        key: str = None,
        netuid : int = 0,
    ) -> bool:
        
        key = self.resolve_key(key)
        assert len(keys) > 0, f"Must provide at least one key"
        key2address = c.key2address()   
        keys = [key2address.get(k, k) for k in keys]             
        assert all([c.valid_ss58_address(k) for k in keys]), f"All keys must be valid ss58 addresses"
        shares = shares or [1 for _ in keys]

        assert len(keys) == len(shares), f"Length of keys {len(keys)} must be equal to length of shares {len(shares)}"

        response = self.compose_call(
            module='SubspaceModule',
            fn='add_profit_shares',
            params={
                'keys': keys, 
                'shares': shares,
                'netuid': netuid
            },
            key=key
        )

        return response


    def stake_many( self, 
                        modules:List[str] = None,
                        amounts:Union[List[str], float, int] = None,
                        key: str = None, 
                        netuid:int = 0,
                        min_balance = 100_000_000_000,
                        n:str = 100) -> Optional['Balance']:
        
        netuid = self.resolve_netuid( netuid )
        key = self.resolve_key( key )

        if modules == None:
            my_modules = self.my_modules(netuid=netuid,  update=False)
            modules = [m['key'] for m in my_modules if 'vali' in m['name']]

        modules = modules[:n] # only stake to the first n modules

        assert len(modules) > 0, f"No modules found with name {modules}"
        module_keys = modules
        
        if amounts == None:
            balance = self.get_balance(key=key, fmt='nanos') - min_balance
            amounts = [(balance // len(modules))] * len(modules) 
            assert sum(amounts) < balance, f'The total amount is {sum(amounts)} > {balance}'
        else:
            if isinstance(amounts, (float, int)): 
                amounts = [amounts] * len(modules)
            for i, amount in enumerate(amounts):
                amounts[i] = self.to_nanos(amount)

        assert len(modules) == len(amounts), f"Length of modules and amounts must be the same. Got {len(modules)} and {len(amounts)}."

        params = {
            "module_keys": module_keys,
            "amounts": amounts
        }

        response = self.compose_call('add_stake_multiple', params=params, key=key)

        return response
                    
    def transfer_multiple( self, 
                        destinations:List[str],
                        amounts:Union[List[str], float, int],
                        key: str = None, 
                        n:str = 10) -> Optional['Balance']:
        key2address = c.key2address()
        key = self.resolve_key( key )
        balance = self.get_balance(key=key, fmt='j')
        for i, destination in enumerate(destinations):
            if not c.valid_ss58_address(destination):
                if destination in key2address:
                    destinations[i] = key2address[destination]
                else:
                    raise Exception(f"Invalid destination address {destination}")
        if type(amounts) in [float, int]: 
            amounts = [amounts] * len(destinations)
        assert len(set(destinations)) == len(destinations), f"Duplicate destinations found"
        assert len(destinations) == len(amounts), f"Length of modules and amounts must be the same. Got {len(destinations)} and {len(amounts)}."
        assert all([c.valid_ss58_address(d) for d in destinations]), f"Invalid destination address {destinations}"
        total_amount = sum(amounts)
        assert total_amount < balance, f'The total amount is {total_amount} > {balance}'

        # convert the amounts to their interger amount (1e9)
        amounts = [a*(10**9) for a in amounts]

        params = {
            "destinations": destinations,
            "amounts": amounts
        }

        return self.compose_call('transfer_multiple', params=params, key=key)

    transfer_many = transfer_multiple

    def my_modules(self,
                    modules : list = None,
                    netuid=0,
                    timeout=30,
                    **kwargs):
        if modules == None:
            modules = self.my_keys(netuid=netuid)
        futures = [c.submit(self.get_module, kwargs=dict(module=module, netuid=netuid, **kwargs)) for module in modules]
        for future in c.as_completed(futures, timeout=timeout):
            module = future.result()
            print(module)
            if not c.is_error(module):
                modules += [module]
        return modules

    def unstake_many( self, 
                        
                        modules:Union[List[str], str] = None,
                        amounts:Union[List[str], float, int] = None,
                        key: str = None, 
                        netuid=0, 
                        update=True,
                        
                        ) -> Optional['Balance']:
        
        key = self.resolve_key( key )
        name2key = {}

        module_keys = []
        for i, module in enumerate(modules):
            if c.valid_ss58_address(module):
                module_keys += [module]
            else:
                if name2key == {}:
                    name2key = self.name2key(netuid=netuid, update=update)
                assert module in name2key, f"Invalid module {module} not found in SubNetwork {netuid}"
                module_keys += [name2key[module]]
            
        # RESOLVE AMOUNTS
        if amounts == None:
            stake_to = self.get_stake_to(key=key, names=False, update=update, fmt='j') # name to amounts
            amounts = [stake_to[m] for m in module_keys]
            
        if isinstance(amounts, (float, int)): 
            amounts = [amounts] * len(module_keys)

        for i, amount in enumerate(amounts):
            amounts[i] = self.to_nanos(amount) 

        assert len(module_keys) == len(amounts), f"Length of modules and amounts must be the same. Got {len(module_keys)} and {len(amounts)}."

        params = {
            "netuid": netuid,
            "module_keys": module_keys,
            "amounts": amounts
        }
        response = self.compose_call('remove_stake_multiple', params=params, key=key)
        return response


    def update_module(
        self,
        module: str, # the module you want to change
        address: str = None, # the address of the new module
        name: str = None, # the name of the new module
        delegation_fee: float = None, # the delegation fee of the new module
        metadata = None, # the metadata of the new module
        fee : float = None, # the fee of the new module
        netuid: int = 0, # the netuid of the new module
        nonce = None, # the nonce of the new module
        tip: int = 0, # the tip of the new module
        params = None
    ) -> bool:
        key = self.resolve_key(module)
        netuid = self.resolve_netuid(netuid)  
        assert self.is_registered(key.ss58_address, netuid=netuid), f"Module {module} is not registered in SubNetwork {netuid}"
        if params == None:
            params = {
                'name': name , # defaults to module.tage
                'address': address , # defaults to module.tage
                'delegation_fee': fee or delegation_fee, # defaults to module.delegate_fee
                'metadata': c.python2str(metadata or {}), # defaults to module.metadata
            }

        should_update_module = False
        module_info = self.get_module(key.ss58_address, netuid=netuid)

        for k,v in params.items(): 
            if params[k] == None:
                params[k] = module_info[k]
            if k in module_info and params[k] != module_info[k]:
                should_update_module = True

        if not should_update_module: 
            return {'success': False, 'message': f"Module {module} is already up to date"}
               
        c.print('Updating with', params, color='cyan')
        params['netuid'] = netuid
        
        reponse  = self.compose_call('update_module', params=params, key=key, nonce=nonce, tip=tip)

        # IF SUCCESSFUL, MOVE THE KEYS, AS THIS IS A NON-REVERSIBLE OPERATION


        return reponse

    update = update_server = update_module

    def stake_transfer(
            self,
            module_key: str ,
            new_module_key: str ,
            amount: Union[int, float] = None, 
            key: str = None,
        ) -> bool:
        # STILL UNDER DEVELOPMENT, DO NOT USE
        key = c.get_key(key)
        netuid = 0
        module_key = self.resolve_module_key(module_key, netuid=netuid)
        new_module_key = self.resolve_module_key(new_module_key, netuid=netuid)

        assert module_key != new_module_key, f"Module key {module_key} is the same as new_module_key {new_module_key}"

        if amount == None:
            amount = self.get_stake_to( key=key , fmt='j', max_age=0).get(module_key, 0)
        
        # Get current stake
        params={
                    'amount': int(amount * 10**9),
                    'module_key': module_key,
                    'new_module_key': new_module_key

                    }

        return self.compose_call('transfer_stake',params=params, key=key)

    def unstake(
            self,
            module : str = None, # defaults to most staked module
            amount: float =None, # defaults to all of the amount
            key : 'c.Key' = None,  # defaults to first key
            netuid=0,
            **kwargs
        ) -> dict:
        """
        description: 
            Unstakes the specified amount from the module. 
            If no amount is specified, it unstakes all of the amount.
            If no module is specified, it unstakes from the most staked module.
        params:
            amount: float = None, # defaults to all
            module : str = None, # defaults to most staked module
            key : 'c.Key' = None,  # defaults to first key 
            netuid : Union[str, int] = 0, # defaults to module.netuid
            network: str= main, # defaults to main
        return: 
            response: dict
        """
        
        key = c.get_key(key)
        # get most stake from the module

        if isinstance(module, int):
            module = amount
            amount = module

        assert module != None or amount != None, f"Must provide a module or an amount"
        key2address = c.key2address()
        if module in key2address:
            module_key = key2address[module]
        else:
            name2key = self.name2key(netuid=netuid)
            if module in name2key:
                module_key = name2key[module]
            else:
                module_key = module
        assert self.is_registered(module_key, netuid=netuid), f"Module {module} is not registered in SubNetwork {netuid}"
        
        if amount == None:
            stake_to = self.get_stake_to(names = False, fmt='nano', key=module_key)
            amount = stake_to[module_key] - 100000
        else:
            amount = int(self.to_nanos(amount))
        # convert to nanos
        params={
            'amount': amount ,
            'module_key': module_key
            }
        response = self.compose_call(fn='remove_stake',params=params, key=key, **kwargs)

        return response

    
    
    def my_servers(self, search=None,  **kwargs):
        servers = [m['name'] for m in self.my_modules(**kwargs)]
        if search != None:
            servers = [s for s in servers if search in s]
        return servers
    
    def my_modules_names(self, *args, **kwargs):
        my_modules = self.my_modules(*args, **kwargs)
        return [m['name'] for m in my_modules]

    def my_module_keys(self, *args,  **kwargs):
        modules = self.my_modules(*args, **kwargs)
        return [m['key'] for m in modules]

    def my_key2uid(self, *args, netuid=0, update=False, **kwargs):
        key2uid = self.key2uid(*args,  netuid=netuid, **kwargs)

        key2address = c.key2address(update=update )
        key_addresses = list(key2address.values())
        if netuid == 'all':
            for netuid, netuid_keys in key2uid.items():
                key2uid[netuid] = {k: v for k,v in netuid_keys.items() if k in key_addresses}

        my_key2uid = { k: v for k,v in key2uid.items() if k in key_addresses}
        return my_key2uid

    def my_keys(self,  
                netuid=0, 
                search=None, 
                max_age=None, 
                names  = False,
                update=False, **kwargs):
        netuid = self.resolve_netuid(netuid)
        keys = self.keys(netuid=netuid, max_age=max_age, update=update, **kwargs)
        key2address = c.key2address(search=search, max_age=max_age, update=update)
        if search != None:
            key2address = {k: v for k,v in key2address.items() if search in k}
        address2key = {v:k for k,v in key2address.items()}
        addresses = list(key2address.values())
        convert_fn = lambda x : address2key.get(x, x) if names else x
        if netuid == 'all':
            my_keys = {}
            for netuid, netuid_keys in keys.items():
                
                my_netuid_keys = [convert_fn(k) for k in netuid_keys if k in addresses]
                
                if len(my_netuid_keys) > 0:
                    my_keys[netuid] = my_netuid_keys
        else:
            my_keys = [convert_fn(k) for k in keys if k in addresses]
        return my_keys

    def register_servers(self,  
                         search=None, 
                         infos=None,  
                         netuid = 0, 
                         timeout=60, 
                         max_age=None, 
                         key=None, update=False, 
                         parallel = True,
                         **kwargs):
        '''
        key2address : dict
            A dictionary of module names to their keys
        timeout : int 
            The timeout for each registration
        netuid : int
            The netuid of the modules
        
        '''
        keys = c.submit(self.keys, dict(netuid=netuid, update=update, max_age=max_age))
        names = c.submit(self.names, dict(netuid=netuid, update=update, max_age=max_age))
        keys, names = c.wait([keys, names], timeout=timeout)

        if infos==None:
            infos = c.infos(search=search, **kwargs)
            should_register_fn = lambda x: x['key'] not in keys and x['name'] not in names
            infos = [i for i in infos if should_register_fn(i)]
            c.print(f'Found {infos} modules to register')
        if parallel:
            launcher2balance = c.key2balance()
            min_stake = self.min_register_stake(netuid=netuid)
            launcher2balance = {k: v for k,v in launcher2balance.items() if v > min_stake}
            launcher_keys = list(launcher2balance.keys())
            futures = []
            for i, info in enumerate(infos):
                if info['key'] in keys:
                    continue
                    
                launcher_key = launcher_keys[i % len(launcher_keys)]
                c.print(f"Registering {info['name']} with module_key {info['key']} using launcher {launcher_key}")
                f = c.submit(c.register, kwargs=dict(name=info['name'], 
                                                    address= info['address'],
                                                    netuid = netuid,
                                                    module_key=info['key'], 
                                                    key=launcher_key), timeout=timeout)
                futures+= [f]

                if len(futures) == len(launcher_keys):
                    for future in c.as_completed(futures, timeout=timeout):
                        r = future.result()
                        c.print(r, color='green')
                        futures.remove(future)
                        break

            for future in c.as_completed(futures, timeout=timeout):
                r = future.result()
                c.print(r, color='green')
                futures.remove(future)

            return infos
                
        else:

            for info in infos:
                r = c.register(name=info['name'], 
                            address= info['address'],
                            module_key=info['key'], 
                            key=key)
                c.print(r, color='green')
  
        return {'success': True, 'message': 'All modules registered'}


    def unregistered_servers(self, search=None, netuid = 0, key=None, max_age=None, update=False, transfer_multiple=True,**kwargs):
        netuid = self.resolve_netuid(netuid)
        servers = c.servers(search=search)
        key2address = c.key2address(update=update)
        keys = self.keys(netuid=netuid, max_age=max_age, update=update)
        unregister_servers = []
        for s in servers:
            if  key2address[s] not in keys:
                unregister_servers += [s]
        return unregister_servers

    
    

    def my_value( self, *args, **kwargs ):
        return sum(list(self.key2value( *args, **kwargs).values()))
    

    def my_total_stake(self, netuid='all', fmt='j', update=False):
        my_stake_to = self.my_stake_to(netuid=netuid,  fmt=fmt, update=update)
        return sum([sum(list(v.values())) for k,v in my_stake_to.items()])
    
    def my_staked_module_keys(self, netuid = 0, **kwargs):
        my_stake_to = self.my_stake_to(netuid=netuid, **kwargs)
        module_keys = {} if netuid == 'all' else []
        for subnet_netuid, stake_to_key in my_stake_to.items():
            if netuid == 'all':
                for _netuid, stake_to_subnet in stake_to_key.items():
                    module_keys[_netuid] = list(stake_to_subnet.keys()) + module_keys.get(_netuid, [])
            else:
                module_keys += list(stake_to_key.keys())
        return module_keys

    def my_stake_to(self, netuid = 0, fmt='j', **kwargs):
        stake_to = self.stake_to(netuid=netuid, fmt=fmt, **kwargs)
        key2address = c.key2address()
        my_stake_to = {}

        for key, address in key2address.items():
            my_stake_to[address] = {k:v  for k,v in stake_to.get(address, [])}
            
        stake_to_keys = list(my_stake_to.keys())
        for key in stake_to_keys:
            if len(my_stake_to[key]) == 0:
                del my_stake_to[key]

        return my_stake_to
    



    def my_stake_from(self, netuid = 0, block=None, update=False,  fmt='j', max_age=1000 , **kwargs):
        stake_from_tuples = self.stake_from(netuid=netuid,
                                             block=block,
                                               update=update, 
                                               tuples = True,
                                               fmt=fmt, max_age=max_age, **kwargs)

        address2key = c.address2key()
        stake_from_total = {}
        if netuid == 'all':
            for netuid, stake_from_tuples_subnet in stake_from_tuples.items():
                for module_key,staker_tuples in stake_from_tuples_subnet.items():
                    for staker_key, stake in staker_tuples:
                        if module_key in address2key:
                            stake_from_total[staker_key] = stake_from_total.get(staker_key, 0) + stake

        else:
            for module_key,staker_tuples in stake_from_tuples.items():
                for staker_key, stake in staker_tuples:
                    if module_key in address2key:
                        stake_from_total[staker_key] = stake_from_total.get(staker_key, 0) + stake

        
        for staker_address in address2key.keys():
            if staker_address in stake_from_total:
                stake_from_total[staker_address] = self.format_amount(stake_from_total[staker_address], fmt=fmt)
        return stake_from_total   



    def my_total_stake_to( self, 
                     key: str = None, 
                       block: Optional[int] = None, 
                       timeout=20,
                       names = False,
                        fmt='j' ,
                        update=False,
                        max_age = 1000,
                         **kwargs) -> Optional['Balance']:
        return sum(list(self.get_stake_to(key=key,  block=block, timeout=timeout, names=names, fmt=fmt, 
                                  update=update, 
                                 max_age=max_age, **kwargs).values()))
        


    
    def my_subnet2netuid(self, key=None, block=None, update=False, **kwargs):
        address2key = c.address2key()
        subnet_params = self.subnet_params(block=block, update=update, netuid='all', **kwargs)
        subnet2netuid = {}
        for netuid, subnet_params in subnet_params.items():
            if subnet_params['founder'] in address2key:
                subnet2netuid[subnet_params['name']] = netuid
        return subnet2netuid
    
    def my_subnets(self, key=None, update=True, **kwargs):
        return list(self.my_subnet2netuid(key=key,  update=update, **kwargs).keys())

    def my_modules(self, search=None, netuid=0, generator=False,  **kwargs):
        keys = self.my_keys(netuid=netuid, search=search)
        if netuid == 'all':
            modules = {}
            all_keys = keys 
            for netuid, keys in enumerate(all_keys):
                try:
                    modules[netuid]= self.get_modules(keys=keys, netuid=netuid, **kwargs)
                except Exception as e:
                    c.print(e)
            modules = {k: v for k,v in modules.items() if len(v) > 0 }
            return modules
        modules =  self.get_modules(keys=keys, netuid=netuid, **kwargs)
        return modules
    
    def stats(self, 
              search = None,
              netuid=0,  
              df:bool=True, 
              update:bool = False ,  
              features : list = ['name', 'emission','incentive', 'dividends', 'stake', 'vote_staleness', 'serving', 'address'],
              sort_features = ['emission', 'stake'],
              fmt : str = 'j',
              modules = None,
              servers = None,
              **kwargs
              ):
        
        if isinstance(netuid, str):
            netuid = self.subnet2netuid(netuid)

        if search == 'all':
            netuid = search
            search = None

        
        if netuid == 'all':
            all_modules = self.my_modules(netuid=netuid, update=update,  fmt=fmt, search=search)
            servers = c.servers()
            stats = {}
            netuid2subnet = self.netuid2subnet(update=update)
            for netuid, modules in all_modules.items():
                subnet_name = netuid2subnet[netuid]
                stats[netuid] = self.stats(modules=modules, netuid=netuid, servers=servers)

                color = c.random_color()
                c.print(f'\n {subnet_name.upper()} :: (netuid:{netuid})\n', color=color)
                c.print(stats[netuid], color=color)
            

        modules = modules or self.my_modules(netuid=netuid, update=update,  fmt=fmt, search=search)

        stats = []

        local_key_addresses = list(c.key2address().values())
        servers = servers or c.servers()
        for i, m in enumerate(modules):
            if m['key'] not in local_key_addresses :
                continue
            # sum the stake_from
            # we want to round these values to make them look nice
            for k in ['emission', 'dividends', 'incentive']:
                m[k] = c.round(m[k], sig=4)

            m['serving'] = bool(m['name'] in servers)
            m['stake'] = int(m['stake'])
            stats.append(m)
        df_stats =  c.df(stats)
        if len(stats) > 0:
            df_stats = df_stats[features]
            if 'emission' in features:
                epochs_per_day = self.epochs_per_day(netuid=netuid)
                df_stats['emission'] = df_stats['emission'] * epochs_per_day
            sort_features = [c for c in sort_features if c in df_stats.columns]  
            df_stats.sort_values(by=sort_features, ascending=False, inplace=True)
            if search is not None:
                df_stats = df_stats[df_stats['name'].str.contains(search, case=True)]

        if not df:
            return df_stats.to_dict('records')
        else:
            return df_stats





    def update_modules(self, search=None, 
                        timeout=60,
                        netuid=0,
                         **kwargs) -> List[str]:
        
        netuid = self.resolve_netuid(netuid)
        my_modules = self.my_modules(search=search, netuid=netuid, **kwargs)

        self.keys()
        futures = []
        namespace = c.namespace()
        for m in my_modules:

            name = m['name']
            if name in namespace:
                address = namespace[name]
            else:
                address = c.serve(name)['address']

            if m['address'] == address and m['name'] == name:
                c.print(f"Module {m['name']} already up to date")

            f = c.submit(c.update_module, kwargs={'module': name,
                                                    'name': name,
                                                    'netuid': netuid,
                                                    'address': address,
                                                  **kwargs}, timeout=timeout)
            futures+= [f]


        results = []

        for future in c.as_completed(futures, timeout=timeout):
            results += [future.result()]
            c.print(future.result())
        return results





    def stake(
            self,
            module: Optional[str] = None, # defaults to key if not provided
            amount: Union['Balance', float] = None, 
            key: str = None,  # defaults to first key
            existential_deposit: float = 0,
            netuid=0,
            **kwargs
        ) -> bool:
        """
        description: 
            Unstakes the specified amount from the module. 
            If no amount is specified, it unstakes all of the amount.
            If no module is specified, it unstakes from the most staked module.
        params:
            amount: float = None, # defaults to all
            module : str = None, # defaults to most staked module
            key : 'c.Key' = None,  # defaults to first key 
            netuid : Union[str, int] = 0, # defaults to module.netuid
            network: str= main, # defaults to main
        return: 
            response: dict
        
        """
        key = c.get_key(key)
        if c.valid_ss58_address(module):
            module_key = module
        else:
            module_key = self.name2key(netuid=netuid).get(module)

        # Flag to indicate if we are using the wallet's own hotkey.
        
        if amount == None:
            amount = self.get_balance( key.ss58_address , fmt='nano') - existential_deposit*10**9
        else:
            amount = int(self.to_nanos(amount - existential_deposit))
        assert amount > 0, f"Amount must be greater than 0 and greater than existential deposit {existential_deposit}"
        
        # Get current stake
        params={
                    'amount': amount,
                    'module_key': module_key
                    }

        return self.compose_call('add_stake',params=params, key=key)




    def key_info(self, key:str = None, netuid='all', detail=0, timeout=10, update=False, **kwargs):
        key_info = {
            'balance': self.get_balance(key=key, **kwargs),
            'stake_to': self.get_stake_to(key=key, **kwargs),
        }
        if detail: 
            pass
        else: 
            for netuid, stake_to in key_info['stake_to'].items():
                key_info['stake_to'][netuid] = sum(stake_to.values())


        return key_info

    


    def subnet2modules(self, **kwargs):
        subnet2modules = {}

        for netuid in self.netuids():
            c.print(f'Getting modules for SubNetwork {netuid}')
            subnet2modules[netuid] = self.my_modules(netuid=netuid, **kwargs)

        return subnet2modules
    
    def staking_rewards( self, 
                     key: str = None, 
                     module_key=None,
                       block: Optional[int] = None, 
                       timeout=20,
                       period = 100, 
                       names = False,
                        fmt='j' , update=False,
                        max_age = 1000,
                         **kwargs) -> Optional['Balance']:

        block = int(block or self.block)
        block_yesterday = int(block - period)
        day_before_stake = self.my_total_stake_to(key=key, module_key=module_key, block=block_yesterday, timeout=timeout, names=names, fmt=fmt,  update=update, max_age=max_age, **kwargs)
        day_after_stake = self.my_total_stake_to(key=key, module_key=module_key, block=block, timeout=timeout, names=names, fmt=fmt,  update=update, max_age=max_age, **kwargs) 
        return (day_after_stake - day_before_stake)

    def registered_servers(self, netuid = 0, **kwargs):
        netuid = self.resolve_netuid(netuid)
        servers = c.servers()
        keys = self.keys(netuid=netuid)
        registered_keys = []
        key2address = c.key2address()
        for s in servers:
            key_address = key2address[s]
            if key_address in keys:
                registered_keys += [s]
        return registered_keys

               
    def key2balance(self, search=None, 
                    batch_size = 64,
                    timeout = 10,
                    max_age = 1000,
                    fmt = 'j',
                    update=False,
                    names = False,
                    min_value=0.0001,
                      **kwargs):

        input_hash = c.hash(c.locals2kwargs(locals()))
        path = f'key2balance/{input_hash}'
        key2balance = self.get(path, max_age=max_age, update=update)

        if key2balance == None:
            key2balance = self.get_balances(search=search, 
                                    batch_size=batch_size, 
                                timeout=timeout, 
                                fmt = 'nanos',
                                update=1,
                                min_value=min_value, 
                                **kwargs)
            self.put(path, key2balance)

        for k,v in key2balance.items():
            key2balance[k] = self.format_amount(v, fmt=fmt)
        key2balance = sorted(key2balance.items(), key=lambda x: x[1], reverse=True)
        key2balance = {k: v for k,v in key2balance if v > min_value}
        if names:
            address2key = c.address2key()
            key2balance = {address2key[k]: v for k,v in key2balance.items()}
        return key2balance
    
    def empty_keys(self,  block=None, update=False, max_age=1000, fmt='j'):
        key2address = c.key2address()
        key2value = self.key2value( block=block, update=update, max_age=max_age, fmt=fmt)
        empty_keys = []
        for key,key_address in key2address.items():
            key_value = key2value.get(key_address, 0)
            if key_value == 0:
                empty_keys.append(key) 
        return empty_keys
    
    def profit_shares(self, key=None, **kwargs) -> List[Dict[str, Union[str, int]]]:
        key = self.resolve_module_key(key)
        return self.query_map('ProfitShares',  **kwargs)

    def key2stake(self, netuid = 'all',
                     block=None, 
                    update=False, 
                    names = True,
                    max_age = 1000,fmt='j'):
        stake_to = self.stake_to(netuid=netuid, 
                                block=block, 
                                max_age=max_age,
                                update=update, 
                                 
                                fmt=fmt)
        address2key = c.address2key()
        stake_to_total = {}
        if netuid == 'all':
            stake_to_dict = stake_to
           
            for staker_address in address2key.keys():
                for netuid, stake_to in stake_to_dict.items(): 
                    if staker_address in stake_to:
                        stake_to_total[staker_address] = stake_to_total.get(staker_address, 0) + sum([v[1] for v in stake_to.get(staker_address)])
        else:
            for staker_address in address2key.keys():
                if staker_address in stake_to:
                    stake_to_total[staker_address] = stake_to_total.get(staker_address, 0) + sum([v[1] for v in stake_to[staker_address]])
            # sort the dictionary by value
            stake_to_total = dict(sorted(stake_to_total.items(), key=lambda x: x[1], reverse=True))
        if names:
            stake_to_total = {address2key.get(k, k): v for k,v in stake_to_total.items()}
        return stake_to_total

    def key2value(self, netuid = 'all', block=None, update=False, max_age=1000, fmt='j', min_value=0, **kwargs):
        key2balance = self.key2balance(block=block, update=update,  max_age=max_age, fmt=fmt)
        key2stake = self.key2stake(netuid=netuid, block=block, update=update,  max_age=max_age, fmt=fmt)
        key2value = {}
        keys = set(list(key2balance.keys()) + list(key2stake.keys()))
        for key in keys:
            key2value[key] = key2balance.get(key, 0) + key2stake.get(key, 0)
        key2value = {k:v for k,v in key2value.items()}
        key2value = dict(sorted(key2value.items(), key=lambda x: x[1], reverse=True))
        return key2value
    
    def resolve_module_key(self, x, netuid=0, max_age=60):
        if not c.valid_ss58_address(x):
            name2key = self.name2key(netuid=netuid, max_age=max_age)
            x = name2key.get(x)
        assert c.valid_ss58_address(x), f"Module key {x} is not a valid ss58 address"
        return x
    
    def global_params(self, 
                    update = False,
                    max_age = 1000,
                    timeout=30,
                    fmt:str='j', 
                    features  = None,
                    value_features = [],
                    path = f'global_params',
                    **kwargs
                    ) -> list:  
        
        features = features or self.config.global_features
        subnet_params = self.get(path, None, max_age=max_age, update=update)
        names = [self.feature2name(f) for f in features]
        future2name = {}
        name2feature = dict(zip(names, features))
        for name, feature in name2feature.items():
            c.print(f'Getting {name} for {feature}')
            query_kwargs = dict(name=feature, params=[], block=None, max_age=max_age, update=update)
            f = c.submit(self.query, kwargs=query_kwargs, timeout=timeout)
            future2name[f] = name
        
        subnet_params = {}

        for f in c.as_completed(future2name):
            result = f.result()
            subnet_params[future2name.pop(f)] = result
        for k in value_features:
            subnet_params[k] = self.format_amount(subnet_params[k], fmt=fmt)
        return subnet_params

    def get_balance(self,
                 key: str = None ,
                 block: int = None,
                 fmt='j',
                 max_age=0,
                 update=False) -> Optional['Balance']:
        r""" Returns the token balance for the passed ss58_address address
        Args:
            address (Substrate address format, default = 42):
                ss58 chain address.
        Return:
            balance (bittensor.utils.balance.Balance):
                account balance
        """
        key_ss58 = self.resolve_key_ss58( key )

        result = self.query(
                module='System',
                name='Account',
                params=[key_ss58],
                block = block,
                update=update,
                max_age=max_age
            )

        return  self.format_amount(result['data']['free'] , fmt=fmt)

    balance = get_balance

    def accounts(self, key = None, update=True, block=None, max_age=100000, **kwargs):
        key = self.resolve_key_ss58(key)
        accounts = self.query_map(
            module='System',
            name='Account',
            update=update,
            block = block,
            max_age=max_age,
            **kwargs
        )
        return accounts
    
    def balances(self,fmt:str = 'n', block: int = None, n = None, update=False , **kwargs) -> Dict[str, 'Balance']:
        accounts = self.accounts( update=update, block=block)
        balances =  {k:v['data']['free'] for k,v in accounts.items()}
        balances = {k: self.format_amount(v, fmt=fmt) for k,v in balances.items()}
        return balances
    
    def blocks_per_day(self):
        return 24*60*60/self.block_time
    
    def min_burn(self,  block=None, update=False, fmt='j'):
        min_burn = self.query('MinBurn', block=block, update=update)
        return self.format_amount(min_burn, fmt=fmt)
    

    def get_balances(self, 
                    keys=None,
                    search=None, 
                    batch_size = 128,
                    fmt = 'j',
                    n = 100,
                    max_trials = 3,
                    names = False,
                    **kwargs):

        key2balance  = {}
        key2address = c.key2address(search=search)

        if keys == None:
            keys = list(key2address.keys())
        
        if len(keys) > n:
            c.print(f'Getting balances for {len(keys)} keys > {n} keys, using batch_size {batch_size}')
            balances = self.balances(**kwargs)
            key2balance = {}
            for k,a in key2address.items():
                if a in balances:
                    key2balance[k] = balances[a]
        else:
            future2key = {}
            for key in keys:
                f = c.submit(self.get_balance, kwargs=dict(key=key, fmt=fmt, **kwargs))
                future2key[f] = key
            
            for f in c.as_completed(future2key):
                key = future2key.pop(f)
                key2balance[key] = f.result()
                
        for k,v in key2balance.items():
            key2balance[k] = self.format_amount(v, fmt=fmt)


        if names:
            address2key = c.address2key()
            key2balance = {address2key[k]: v for k,v in key2balance.items()}
            
        return key2balance

    def total_balance(self, **kwargs):
        balances = self.balances(**kwargs)
        return sum(balances.values())

    def num_holders(self, **kwargs):
        balances = self.balances(**kwargs)
        return len(balances)

    def proposals(self,  block=None,  nonzero:bool=False, update:bool = False,  **kwargs):
        proposals = [v for v in self.query_map('Proposals', block=block, update=update, **kwargs)]
        return proposals

    def registrations_per_block(self,**kwargs) -> int:
        return self.query('RegistrationsPerBlock', params=[],  **kwargs)
    regsperblock = registrations_per_block
    
    def max_registrations_per_block(self, **kwargs) -> int:
        return self.query('MaxRegistrationsPerBlock', params=[], **kwargs)

    #################
    #### Serving ####
    #################
    def update_global(
        self,
        key: str = None,
        network : str = 'main',
        sudo:  bool = True,
        **params,
    ) -> bool:

        key = self.resolve_key(key)
        network = self.resolve_network(network)
        global_params = self.global_params(fmt='nanos')
        global_params.update(params)
        params = global_params
        for k,v in params.items():
            if isinstance(v, str):
                params[k] = v.encode('utf-8')
        # this is a sudo call
        return self.compose_call(fn='update_global',
                                     params=params, 
                                     key=key, 
                                     sudo=sudo)


    #################
    #### Serving ####
    #################
    def vote_proposal(
        self,
        proposal_id: int = None,
        key: str = None,
        network = 'main',
        nonce = None,
        netuid = 0,
        **params,

    ) -> bool:

        self.resolve_network(network)
        # remove the params that are the same as the module info
        params = {
            'proposal_id': proposal_id,
            'netuid': netuid,
        }

        response = self.compose_call(fn='add_subnet_proposal',
                                     params=params, 
                                     key=key, 
                                     nonce=nonce)

        return response
       





    def register(
        self,
        name: str , # defaults to module.tage
        address : str = None,
        stake : float = None,
        netuid = 0,
        subnet: str = None,
        key : str  = None,
        module_key : str = None,
        wait_for_inclusion: bool = True,
        wait_for_finalization: bool = True,
        max_address_characters = 32,
        metadata = None,
        nonce=None,
        tag = None,
        ensure_server = True,
    **kwargs
    ) -> bool:
        module_key =  c.get_key(module_key or name).ss58_address
        if subnet == None:
            netuid2subnet = self.netuid2subnet(update=False)   
            subnet = netuid2subnet[netuid]
        else:
            assert isinstance(subnet, str), f"Subnet must be a string"
            if not subnet in subnet2netuid:
                subnet2netuid = self.subnet2netuid(update=True)
                if subnet not in subnet2netuid:
                    subnet2netuid[subnet] = len(subnet2netuid)
                    response = input(f"Do you want to create a new subnet ({subnet}) (yes or y or dope): ")
                    if response.lower() not in ["yes", 'y', 'dope']:
                        return {'success': False, 'msg': 'Subnet not found and not created'}
                
        # require prompt to create new subnet        
        stake = (stake or 0) * 1e9
        address = address or '0.0.0.0'
        if c.server_exists(name):
            address = c.namespace().get(name)

        params = { 
                    'network': subnet.encode('utf-8'),
                    'address': address[-max_address_characters:].replace('0.0.0.0', c.ip()).encode('utf-8'),
                    'name': name.encode('utf-8'),
                    'stake': stake,
                    'module_key': module_key,
                    'metadata': json.dumps(metadata or {}).encode('utf-8'),
                }
        
        # create extrinsic call
        response = self.compose_call('register', params=params, key=key, wait_for_inclusion=wait_for_inclusion, wait_for_finalization=wait_for_finalization, nonce=nonce)
        return response
    
    def resolve_uids(self, uids: Union['torch.LongTensor', list], netuid: int = 0, update=False) -> None:
        name2uid = None
        key2uid = None
        for i, uid in enumerate(uids):
            if isinstance(uid, str):
                if name2uid == None:
                    name2uid = self.name2uid(netuid=netuid, update=update)
                if uid in name2uid:
                    uids[i] = name2uid[uid]
                else:
                    if key2uid == None:
                        key2uid = self.key2uid(netuid=netuid, update=update)
                    if uid in key2uid:
                        uids[i] = key2uid[uid]
        return uids

    def set_weights(
        self,
        uids: Union['torch.LongTensor', list] ,
        weights: Union['torch.FloatTensor', list] ,
        netuid: int = 0,
        key: 'c.key' = None,
        update=False,
        modules = None,
        vector_length = 2**16 - 1,
        nonce=None,
        **kwargs
    ) -> bool:
        import torch
        netuid = self.resolve_netuid(netuid)
        key = self.resolve_key(key)

        # ENSURE THE UIDS ARE VALID UIDS, CONVERTING THE NAMES AND KEYS ASSOCIATED WITH THEM
        uids = self.resolve_uids(modules or uids, netuid=netuid, update=update)
        weights = weights or  [1] * len(uids)
        
        # CHECK WEIGHTS LENGHTS
        assert len(uids) == len(weights), f"Length of uids {len(uids)} must be equal to length of weights {len(weights)}"
        
        # NORMALIZE WEIGHTS
        weights = torch.tensor(weights)
        weights = (weights / weights.sum()) * vector_length # normalize the weights between 0 and 1
        weights = torch.clamp(weights, 0, vector_length)  # min_value and max_value are between 0 and 1
        
        params = {'uids': list(map(int, uids)),
                  'weights': list(map(int, weights.tolist())), 
                  'netuid': netuid}
        
        return self.compose_call('set_weights',params = params , key=key, nonce=nonce, **kwargs)
        
    vote = set_weights
    
    def unstake_all( self, 
                        key: str = None, 
                        existential_deposit = 1,
                        min_stake = 0.5,
                        ) -> Optional['Balance']:
        
        key = self.resolve_key( key )
        key_stake_to = self.get_stake_to(key=key,  names=False, update=True, fmt='nanos') # name to amount

        min_stake = min_stake * 1e9
        key_stake_to = {k:v for k,v in key_stake_to.items() if v > min_stake }

        params = {
            "module_keys": list(key_stake_to.keys()),
            "amounts": list(key_stake_to.values())
        }

        



        response = {}

        if len(key_stake_to) > 0:
            c.print(f'Unstaking all of {len(key_stake_to)} modules')
            response['stake'] = self.compose_call('remove_stake_multiple', params=params, key=key)
            total_stake = (sum(key_stake_to.values())) / 1e9
        else: 
            c.print(f'No modules found to unstake')
            total_stake = self.get_balance(key)
        total_stake = total_stake - existential_deposit
        
        return response

    def registered_keys(self, netuid='all'):
        key2address = c.key2address()
        address2key = {v:k for k,v in key2address.items()}
        
        if netuid == 'all':
            registered_keys = {}
            netuid2keys =  self.keys(netuid=netuid)
            for netuid, keys in netuid2keys.items():
                registered_keys[netuid] = []
                for k in keys:
                    if k in address2key:
                        registered_keys[netuid].append(k)
        else:
            registered_keys = [k for k in self.keys(netuid=netuid) if k in address2key]

        return registered_keys
