import commune as c
import json
import numpy as np
import os
import streamlit as st
import plotly.express as px
import datetime

class App(c.Module):
    def __init__(self, model = 'model.openrouter', 
                 score_module=None):
        self.model = c.module(model)()
        if score_module != None:
            self.score_model = c.module(score_module)()
        else:
            self.score_model =  c.import_object('redvblue.score_model.JailbreakScoreModel')()
        
    def signin(self):
        
        secret = st.text_input('SIGNIN WITH SECRET', 'FAM', type='password')
        key = c.pwd2key(secret)
        self.key = key
        st.write('My Key Address')
        st.code(key.ss58_address)

        with st.expander('About SIGNIN'):
            st.write('''
            This is a simple sign in form that will generate a key based on a secret. 
            The key is used to identify you in the system. 

            Please enter a secret that you can remember. We do not store your secret, only the key that is generated from it.
                     
            How is the key generated?
            The key is generated by hashing the secret using the sha256 algorithm. This hash is then used as the uri for the key.
            
            Security Note: The longer the secret, the more secure the key. If you have a short secret, it can be regenerated by an attacker. You should have a long secret that is hard to guess. 
                     
            ''')
        
        
        return self.key
    

    def get_history(self, address=None, model=None):
        history_paths = self.get_history_paths(address=address, model=model)
        history = [self.get_json(fp) for fp in history_paths]
        return history
    

    def get_history_paths(self, address=None, model=None):
        address = address or self.key.ss58_address
        history_paths = []
        model_paths = [self.resolve_path(f'history/{model}')] if model else self.ls('history')
        for model_path in model_paths:
            user_folder = f'{model_path}/{address}'
            if not self.exists(user_folder):
                continue
            for fp in self.ls(user_folder):
                history_paths += [fp]
        return history_paths
    


    def defend_model(self):
        pass

    def blue_team(self):
        st.write('## Blue Team')

    def help(self):

        st.write('''
                 
        ## Purpose
                 
        This is the attack model section. In this section, you can attack the model by providing a red team prompt and the model will respond with a prediction. 
        The prediction will be scored by the blue team model and the result will be displayed. The higher the score, the more likely the model is to be jailbroken.
        
        ## How to Attack
        
        1. Enter a prompt in the text area under the Attack section
        2. Select a model from the dropdown
        3. Click the Submit Attack button
        4. The model will respond with a prediction
        5. The prediction will be scored by the blue team model. 
                 
                 ''')




    def arena(self):
        # c.load_style()
        model = st.selectbox('Select a model', self.score_model.models())
        text = st.text_area('Red Team Prompt')
        cols = st.columns([1,1])

        submit_attack = cols[0].button('Submit Attack')
        cancel_attack = cols[1].button('Cancel Attack')
        attack_model = submit_attack and not cancel_attack
        if attack_model :
            model_response_generator = self.model.forward(text, model=model, stream=True)

            model_dict =  {'response': ''}
            def generator_stream(generator, model_dict=None):
                for token in generator:
                    if model_dict != None:
                        model_dict['response'] += token
                    yield token
                
                
            st.write_stream(generator_stream(model_response_generator, model_dict))
            model_response = model_dict['response']

            result = self.score_model.score(model_response)# dict where mean is the score
            result['prompt'] = text
            result['response'] = model_response
            result['model'] = model
            result['address'] = self.key.ss58_address
            self.save_result(result)

            with st.status(f"Jailbreak Score ({result['mean']})", expanded=False):
                st.write(result)

    def save_result(self, response):
        model = response['model']
        address = response['address']
        model = model.replace('/', '::')
        path =  f'history/{model}/{address}/{c.time()}.json'
        self.put_json(path, response)

    def my_history(self, columns=['mean', 'timestamp', 'model', 'address'], sort_by='timestamp', ascending=False, model=None):
        df = c.df(self.get_history(model=model))
        if len(df) > 0:
            df = df[columns].sort_values(sort_by, ascending=ascending)
        else:
            st.write('No history found')
            return df
        # convert timestmap to human readable
        df['time'] = df['timestamp'].apply(lambda x: datetime.datetime.fromtimestamp(x).strftime('%m-%d %H:%M'))
        del df['timestamp']
        del df['address']
        df = df.set_index('time')
        df.sort_index(inplace=True)
        return df

    def leaderboard(self, 
              columns=['mean', 'timestamp', 'model', 'address'],
              group_by = ['address', 'model'], 
              sort_by='mean', ascending=False, model=None):
        cols = st.columns([4,1])
        for i in range(2):
            cols[0].write('\n')

        df = c.df(self.global_history())
      
        if len(df) == 0:
            st.error('No history found, enter the arena')
            return df
        
        # PROCESS THE DATA
        df = df[columns].sort_values(sort_by, ascending=ascending)
        # convert timestmap to human readable
        df['time'] = df['timestamp'].apply(lambda x: datetime.datetime.fromtimestamp(x).strftime('%Y-%m-%d %H:%M:%S'))
        del df['timestamp']

        # group based on address


        st.write('Top Jailbreakers')
        user_df = df
        # select a model
        models = ['ALL'] + list(user_df['model'].unique())
        model = st.selectbox('Select a models', models, 0)
        if model != 'ALL':
            user_df = user_df[user_df['model'] == model]
        user_df = user_df.groupby('address')['mean'].agg(['mean', 'std', 'count']).reset_index()
        user_df = user_df.sort_values('mean', ascending=False)
        st.write(user_df)

        st.write('Least Jailbroken Models') 
        model_df = df.groupby('model')['mean'].agg(['mean', 'std', 'count']).reset_index()
        model_df = model_df.sort_values('mean', ascending=False)
        st.write(model_df)

    def sidebar(self, sidebar=True):
    
        if sidebar:
            with st.sidebar:
                return self.sidebar(sidebar=False)
        st.write('# RedvBlue')
        self.signin()
        teams = ['red', 'blue']
        # side by side radio buttons
        self.team = st.radio('Select a team', teams, index=0)
        

    def top_header(self):
        # have a random image
        st.write(f'# TEAM {self.team.upper()} ') 


    def app(self):
        self.sidebar()
        self.load_style()
        self.top_header()
        fns = [ f'arena', 'leaderboard', 'help']
        tab_names = ['Attack', 'Leaderboard', 'Mission Details']
        tabs = st.tabs(tab_names)
        for i, fn in enumerate(fns):
            with tabs[i]:
                getattr(self, fn)()

    @property
    def readme(self):
        return self.get_text(f'{self.dirpath()}/README.md')


    def global_history_paths(self):
        return self.glob('history/**')
    
    def global_history(self):
        history = []
        for path in self.global_history_paths():
            history += [self.get_json(path)]
        return history
    
    def clear_history(self):
        return [self.rm(path) for path in self.global_history_paths()]
    
    def load_style(self):
        style_path = self.dirpath() + f'/styles/app.css'
        with open(style_path) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True) 


        style_path = self.dirpath() + f'/styles/{self.team}.css'
        with open(style_path) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True) 

    
App.run(__name__)