import commune as c
from typing import *




class Access(c.Module):


    def __init__(self, 
                module : Union[c.Module, str] = None, # the module or any python object
                network: str =  'main', # mainnet
                stake2rate: int =  100.0,  # 1 call per every N tokens staked per timescale
                max_rate: int =  1000.0, # 1 call per every N tokens staked per timescale
                period = 60, # the period in seconds for the rate limit (1 minute)
                max_age = 600, # max age of the state in seconds
                sync_interval: int =  60, #  1000 seconds per sync with the network
                base_rate: int =  2, # the base rate for the whitelist
                **kwargs):
        """
        params: 
            module: the module to be used for the whitelist and blacklist
            network: the network to be used
            stake2rate: the rate at which the stake is converted to a rate
            max_rate: the maximum rate that can be achieved
            period: the period in seconds for the rate limit
            max_age: the maximum age of the state in seconds
            sync_interval: the interval in seconds to sync with the network
            base_rate: the base rate for the whitelist
        """
        self.set_config(locals())
        del self.config['module']
        self.set_module(module)
        self.sync_network()
        c.thread(self.run_loop)


    def verify(self, 
               address='5FNBuR2yVf4A1v5nt3w5oi4ScorraGRjiSVzkXBVEsPHaGq1', 
               fn: str = 'info') -> dict:
        # ONLY THE ADMIN CAN CALL ANY FUNCTION, THIS IS A SECURITY FEATURE
        # THE ADMIN KEYS ARE STORED IN THE CONFIG
        if c.is_admin(address):
            return {'success': True, 'msg': f'is verified admin'}
        if self.filter_user != None:
            assert self.filter_user(address, fn)
        # THIS IS VERY IMPORTANT 
        if fn not in self.whitelist:
            return {'success': False, 'msg': f"Function {fn} not in whitelist={self.whitelist}"}
        if fn in self.blacklist:
            return {'success': False, 'msg': f"Function {fn} is blacklisted={self.blacklist}" }
        if fn.startswith('__') or fn.startswith('_'):
            return {'success': False, 'msg': f'Function {fn} is private'}      
        if address in self.address2key:
            return {'success': True, 'msg': f'address {address} is a local key'}
        if c.is_user(address):
            return {'success': True, 'msg': f'is verified user'}

        self.sync_network()

        current_time = c.time()
        # sync of the state is not up to date 

        # STEP 1:  FIRST CHECK THE WHITELIST AND BLACKLIST
        state = self.state
        config = self.config
        c.print(state.keys(), 'fam')
        stake = state['stake'].get(address, 0)

        # STEP 2: CHECK THE STAKE AND CONVERT TO A RATE LIMIT
        rate_limit = min((stake / config.stake2rate) + self.config.base_rate, config.max_rate) # convert the stake to a rate
        # NOW LETS CHECK THE RATE LIMIT
        user_info_path = f'user_info/{address}'
        user_info = self.get(user_info_path, {})
        user_info['timestamp'] = user_info.get('timestamp', 0)
        # check if the user has exceeded the rate limit
        # if the time since the last call is greater than the seconds in the period, reset the requests
        time_since_reset_count = current_time - user_info['timestamp']
        if time_since_reset_count > config.period:
            user_info['rate'] = 0
            user_info['timestamp'] = current_time
        else:
            user_info['rate'] = user_info.get('rate', 0) + 1
    
        # update the user info
        user_info['success'] = bool(user_info['rate'] <= rate_limit)
        user_info['rate_limit'] = rate_limit
        user_info['period'] = config.period
        user_info['stake'] = stake
        
        self.put(user_info_path, user_info)
        self.state = state
        return user_info


    def set_module(self, module: c.Module):
        module = module or 'module'
        if isinstance(module, str):
            module = c.module(module)()
        self.whitelist =  list(set(module.whitelist + c.whitelist))
        self.blacklist =  list(set(module.blacklist + c.blacklist))
        if hasattr(self.module, 'filter_user'):
            self.filter_user = self.module.filter_user
        else:
             self.filter_user = None
        self.module = module
        return {'success': True, 'msg': f'set module to {module}'}
 
    time_since_sync = 0
    def sync_network(self):
        self.state_path = self.module.server_name
        state = self.get(self.state_path, {}, max_age=self.config.sync_interval)
        current_time = c.time()
        time_since_sync = current_time - self.time_since_sync
        if time_since_sync > self.config.sync_interval:
            self.key2address = c.key2address()
            self.address2key = {v:k for k,v in self.key2address.items()}
            self.subspace = c.module('subspace')(network=self.config.network)
            state['stake'] = self.subspace.stakes(fmt='j', netuid='all', update=False, max_age=self.config.max_age)
            state['timestamp'] = current_time
            self.put(self.state_path, state)
            self.time_since_sync = current_time
            c.print(f'🔄 Synced {self.state_path} at {state["timestamp"]}... 🔄\033', color='yellow')

        response = {'success': True, 
                    'path': self.state_path}
        self.state = state
        return response


    def run_loop(self):
        while True:
            try:
                r = self.sync_network()
            except Exception as e:
                r = c.detailed_error(e)
            c.print(r)
            c.sleep(self.config.sync_interval)



    @classmethod
    def test_whitelist(cls, key='vali::fam', base_rate=2, fn='info'):
        module = cls(module=c.module('module')(),  base_rate=base_rate)
        key = c.new_key()
        for i in range(base_rate*3):    
            t1 = c.time()
            result = module.verify(**{'address': key.ss58_address, 'fn': 'info'})
            assert result['success'] == bool(i <= base_rate), f'result: {result} expected: {i < base_rate}'
            t2 = c.time()

        c.print('🟢 Now with the root_key 🟢', color='green')
        key = c.root_key()
        # test for admin
        for i in range(base_rate*4):    
            t1 = c.time()
            result = module.verify(**{'address': key.ss58_address, 'fn': 'info'})
            assert result['success'] ,  result
            t2 = c.time()
        return {'success': True}


    @classmethod
    def test_blacklist(cls, fn='cmd'):
        module = cls(module=c.module('module')())
        admin_key = c.root_key()
        assert module.verify(**{'address': admin_key.ss58_address, 'fn': fn})['success']
        new_key = c.new_key()
        assert not module.verify(**{'address': new_key.ss58_address, 'fn': fn})['success']


        return {'success': True}

    def rm_state(self):
        self.put(self.state_path, {})
        return {'success': True, 'msg': f'removed {self.state_path}'}

    


if __name__ == '__main__':
    Access.run()

            
